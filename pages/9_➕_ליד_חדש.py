import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import time
import json

from engines import (
    init_db, calculate_smart_commission, N8nIntegration, TelegramNotifier,
    COMMISSION_RATES
)

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="הוספת ליד חדש")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="new_lead_dark_mode")
if dark_mode:
    TEXT_COLOR = "#ffffff"
else:
    TEXT_COLOR = "#000000"

st.markdown(f"""
<style>
    .stApp, .main, .stMarkdown, p, h1, h2, h3, h4, h5, h6, span, label {{
        direction: rtl;
        text-align: right;
        font-family: 'Heebo', sans-serif;
        color: {TEXT_COLOR} !important;
    }}
    section[data-testid="stSidebar"] {{
        direction: rtl;
        text-align: right;
    }}
</style>
""", unsafe_allow_html=True)

# --- Constants ---
SOURCE_OPTIONS = ["פייסבוק", "גוגל", "חבר מביא חבר", "אינסטגרם", "טיקטוק", "רכישת לידים", "LinkedIn", "אתר אינטרנט",
                  "אחר"]

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("➕ הוספת ליד חדש")

with st.form("add_lead_ultimate"):
    st.subheader("📋 פרטים אישיים")

    # שורה ראשונה - פרטי יצירת קשר בסיסיים
    col1, col2, col3 = st.columns(3)
    new_name = col1.text_input("שם מלא *")
    new_phone = col2.text_input("טלפון *")
    new_email = col3.text_input("אימייל")

    # שורה שנייה - זיהוי ותאריכים (התאמה לשדרוג ה-OCR)
    col4, col5, col6, col7 = st.columns(4)
    new_id_number = col4.text_input("תעודת זהות")
    new_issue_date = col5.text_input("תאריך הנפקה") # השדה החדש
    new_expiry_date = col6.text_input("תאריך תוקף")   # שונה מ-"הנפקה/תוקף"
    new_source = col7.selectbox("מקור ליד", SOURCE_OPTIONS)

    st.divider()
    st.subheader("💼 תיק ביטוחי")
    default_policies = pd.DataFrame([{"type": "בחר...", "company": "בחר...", "prem": 0}])
    policy_config = {
        "type": st.column_config.SelectboxColumn("מוצר",
                                                 options=["רכב", "דירה", "בריאות", "חיים", "פנסיוני", "משכנתה"]),
        "company": st.column_config.SelectboxColumn("חברה", options=list(COMMISSION_RATES.keys())),
        "prem": st.column_config.NumberColumn("פרמיה חודשית", format="₪%.0f")
    }
    new_policies = st.data_editor(default_policies, column_config=policy_config, num_rows="dynamic",
                                  use_container_width=True)

    st.divider()
    st.subheader("⏰ תזמון והערות")
    new_callback = st.date_input("📅 תאריך חזרה", datetime.now() + timedelta(days=1))
    new_notes = st.text_area("📝 הערות ראשוניות")

    submitted = st.form_submit_button("💾 שמור ליד", type="primary", use_container_width=True)

    if submitted:
        if not new_name or not new_phone:
            st.error("❌ חובה למלא שם וטלפון!")
        else:
            valid_policies = [p for p in new_policies.to_dict('records') if p.get('type') != "בחר..."]
            total_premium = sum(p['prem'] for p in valid_policies)
            total_commission = sum(
                calculate_smart_commission(p['company'], p['type'], p['prem']) for p in valid_policies)
            policies_json = json.dumps(valid_policies, ensure_ascii=False)

            # עדכון השאילתה לכלול את כל 13 השדות (כולל issue_date)
            conn.execute("""
                INSERT INTO leads (name, phone, id_number, expiry_date, issue_date, email, source, policies_json, monthly_premium, estimated_commission, callback_date, notes, lead_score) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (new_name, new_phone, new_id_number, new_expiry_date, new_issue_date, new_email, new_source, policies_json,
                  total_premium, total_commission, new_callback.strftime('%Y-%m-%d'), new_notes, 50))
            conn.commit()

            lead_payload = {"name": new_name, "phone": new_phone, "email": new_email, "source": new_source,
                            "status": "חדש"}
            N8nIntegration.notify_new_lead(lead_payload)

            st.success("✅ ליד נשמר בהצלחה!")
            st.balloons()
            time.sleep(1.5)
            st.rerun()