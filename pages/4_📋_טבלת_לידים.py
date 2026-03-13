import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import math
import json
import io

from engines import (
    init_db, get_leads_data, FinanceEngine, generate_hebrew_pdf,
    COMMISSION_RATES, setup_page_styling, N8nIntegration,
    AIEngine, AISalesCoach, get_smart_age_insights
)

# --- Page Configuration & Styling (RULE 1 & 2) ---
st.set_page_config(layout="wide", page_title="טבלת לידים")
theme = setup_page_styling()

# --- Constants & DB ---
ITEMS_PER_PAGE = 10
SOURCE_OPTIONS = ["פייסבוק", "גוגל", "חבר מביא חבר", "אינסטגרם", "טיקטוק", "רכישת לידים", "LinkedIn", "אתר אינטרנט", "אחר"]
STATUS_OPTIONS = ["חדש", "בטיפול", "לא עונה", "נמכר", "לא רלוונטי", "פגישה תואמה"]
conn = init_db()

# --- Main Page ---
st.title("📋 טבלת לידים - ניהול ועריכה")

df = get_leads_data(conn)

if df.empty:
    st.info("אין לידים במערכת")
    st.stop()

# --- Filters ---
with st.expander("🔍 סינון וחיפוש", expanded=True):
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    search_text = fcol1.text_input("חיפוש חופשי", placeholder="שם, טלפון, ת.ז...")
    filter_status = fcol2.multiselect("סטטוס", df['status'].unique())
    filter_source = fcol3.multiselect("מקור", df['source'].unique())
    min_comm = fcol4.number_input("עמלה מינימלית", 0, int(df['estimated_commission'].max() if not df.empty else 0), 0)

filtered = df.copy()
if search_text:
    filtered = filtered[
        filtered['name'].str.contains(search_text, case=False, na=False) |
        filtered['phone'].str.contains(search_text, case=False, na=False) |
        (filtered['id_number'].astype(str).str.contains(search_text, case=False, na=False) if 'id_number' in filtered.columns else False)
    ]
if filter_status:
    filtered = filtered[filtered['status'].isin(filter_status)]
if filter_source:
    filtered = filtered[filtered['source'].isin(filter_source)]
if min_comm > 0:
    filtered = filtered[filtered['estimated_commission'] >= min_comm]

st.caption(f"מציג {len(filtered)} מתוך {len(df)} לידים")

# --- Display Table ---
display_cols = ['name', 'phone', 'status', 'source', 'estimated_commission', 'callback_date']
display_df = filtered[display_cols].copy()
display_df.columns = ['שם', 'טלפון', 'סטטוס', 'מקור', 'עמלה', 'תאריך חזרה']
st.dataframe(display_df, use_container_width=True, hide_index=True)

# --- Detailed Edit & AI Coach ---
st.divider()
st.subheader("⚙️ אזור עבודה חכם - כרטיס לקוח")

lead_to_edit_id = st.selectbox("בחר ליד לעבודה שוטפת:", filtered['id'].tolist(), format_func=lambda x: f"{filtered.loc[filtered['id'] == x, 'name'].iloc[0]} (ID: {x})") if not filtered.empty else None

if lead_to_edit_id:
    lead_row_series = filtered[filtered['id'] == lead_to_edit_id].iloc[0]
    lead_row_dict = lead_row_series.to_dict()

    tab_edit, tab_ai = st.tabs(["✏️ עריכת פרטים וסטטוס", "🧠 תובנות AI (Sales Coach)"])

    with tab_edit:
        # ... (Detailed edit form logic remains here) ...
        pass

    with tab_ai:
        col_score, col_action, col_insights = st.columns(3)

        lead_score = AIEngine.calculate_lead_score(lead_row_dict, conn)
        with col_score:
            st.markdown("### 🎯 מדד חום (Lead Score)")
            st.success(f"**{lead_score}/100**")

        with col_action:
            st.markdown("### 📅 המלצה לפעולה")
            st.info(AIEngine.suggest_next_action(lead_row_dict))

        with col_insights:
            st.markdown("### 🎂 תובנות דמוגרפיות")
            # --- Corrected function call (RULE 4) ---
            age, age_insights = get_smart_age_insights(lead_row_dict.get('birth_date'))
            if age:
                st.markdown(f"**גיל:** {age}")
                for insight in age_insights: st.markdown(f"- {insight}")
            else:
                st.write("הזן תאריך לידה כדי לקבל תובנות.")
        
        # ... (Rest of the AI coach logic) ...

if conn:
    conn.close()
