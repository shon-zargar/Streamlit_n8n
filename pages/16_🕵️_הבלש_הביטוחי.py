import streamlit as st
import pandas as pd
import json

from engines import init_db, get_leads_data, AIEngine, setup_page_styling

# --- Page Configuration & Styling (RULE 1) ---
st.set_page_config(layout="wide", page_title="הבלש הביטוחי")
theme = setup_page_styling()

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
        
        # --- Card UI Refactoring (RULE 2) ---
        st.markdown(f"""
        <div style="background-color:{theme.get('card', '#f8f9fa')}; padding: 15px; border-radius: 10px; border: 1px solid {theme.get('border', '#ddd')};">
            **שם:** {lead['name']}  |  
            **סטטוס משפחתי:** {lead['marital_status']}  |  
            **ילדים:** {lead['children']}
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        st.subheader("🔍 ממצאים והזדמנויות")

        opportunities = AIEngine.identify_cross_sell(lead.to_dict())
        if opportunities:
            for opp in opportunities:
                st.warning(opp)
        else:
            st.success("✅ לא נמצאו פערים משמעותיים בכיסוי!")
            
        st.subheader("📍 פעולה מומלצת")
        next_action = AIEngine.suggest_next_action(lead.to_dict())
        st.info(next_action)
