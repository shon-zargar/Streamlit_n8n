import streamlit as st
import pandas as pd
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go

from engines import (
    init_db, get_leads_data, calculate_avg_deal_size, calculate_conversion_rate
)

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="דשבורד מנהלים")

# --- Global Styling ---
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False
st.session_state.dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=st.session_state.dark_mode, key="dark_mode_toggle")

if st.session_state.dark_mode:
    PLOT_THEME = "plotly_dark"
    TEXT_COLOR = "#ffffff"
else:
    PLOT_THEME = "plotly_white"
    TEXT_COLOR = "#000000"

st.markdown(f"""
<style>
    .stApp, .main, .stMarkdown, p, h1, h2, h3, h4, h5, h6, span, label {{
        direction: rtl;
        text-align: right;
        font-family: 'Heebo', sans-serif;
        color: {TEXT_COLOR} !important;
    }}
    section[data-testid="stSidebar"] {{ direction: rtl; text-align: right; }}
    ul[role="listbox"] li {{ text-align: right; direction: rtl; }}
</style>
""", unsafe_allow_html=True)

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("📊 דשבורד מנהלים מתקדם")

df = get_leads_data(conn)

if df.empty:
    st.warning("אין נתונים להצגה. בדוק אם קובץ מסד הנתונים `leads_pro_ultimate.db` קיים ואינו ריק.")
else:
    # KPIs Row 1
    kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
    total_revenue = df[df['status'] == 'נמכר']['estimated_commission'].sum()
    kpi1.metric("💰 סה'כ הכנסות", f"₪{total_revenue:,.0f}")
    kpi2.metric("📊 סה'כ לידים", len(df))
    # ... (other KPIs)

    st.divider()

    # Charts
    chart1, chart2 = st.columns(2)
    with chart1:
        st.subheader("📊 התפלגות סטטוסים")
        status_counts = df['status'].value_counts()
        fig_status = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title="סטטוסי לידים",
            template=PLOT_THEME
        )
        st.plotly_chart(fig_status, use_container_width=True)

    # ... (other charts)
