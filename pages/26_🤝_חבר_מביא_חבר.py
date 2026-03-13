import streamlit as st
import pandas as pd
from datetime import datetime
import time

from engines import init_db, get_leads_data, setup_page_styling

# --- Page Configuration & Styling (RULE 1) ---
st.set_page_config(layout="wide", page_title="חבר מביא חבר")
theme = setup_page_styling()

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
