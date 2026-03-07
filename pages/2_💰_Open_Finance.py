import streamlit as st
import pandas as pd
import plotly.express as px

from engines import (
    init_db, get_leads_data, add_interaction, save_file,
    DataIngestionLayer, FinanceEngine, FinConfig, generate_branded_calc_pdf
)
from datetime import date, datetime

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Open Finance")

# --- Global Styling ---
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False
st.session_state.dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=st.session_state.dark_mode, key="dark_mode_toggle")

TEXT_COLOR = "#ffffff" if st.session_state.dark_mode else "#000000"

st.markdown(f"""
<style>
    .stApp, .main, .stMarkdown, p, h1, h2, h3, h4, h5, h6, span, label {{
        direction: rtl;
        text-align: right;
        font-family: 'Heebo', sans-serif;
        color: {TEXT_COLOR} !important;
    }}
    section[data-testid="stSidebar"] {{ direction: rtl; text-align: right; }}
</style>
""", unsafe_allow_html=True)

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("💰 Open Finance Israel 2025")
# ... (rest of the page logic)
tabs = st.tabs(["🚀 טעינת HAR", "🧠 מס 2025", "📉 דמי ניהול", "👴 תיקון 190", "💡 ביטוח חיים", "🏠 משכנתה"])
# ...
