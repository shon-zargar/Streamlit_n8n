import streamlit as st
import pandas as pd
from datetime import datetime
import time

from engines import init_db, get_leads_data

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="חבר מביא חבר")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="referral_dark_mode")
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
st.title("🤝 תוכנית חבר מביא חבר")
df_leads = get_leads_data(conn)

if not df_leads.empty:
    with st.expander("➕ רישום הפניה חדשה"):
        with st.form("new_referral"):
            referrer = st.selectbox("לקוח מפנה", df_leads['id'].tolist(), format_func=lambda x: df_leads[df_leads['id'] == x]['name'].values[0])
            ref_name = st.text_input("שם הממליץ החדש")
            ref_phone = st.text_input("טלפון הממליץ החדש")
            
            if st.form_submit_button("💾 רשום הפניה"):
                conn.execute("INSERT INTO referrals (referrer_id, referred_name, referred_phone, status, date_referred) VALUES (?, ?, ?, ?, ?)",
                             (referrer, ref_name, ref_phone, 'ממתין', datetime.now().strftime('%Y-%m-%d')))
                conn.commit()
                st.success("✅ הפניה נרשמה!")
                time.sleep(0.5)
                st.rerun()

    referrals = pd.read_sql("SELECT r.*, l.name as referrer_name FROM referrals r JOIN leads l ON r.referrer_id = l.id", conn)
    if not referrals.empty:
        st.subheader("📋 הפניות")
        st.dataframe(referrals, use_container_width=True, hide_index=True)
    else:
        st.info("אין הפניות עדיין")
else:
    st.warning("אין לקוחות במערכת.")
