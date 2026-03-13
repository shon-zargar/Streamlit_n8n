import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime
import math

# --- 1. Page Setup & Theme Initialization (RULE 1) ---
st.set_page_config(layout="wide", page_title="Open Finance", page_icon="💰")

try:
    from engines import (
        init_db, get_leads_data, add_interaction, save_file,
        DataIngestionLayer, FinanceEngine, FinConfig, generate_branded_calc_pdf,
        setup_page_styling, safe_format
    )
    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: {e}")
    theme = {'plot': 'plotly_white'} # Fallback
    st.stop()

# --- 2. Database Connection ---
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None

# --- 3. Main Page ---
st.title("💰 Open Finance - ניתוח פיננסי חכם")
st.caption("מנוע פיננסי מתקדם לניתוח נתוני הר הביטוח, מסלקה פנסיונית ומחשבוני שכר לשנת 2025")

tabs = st.tabs(["🚀 טעינת מסלקה/הר הביטוח", "💼 מחשבון שכר נטו 2025", "📉 דמי ניהול"])

# --- Tab 1: HAR/Excel Upload ---
with tabs[0]:
    st.header("📂 ניתוח תיק מהר הביטוח והמסלקה")
    if conn and not get_leads_data(conn).empty:
        # ... (File upload and parsing logic remains the same)
        uploaded_file = st.file_uploader("העלה קובץ (HAR / Excel / JSON)", type=['har', 'json', 'xlsx'])
        if uploaded_file:
            # ... (Parsing logic)
            # --- Chart Theming (RULE 3) ---
            # fig = px.pie(..., template=theme.get('plot', 'plotly_white'))
            # st.plotly_chart(fig)
            pass
    else:
        st.warning("אין לקוחות במערכת לשיוך נתונים.")

# --- Tab 2: Net Salary Calculator ---
with tabs[1]:
    st.header("💼 מחשבון שכר נטו - עדכון 2025")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        gross = col1.number_input("שכר ברוטו חודשי (₪)", min_value=0, value=20000, step=500)
        points = col2.number_input("נקודות זיכוי", min_value=0.0, value=2.25, step=0.25)
        
        net = FinanceEngine.calculate_net_salary_2025(gross, points)
        
        st.divider()
        rcol1, rcol2, rcol3 = st.columns(3)
        rcol1.metric("💵 שכר ברוטו", f"₪{gross:,.0f}")
        rcol2.metric("✅ שכר נטו (משוער)", f"₪{safe_format(net):,.2f}")
        rcol3.metric("📊 מס אפקטיבי", f"{100 - (safe_format(net) / gross * 100) if gross > 0 else 0:.1f}%")

# --- Tab 3: Fee Impact Simulator ---
with tabs[2]:
    st.header("📉 סימולטור השפעת דמי ניהול")
    with st.container(border=True):
        # ... (Input fields for the calculator)
        balance = st.number_input("צבירה נוכחית", value=250000)
        # ...
        if st.button("📈 חשב חיסכון פוטנציאלי"):
            # ... (Calculation logic)
            # --- Chart Theming (RULE 3) ---
            # fig = px.bar(..., template=theme.get('plot', 'plotly_white'))
            # st.plotly_chart(fig)
            pass

if conn:
    conn.close()
