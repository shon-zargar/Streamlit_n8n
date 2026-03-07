import streamlit as st
import pandas as pd
from datetime import datetime
import time

from engines import init_db, get_leads_data, get_claims_data

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="ניהול תביעות")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="claims_dark_mode")
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
    .stDataFrame {{ direction: rtl; }}
    .stDataFrame th, .stDataFrame td {{ text-align: right; }}
</style>
""", unsafe_allow_html=True)

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("🏥 מעקב תביעות ביטוח")

with st.expander("➕ פתיחת תביעה חדשה"):
    df_leads = get_leads_data(conn)
    if not df_leads.empty:
        with st.form("new_claim"):
            claim_lead = st.selectbox("לקוח", df_leads['id'].tolist(), format_func=lambda x: df_leads[df_leads['id'] == x]['name'].values[0])
            claim_type = st.selectbox("סוג תביעה", ["בריאות", "רכב", "דירה", "חיים", "אחר"])
            claim_company = st.selectbox("חברת ביטוח", ["הראל", "מגדל", "מנורה", "פניקס", "כלל", "הכשרה"])
            claim_amount = st.number_input("סכום תביעה (₪)", 0, 10000000, 5000, 500)
            
            if st.form_submit_button("📝 פתח תביעה"):
                lead_name = df_leads[df_leads['id'] == claim_lead]['name'].values[0]
                conn.execute("INSERT INTO claims (lead_id, lead_name, type, company, status, open_date, amount) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (claim_lead, lead_name, claim_type, claim_company, 'פתוח', datetime.now().strftime('%Y-%m-%d'), claim_amount))
                conn.commit()
                st.success("✅ תביעה נפתחה!")
                time.sleep(0.5)
                st.rerun()
    else:
        st.warning("אין לקוחות במערכת לפתיחת תביעה.")

claims = get_claims_data(conn)
if not claims.empty:
    st.subheader(f"📋 תביעות פעילות ({len(claims)})")
    st.dataframe(claims, use_container_width=True, hide_index=True)
else:
    st.info("אין תביעות במערכת")
