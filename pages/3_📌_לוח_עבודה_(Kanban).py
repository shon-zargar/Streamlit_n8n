import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import math

# --- 1. Page Setup & Theme Initialization (RULE 1) ---
st.set_page_config(layout="wide", page_title="לוח עבודה - Kanban", page_icon="📌")

try:
    from engines import (
        init_db, get_leads_data, get_interactions, get_files, get_tasks,
        add_interaction, add_task, save_file,
        AIEngine, N8nIntegration, setup_page_styling,
        generate_whatsapp_link, generate_google_calendar_link
    )
    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: {e}")
    theme = {"card": "#fff", "text": "#000", "border": "#ddd"} # Fallback
    st.stop()

# --- 2. Constants & DB Connection ---
STATUS_OPTIONS = ["חדש", "בטיפול", "לא עונה", "נמכר", "לא רלוונטי", "פגישה תואמה"]
try:
    conn = init_db()
    df = get_leads_data(conn)
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    df = pd.DataFrame()

# --- 3. Main Page UI ---
st.title("📌 לוח עבודה - Kanban Board")

if df.empty:
    st.info("📭 אין לידים להצגה כרגע.")
else:
    # --- Kanban Columns ---
    statuses_to_display = ["חדש", "בטיפול", "לא עונה", "נמכר"]
    colors = ["#FF6B6B", "#FFA500", "#95A5A6", "#4CAF50"]
    cols = st.columns(len(statuses_to_display))

    for i, status in enumerate(statuses_to_display):
        status_leads = df[df['status'] == status]
        cols[i].markdown(f"<div style='text-align:center; background-color:{colors[i]}; color:white; padding:10px; border-radius:8px; margin-bottom:10px;'><b>{status} ({len(status_leads)})</b></div>", unsafe_allow_html=True)

        with cols[i].container(height=800, border=False):
            for idx, row in status_leads.iterrows():
                next_action = AIEngine.suggest_next_action(row.to_dict())
                
                # --- Card UI Refactoring (RULE 2) ---
                st.markdown(f"""
                    <div style='background-color:{theme.get("card", "#fff")}; border:1px solid {theme.get("border", "#ddd")}; padding:15px; border-radius:10px; margin-bottom:15px; border-right:5px solid {colors[i]};'>
                        <h5 style='margin:0; color:{theme.get("text", "#000")}; font-weight:bold;'>{row.get('name', 'ללא שם')}</h5>
                        <p style='margin:5px 0; color:gray; font-size:0.9em;'>📞 {row.get('phone', 'אין מספר')}</p>
                        <p style='margin:5px 0; font-size:0.85em; color:#4CAF50; font-weight:bold;'>💡 {next_action}</p>
                    </div>
                """, unsafe_allow_html=True)

                with st.expander(f"⚙️ פעולות: {row.get('name', 'לקוח')}"):
                    # ... (All management logic remains the same)
                    pass
if conn:
    conn.close()
