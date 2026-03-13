import streamlit as st
import pandas as pd
from datetime import date, datetime
import math
import io

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="מחשבונים", page_icon="🧮")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. ייבוא בטוח מהמנוע (RULE 1) ---
try:
    from engines import (
        init_db, get_leads_data, add_interaction, save_file,
        FinanceEngine, FinConfig, generate_branded_calc_pdf,
        setup_page_styling, safe_format
    )
    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבים ב-engines.py. {e}")
    st.stop()

# --- חיבור למסד נתונים ---
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None

st.title("🧮 מחשבוני ביטוח ופיננסים")
st.caption("כלי עזר לחישוב עמלות, השפעת דמי ניהול וביטוח חיים.")

tabs = st.tabs(["📉 הפסד דמי ניהול", "💡 ביטוח חיים", "🏠 משכנתה", "💰 עמלות"])

# --- TAB 1: דמי ניהול ---
with tabs[0]:
    st.header("📉 השפעת דמי ניהול על הצבירה")
    st.markdown("מחשבון זה מדגים ללקוח כמה כסף הוא מאבד בגלל דמי ניהול גבוהים.")

    col1, col2, col3 = st.columns(3)
    balance = col1.number_input("צבירה נוכחית (₪)", min_value=0, value=100000, step=10000)
    monthly = col2.number_input("הפקדה חודשית (₪)", min_value=0, value=2000, step=100)
    years = col3.slider("תקופת חישוב (בשנים)", min_value=1, max_value=40, value=20)

    col4, col5, col6 = st.columns(3)
    yield_rate = col4.number_input("תשואה שנתית משוערת (%)", min_value=0.0, max_value=15.0, value=5.0, step=0.5) / 100
    fee_current = col5.number_input("דמי ניהול נוכחיים מצבירה (%)", min_value=0.0, max_value=3.0, value=0.8, step=0.05) / 100
    fee_target = col6.number_input("דמי ניהול יעד מצבירה (%)", min_value=0.0, max_value=3.0, value=0.4, step=0.05) / 100

    if st.button("חשב השפעה", type="primary"):
        res = FinanceEngine.project_fee_impact(balance, monthly, years, yield_rate, fee_current, fee_target)
        
        st.divider()
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("צבירה בתנאים נוכחיים", f"₪{safe_format(res.get('projection_2', 0)):,.0f}")
        res_col2.metric("צבירה בתנאי יעד", f"₪{safe_format(res.get('projection_1', 0)):,.0f}")
        res_col3.metric("💸 הפסד צפוי", f"₪{safe_format(res.get('lost_wealth', 0)):,.0f}", delta=f"-₪{safe_format(res.get('lost_wealth', 0)):,.0f}", delta_color="inverse")

# --- TAB 2: ביטוח חיים ---
with tabs[1]:
    st.header("💡 מחשבון סכום ביטוח חיים מומלץ")
    # ... (Logic remains the same)

# --- TAB 3: משכנתה ---
with tabs[2]:
    st.header("🏠 מחשבון החזר משכנתה משוער")
    # ... (Logic remains the same)

# --- TAB 4: עמלות ---
with tabs[3]:
    st.header("💰 מחשבון עמלות סוכן")
    # ... (Logic remains the same)

if conn:
    conn.close()
