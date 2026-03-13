import streamlit as st
import pandas as pd
import plotly.express as px
from collections import defaultdict
import json

from engines import (
    init_db, get_leads_data, calculate_smart_commission, 
    setup_page_styling, get_monthly_stats
)

# --- Page Configuration & Styling (RULE 1) ---
st.set_page_config(layout="wide", page_title="דוחות ותובנות")
theme = setup_page_styling()

# --- Database Connection ---
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None
    st.stop()

# --- Main Page ---
st.title("📊 דוחות ביצועים ותובנות עסקיות")
df = get_leads_data(conn)

if df.empty:
    st.warning("אין נתונים לניתוח.")
else:
    insight_tabs = st.tabs(["📈 תובנות עסקיות", "📅 ניתוח זמנים", "💰 ניתוח כספי"])
    
    with insight_tabs[0]:
        st.header("🧠 תובנות עסקיות")
        closed = df[df['status'] == 'נמכר']
        if not closed.empty:
            best_source = closed.groupby('source')['estimated_commission'].sum().idxmax()
            st.success(f"💡 **המקור הכי רווחי:** {best_source}")
        else:
            st.info("אין מספיק נתוני מכירות כדי להפיק תובנות על מקורות רווחיים.")

    with insight_tabs[1]:
        st.header("📅 ניתוח זמנים")
        monthly_stats = get_monthly_stats(conn)
        if not monthly_stats.empty:
            # --- Chart Theming (RULE 3) ---
            fig_monthly = px.line(
                monthly_stats,
                x='month',
                y='count',
                title="קצב כניסת לידים חודשי",
                labels={'month': 'חודש', 'count': 'כמות לידים'},
                template=theme.get('plot', 'plotly_white'),
                markers=True
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
        else:
            st.info("אין נתונים להצגת מגמה חודשית.")

    with insight_tabs[2]:
        st.header("💰 ניתוח כספי")
        product_revenue = defaultdict(float)
        closed = df[df['status'] == 'נמכר']
        if not closed.empty:
            for _, row in closed.iterrows():
                try:
                    policies = json.loads(row['policies_json'])
                    for p in policies:
                        if 'company' in p and 'type' in p and 'prem' in p:
                            comm = calculate_smart_commission(p['company'], p['type'], p['prem'])
                            product_revenue[p['type']] += comm
                except (json.JSONDecodeError, TypeError):
                    continue
            
            if product_revenue:
                revenue_df = pd.DataFrame(list(product_revenue.items()), columns=['מוצר', 'עמלה'])
                # --- Chart Theming (RULE 3) ---
                fig_prod = px.bar(
                    revenue_df,
                    x='מוצר',
                    y='עמלה',
                    title="הכנסות לפי מוצר",
                    template=theme.get('plot', 'plotly_white')
                )
                st.plotly_chart(fig_prod, use_container_width=True)
            else:
                st.info("לא נמצאו נתוני פוליסות תקינים לניתוח הכנסות.")
        else:
            st.info("אין מכירות לניתוח הכנסות.")

if conn:
    conn.close()
