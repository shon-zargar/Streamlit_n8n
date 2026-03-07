import streamlit as st
import pandas as pd
import time

from engines import init_db, get_leads_data, SMS2010Handler

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="מרכז הודעות")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="sms_dark_mode")
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
    /* Fix for table alignment */
    .stDataFrame {{
        direction: rtl;
    }}
    .stDataFrame th, .stDataFrame td {{
        text-align: right;
    }}
</style>
""", unsafe_allow_html=True)

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("💬 מרכז הודעות ו-SMS")
st.caption(f"מחובר למערכת SMS2010 | יתרה נוכחית: {SMS2010Handler.get_balance()} הודעות")

sms_tabs = st.tabs(["🚀 שליחה מהירה", "📢 קמפיין תפוצה", "📝 ניהול תבניות", "📜 היסטוריה"])

# Tab 1: Quick Send
with sms_tabs[0]:
    st.subheader("שליחת הודעה ללקוח בודד")
    df = get_leads_data(conn)
    if not df.empty:
        selected_lead_id = st.selectbox("בחר לקוח:", df['id'].tolist(), format_func=lambda x: df[df['id'] == x]['name'].values[0])
        lead_row = df[df['id'] == selected_lead_id].iloc[0]
        
        message_body = st.text_area("תוכן ההודעה", height=150)
        if st.button("📤 שלח SMS", type="primary"):
            if message_body:
                success, resp = SMS2010Handler.send_sms(lead_row['phone'], message_body, lead_row['id'], conn)
                if success:
                    st.success("✅ ההודעה נשלחה בהצלחה!")
                else:
                    st.error(f"❌ שגיאה בשליחה: {resp}")
            else:
                st.error("ההודעה ריקה!")
    else:
        st.warning("אין לקוחות במערכת.")

# Tab 2: Bulk Campaign
with sms_tabs[1]:
    st.subheader("שליחה מרובה (Bulk SMS)")
    df = get_leads_data(conn)
    if not df.empty:
        filter_status = st.multiselect("סנן לפי סטטוס", df['status'].unique(), default=["חדש", "בטיפול"])
        target_leads = df[df['status'].isin(filter_status)]
        st.metric("קהל יעד", f"{len(target_leads)} לקוחות")
        
        bulk_msg = st.text_area("תוכן ההודעה לתפוצה", placeholder="שלום {name}, רצינו לעדכן...")
        if st.button("🚀 שלח לכולם"):
            # Simulation for now
            st.success(f"סימולציה: נשלחו {len(target_leads)} הודעות.")
    else:
        st.warning("אין לקוחות במערכת.")

# Tab 3: Templates
with sms_tabs[2]:
    st.subheader("ניהול תבניות SMS")
    with st.form("new_sms_template"):
        t_title = st.text_input("שם התבנית")
        t_content = st.text_area("תוכן (השתמש ב-{name})")
        if st.form_submit_button("💾 שמור תבנית"):
            conn.execute("INSERT INTO sms_templates (title, content) VALUES (?,?)", (t_title, t_content))
            conn.commit()
            st.success("נשמר!")
            st.rerun()
    
    templates = pd.read_sql("SELECT * FROM sms_templates", conn)
    st.dataframe(templates, use_container_width=True)

# Tab 4: History
with sms_tabs[3]:
    st.subheader("לוג הודעות יוצאות")
    logs = pd.read_sql("SELECT * FROM sms_logs ORDER BY id DESC", conn)
    st.dataframe(logs, use_container_width=True)
