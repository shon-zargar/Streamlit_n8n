import streamlit as st
import pandas as pd
from datetime import datetime
import time

from engines import init_db

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="ניהול הוצאות")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="expenses_dark_mode")
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
st.title("💸 מעקב הוצאות עסקיות")

with st.expander("➕ הוספת הוצאה"):
    with st.form("add_expense"):
        exp_date = st.date_input("תאריך", datetime.now())
        exp_category = st.selectbox("קטגוריה", ["שיווק", "משרד", "נסיעות", "אחר"])
        exp_amount = st.number_input("סכום (₪)", 0, 100000, 0, 10)
        
        if st.form_submit_button("💾 שמור הוצאה"):
            conn.execute("INSERT INTO expenses (date, category, amount) VALUES (?, ?, ?)",
                         (exp_date.strftime('%Y-%m-%d'), exp_category, exp_amount))
            conn.commit()
            st.success("✅ נשמר!")
            time.sleep(0.5)
            st.rerun()

expenses = pd.read_sql("SELECT * FROM expenses ORDER BY date DESC", conn)
if not expenses.empty:
    st.metric("💸 סה'כ הוצאות", f"₪{expenses['amount'].sum():,.0f}")
    st.bar_chart(expenses.groupby('category')['amount'].sum())
    st.dataframe(expenses, use_container_width=True, hide_index=True)
else:
    st.info("אין הוצאות רשומות")
