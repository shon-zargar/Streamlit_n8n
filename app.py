import streamlit as st
import pandas as pd
from datetime import datetime
import random
import threading
from flask import Flask, jsonify

# Import necessary functions for the main page and global setup
from engines import (
    init_db, get_stats, setup_page_styling, get_leads_data, 
    calculate_conversion_rate
)

# ==========================================
# 1. Page Configuration & Global Styling
# ==========================================
st.set_page_config(
    page_title="LeadFlow Pro X - Ultimate",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Run the global styling function from engines.py
theme = setup_page_styling()

# --- Database Connection ---
conn = init_db()

# --- API Server (Optional) ---
app = Flask(__name__)
@app.route('/stats')
def api_stats():
    data = get_stats()
    return jsonify(data)

def run_api():
    app.run(port=8502, host='0.0.0.0', debug=False, use_reloader=False)

if not any(t.name == "n8n_api" for t in threading.enumerate()):
    threading.Thread(target=run_api, name="n8n_api", daemon=True).start()

# ==========================================
# 2. Main Home Page Content
# ==========================================
st.title("🏠 ברוכים הבאים ל-LeadFlow Pro X Ultimate")

st.markdown(f"""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 40px; border-radius: 15px; text-align: center; color: white; margin-bottom: 30px;'>
    <h1 style='color: white; margin: 0;'>💎 LeadFlow Pro X Ultimate</h1>
    <p style='font-size: 1.2em; margin-top: 10px; color: white;'>
        מערכת ניהול לידים מתקדמת עם AI, אוטומציות ותובנות בזמן אמת
    </p>
</div>
""", unsafe_allow_html=True)

# --- Quick Actions ---
st.subheader("⚡ פעולות מהירות")
qcol1, qcol2, qcol3, qcol4 = st.columns(4)

with qcol1:
    if st.button("➕ ליד חדש", use_container_width=True, type="primary"):
        st.switch_page("pages/9_➕_ליד_חדש.py")
with qcol2:
    if st.button("📊 דשבורד", use_container_width=True):
        st.switch_page("pages/1_📊_דשבורד_מנהלים.py")
with qcol3:
    if st.button("🎯 Focus", use_container_width=True):
        st.switch_page("pages/10_🎯_Focus_Mode.py")
with qcol4:
    if st.button("📋 טבלת לידים", use_container_width=True):
        st.switch_page("pages/4_📋_טבלת_לידים.py")

st.divider()

# --- Today's Summary ---
col1, col2, col3, col4 = st.columns(4)
df_home = get_leads_data(conn)

if not df_home.empty:
    today = datetime.now().strftime('%Y-%m-%d')
    urgent_today = len(df_home[(df_home['callback_date'] <= today) & (~df_home['status'].isin(['נמכר', 'לא רלוונטי']))])
    
    current_month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')
    month_sales_df = df_home[(df_home['status'] == 'נמכר') & (df_home['created_at'] >= current_month_start)]
    month_sales = len(month_sales_df)
    month_revenue = month_sales_df['estimated_commission'].sum()

    col1.metric("🚨 דחופים להיום", urgent_today)
    col2.metric("💰 הכנסות החודש", f"₪{month_revenue:,.0f}")
    col3.metric("✅ מכירות החודש", month_sales)
    col4.metric("📊 Conversion Rate", f"{calculate_conversion_rate(conn):.1f}%")

st.divider()

# --- Recent Activity ---
st.subheader("🕐 פעילות אחרונה")
if not df_home.empty:
    recent = df_home.head(5)[['name', 'phone', 'status', 'callback_date', 'estimated_commission']]
    recent.columns = ['שם', 'טלפון', 'סטטוס', 'חזרה', 'עמלה']
    st.dataframe(recent, use_container_width=True, hide_index=True)
else:
    st.info("אין לידים במערכת. התחל בהוספת ליד ראשון!")

# --- Tips ---
st.divider()
st.subheader("💡 טיפים מהירים")
tips = [
    "השתמש ב-Focus Mode לניהול משימות יומיות ממוקד.",
    "הגדר יעדים חודשיים כדי לעקוב אחרי ההתקדמות.",
    "השתמש בתבניות להאצת התקשורת עם לקוחות.",
    "בדוק את 'הבלש הביטוחי' לזיהוי הזדמנויות cross-sell.",
    "גבה את המערכת באופן קבוע דרך מסך ההגדרות."
]
st.info(f"💡 {random.choice(tips)}")
