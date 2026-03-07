import streamlit as st
import pandas as pd
from collections import defaultdict

from engines import init_db, get_leads_data, calculate_smart_commission

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="דוחות ותובנות")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="insights_dark_mode")
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
st.title("📊 Business Intelligence & Insights")
df = get_leads_data(conn)

if df.empty:
    st.warning("אין נתונים לניתוח")
else:
    insight_tabs = st.tabs(["📈 תובנות עסקיות", "📅 ניתוח זמנים", "💰 ניתוח כספי"])
    
    with insight_tabs[0]:
        st.header("🧠 תובנות עסקיות")
        closed = df[df['status'] == 'נמכר']
        if not closed.empty:
            best_source = closed.groupby('source')['estimated_commission'].sum().idxmax()
            st.success(f"💡 **המקור הכי רווחי:** {best_source}")

    with insight_tabs[1]:
        st.header("📅 ניתוח זמנים")
        df['month'] = pd.to_datetime(df['created_at']).dt.to_period('M')
        monthly_leads = df.groupby('month').size()
        st.line_chart(monthly_leads)

    with insight_tabs[2]:
        st.header("💰 ניתוח כספי")
        product_revenue = defaultdict(float)
        closed = df[df['status'] == 'נמכר']
        for _, row in closed.iterrows():
            try:
                # Use json.loads which is more robust for this structure
                policies = json.loads(row['policies_json'])
                for p in policies:
                    comm = calculate_smart_commission(p['company'], p['type'], p['prem'])
                    product_revenue[p['type']] += comm
            except:
                pass
        if product_revenue:
            st.bar_chart(product_revenue)
