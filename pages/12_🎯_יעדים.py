import streamlit as st
from datetime import datetime
import time

from engines import init_db, get_goals, get_leads_data

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="יעדים")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="goals_dark_mode")
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
st.title("🎯 ניהול יעדים חודשיים")

with st.expander("➕ הגדרת יעד חודשי"):
    with st.form("set_goal"):
        goal_month = st.date_input("חודש", datetime.now()).strftime('%Y-%m')
        goal_amount = st.number_input("יעד הכנסות (₪)", 0, 10000000, 50000, 1000)
        goal_deals = st.number_input("יעד עסקאות", 0, 1000, 10, 1)
        if st.form_submit_button("💾 שמור יעד"):
            existing = conn.execute("SELECT id FROM goals WHERE month=?", (goal_month,)).fetchone()
            if existing:
                conn.execute("UPDATE goals SET target_amount=?, target_deals=? WHERE month=?", (goal_amount, goal_deals, goal_month))
            else:
                conn.execute("INSERT INTO goals (month, target_amount, target_deals) VALUES (?, ?, ?)", (goal_month, goal_amount, goal_deals))
            conn.commit()
            st.success("✅ יעד נשמר!")
            time.sleep(0.5)
            st.rerun()

goals = get_goals(conn)
if not goals.empty:
    st.subheader("📊 יעדים והשגות")
    for _, goal in goals.iterrows():
        st.markdown(f"### {goal['month']}")
        # Logic to calculate and display progress would go here
        st.metric("💰 יעד הכנסות", f"₪{goal['target_amount']:,.0f}")
        st.metric("🎯 יעד עסקאות", goal['target_deals'])
        st.divider()
