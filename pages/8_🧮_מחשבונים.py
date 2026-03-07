import streamlit as st
import pandas as pd
import plotly.express as px

from engines import FinanceEngine

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="מחשבונים")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="calc_dark_mode")
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


# --- Main Page ---
st.title("🧮 מחשבונים פיננסיים")
calc_tabs = st.tabs(["🏦 פרישה בסיסי", "💸 דמי ניהול", "📊 תשואה מורכבת", "🏠 החזר הלוואה"])

with calc_tabs[0]:
    st.header("🏦 סימולטור פנסיוני פשוט")
    r_age = st.number_input("גיל נוכחי", 20, 67, 30)
    r_salary = st.number_input("שכר חודשי (₪)", 5000, 100000, 15000, 500)
    r_accumulation = st.number_input("צבירה נוכחית (₪)", 0, 5000000, 100000, 10000)
    years_to_retire = 67 - r_age
    future_value = r_accumulation * (1.05 ** years_to_retire) + (r_salary * 0.185 * 12) * ((1.05 ** years_to_retire - 1) / 0.05)
    st.metric("💰 צבירה צפויה", f"₪{future_value:,.0f}")

with calc_tabs[1]:
    st.header("💸 השפעת דמי ניהול")
    f_balance = st.number_input("צבירה (₪)", 0, 5000000, 200000, 10000, key="f_b")
    f_monthly = st.number_input("הפקדה חודשית (₪)", 0, 20000, 2000, 100, key="f_m")
    f_years = st.slider("תקופה (שנים)", 5, 40, 25, key="f_y")
    
    res = FinanceEngine.project_fee_impact(f_balance, f_monthly, f_years, 0.05, 0.02, 0.01)
    st.metric("💸 הפסד צפוי מדמי ניהול גבוהים", f"₪{res['lost_wealth']:,.0f}")

with calc_tabs[2]:
    st.header("📊 מחשבון תשואה מורכבת")
    c_initial = st.number_input("השקעה ראשונית (₪)", 0, 10000000, 100000, 5000)
    c_monthly = st.number_input("הוספה חודשית (₪)", 0, 50000, 1000, 100)
    c_rate = st.slider("תשואה שנתית (%)", 1.0, 15.0, 6.0, 0.5)
    c_years = st.slider("תקופה (שנים)", 1, 50, 20, 1)
    
    months = c_years * 12
    monthly_rate = c_rate / 100 / 12
    future_val = c_initial * ((1 + monthly_rate) ** months) + c_monthly * (((1 + monthly_rate) ** months - 1) / monthly_rate)
    st.metric("💰 ערך עתידי", f"₪{future_val:,.0f}")

with calc_tabs[3]:
    st.header("🏠 מחשבון החזר הלוואה")
    l_principal = st.number_input("סכום הלוואה (₪)", 50000, 10000000, 500000, 10000)
    l_rate = st.number_input("ריבית שנתית (%)", 1.0, 15.0, 4.0, 0.1)
    l_years = st.number_input("תקופה (שנים)", 1, 30, 20, 1)
    
    payment = FinanceEngine.calculate_mortgage_payment(l_principal, l_rate, l_years)
    st.metric("💳 החזר חודשי", f"₪{payment:,.0f}")
