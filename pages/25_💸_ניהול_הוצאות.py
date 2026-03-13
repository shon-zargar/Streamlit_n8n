import streamlit as st
import pandas as pd
from datetime import datetime
import time
import plotly.express as px

from engines import init_db, setup_page_styling

# --- Page Configuration & Styling (RULE 1) ---
st.set_page_config(layout="wide", page_title="ניהול הוצאות")
theme = setup_page_styling()

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
    
    # --- Chart Theming (RULE 3) ---
    fig = px.bar(
        expenses.groupby('category')['amount'].sum(),
        title="הוצאות לפי קטגוריה",
        template=theme.get('plot', 'plotly_white')
    )
    st.plotly_chart(fig, use_container_width=True)

    st.dataframe(expenses, use_container_width=True, hide_index=True)
else:
    st.info("אין הוצאות רשומות")
