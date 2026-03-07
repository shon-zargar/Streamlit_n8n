import streamlit as st
import pandas as pd
from datetime import datetime
import time

from engines import init_db

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="ניהול קמפיינים")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="campaign_dark_mode")
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
st.title("💼 Campaign Manager")

with st.expander("➕ יצירת קמפיין חדש"):
    with st.form("new_campaign"):
        camp_name = st.text_input("שם הקמפיין")
        camp_type = st.selectbox("סוג", ["Email", "SMS", "WhatsApp"])
        camp_start = st.date_input("תאריך התחלה")
        
        if st.form_submit_button("🚀 צור קמפיין"):
            conn.execute("INSERT INTO campaigns (name, type, start_date) VALUES (?, ?, ?)", 
                         (camp_name, camp_type, camp_start.strftime('%Y-%m-%d')))
            conn.commit()
            st.success("✅ קמפיין נוצר!")
            time.sleep(0.5)
            st.rerun()

campaigns = pd.read_sql("SELECT * FROM campaigns ORDER BY id DESC", conn)
if not campaigns.empty:
    st.subheader("📋 קמפיינים פעילים")
    st.dataframe(campaigns, use_container_width=True, hide_index=True)
else:
    st.info("אין קמפיינים")
