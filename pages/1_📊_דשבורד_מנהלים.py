import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- 1. Page Setup & Theme Initialization (RULE 1) ---
st.set_page_config(layout="wide", page_title="דשבורד מנהלים", page_icon="📊")

try:
    from engines import init_db, get_leads_data, setup_page_styling
    theme = setup_page_styling()
except ImportError:
    st.error("שגיאה בטעינת קובצי המערכת (engines.py).")
    # Fallback theme to prevent app crash
    theme = {"plot": "plotly_white"} 
    st.stop()

# --- 2. Main Page ---
st.title("📊 דשבורד מנהלים")
st.markdown("כאן תוכל לראות את ביצועי העסק בזמן אמת, מבוסס על נתוני הלידים והעסקאות.")

# --- Database Connection ---
conn = init_db()
df = get_leads_data(conn)

if df.empty:
    st.warning("📭 אין כרגע נתונים במערכת. הוסף לידים כדי לראות את הדשבורד בפעולה.")
else:
    # --- Sidebar Filters ---
    st.sidebar.header("סינון נתונים")
    if 'status' in df.columns:
        status_options = df['status'].unique().tolist()
        selected_statuses = st.sidebar.multiselect("בחר סטטוסים:", status_options, default=status_options)
        filtered_df = df[df['status'].isin(selected_statuses)]
    else:
        filtered_df = df

    # --- KPI Cards ---
    st.subheader("מדדי מפתח")
    col1, col2, col3 = st.columns(3)
    col1.metric("סה״כ לידים (בסינון הנוכחי)", len(filtered_df))
    if 'estimated_commission' in filtered_df.columns and 'status' in filtered_df.columns:
        total_rev = filtered_df[filtered_df['status'] == 'נמכר']['estimated_commission'].sum()
        col2.metric("הכנסות ממכירות", f"₪{total_rev:,.0f}")
    else:
        col2.metric("הכנסות ממכירות", "₪0")
    if 'lead_score' in filtered_df.columns:
        avg_score = filtered_df['lead_score'].mean()
        col3.metric("איכות ליד ממוצעת", f"{avg_score:.1f}/100")
    else:
        col3.metric("איכות ליד ממוצעת", "לא ידוע")

    st.divider()

    # --- Plotly Charts ---
    chart_col1, chart_col2 = st.columns(2)
    with chart_col1:
        st.subheader("פילוח לידים לפי סטטוס")
        if 'status' in filtered_df.columns and not filtered_df.empty:
            status_counts = filtered_df['status'].value_counts().reset_index()
            status_counts.columns = ['סטטוס', 'כמות']
            
            # --- Chart Theming (RULE 3) ---
            fig_status = px.pie(
                status_counts,
                names='סטטוס',
                values='כמות',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Pastel,
                template=theme.get('plot', 'plotly_white')
            )
            fig_status.update_layout(font=dict(family="Heebo, Arial, sans-serif"))
            st.plotly_chart(fig_status, use_container_width=True)
        else:
            st.info("אין נתוני סטטוס להצגה.")

    with chart_col2:
        st.subheader("מקורות הגעה (Sources)")
        if 'source' in filtered_df.columns and not filtered_df.empty:
            source_counts = filtered_df['source'].value_counts().reset_index()
            source_counts.columns = ['מקור', 'כמות']

            # --- Chart Theming (RULE 3) ---
            fig_source = px.bar(
                source_counts,
                x='מקור',
                y='כמות',
                color='מקור',
                color_discrete_sequence=px.colors.qualitative.Set2,
                template=theme.get('plot', 'plotly_white')
            )
            fig_source.update_layout(font=dict(family="Heebo, Arial, sans-serif"), showlegend=False)
            st.plotly_chart(fig_source, use_container_width=True)
        else:
            st.info("אין נתוני מקור להצגה.")
