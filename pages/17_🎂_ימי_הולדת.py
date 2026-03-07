import streamlit as st
import pandas as pd
from datetime import datetime

from engines import init_db, get_leads_data, generate_ai_blessing, generate_whatsapp_link, add_interaction

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="ימי הולדת")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="bday_dark_mode")
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
st.title("🎂 ימי הולדת היום - אוטומציה")
df = get_leads_data(conn)
today = datetime.now()

if not df.empty:
    df['birth_dt'] = pd.to_datetime(df['birth_date'], errors='coerce')
    birthdays_today = df[(df['birth_dt'].dt.month == today.month) & (df['birth_dt'].dt.day == today.day)]

    if birthdays_today.empty:
        st.info("🎈 אין ימי הולדת היום!")
    else:
        st.success(f"🎉 יש {len(birthdays_today)} ימי הולדת היום!")
        for idx, row in birthdays_today.iterrows():
            with st.expander(f"🎂 {row['name']} ({row['phone']})", expanded=True):
                default_msg = generate_ai_blessing(row['name'])
                final_blessing = st.text_area("✏️ ערוך ברכה:", value=default_msg, key=f"text_{row['id']}")
                st.link_button("💬 שלח ב-WhatsApp", generate_whatsapp_link(row['phone'], final_blessing), use_container_width=True)
                if st.button("📝 שמור כהערה", key=f"save_note_{row['id']}"):
                    add_interaction(conn, row['id'], "יום הולדת", f"נשלחה ברכה: {final_blessing}")
                    st.success("✅ נשמר!")
else:
    st.warning("אין לידים במערכת.")
