import streamlit as st
import pandas as pd
import json

from engines import init_db, get_leads_data, AIEngine

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="הבלש הביטוחי")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="detective_dark_mode")
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

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("🕵️‍♂️ הבלש הביטוחי - AI Insights")
st.caption("זיהוי אוטומטי של הזדמנויות ופערים בכיסוי")
df_leads = get_leads_data(conn)

if df_leads.empty:
    st.warning("אין לידים לניתוח")
else:
    detective_lead = st.selectbox("בחר לקוח לניתוח:", df_leads['id'].tolist(), format_func=lambda x: df_leads[df_leads['id'] == x]['name'].values[0])
    if detective_lead:
        lead = df_leads[df_leads['id'] == detective_lead].iloc[0]
        
        st.info(f"**שם:** {lead['name']} | **סטטוס משפחתי:** {lead['marital_status']} | **ילדים:** {lead['children']}")
        
        st.subheader("🔍 ממצאים")
        opportunities = AIEngine.identify_cross_sell(lead)
        if opportunities:
            for opp in opportunities:
                st.warning(opp)
        else:
            st.success("✅ לא נמצאו פערים משמעותיים בכיסוי!")
            
        st.subheader("📍 פעולה מומלצת")
        next_action = AIEngine.suggest_next_action(lead)
        st.info(next_action)
