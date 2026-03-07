import streamlit as st
from streamlit_calendar import calendar

from engines import init_db, get_leads_data, generate_whatsapp_link

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="יומן פגישות")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="calendar_dark_mode")
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
st.title("📅 יומן פגישות ומשימות ויזואלי")
calendar_events = []
df = get_leads_data(conn)
for _, row in df.iterrows():
    if row['callback_date']:
        calendar_events.append({
            "title": f"📞 {row['name']}",
            "start": row['callback_date'],
            "extendedProps": {"phone": row['phone'], "status": row['status']}
        })

calendar_options = {
    "headerToolbar": {"left": "today prev,next", "center": "title", "right": "dayGridMonth,timeGridWeek"},
    "initialView": "dayGridMonth", "direction": "rtl", "locale": "he"
}

state = calendar(events=calendar_events, options=calendar_options, key="crm_calendar")

if state and state.get("eventClick"):
    event = state["eventClick"]["event"]
    st.sidebar.subheader("📋 פרטי פגישה")
    st.sidebar.write(f"**לקוח:** {event['title']}")
    st.sidebar.link_button("💬 וואטסאפ", generate_whatsapp_link(event['extendedProps']['phone']))
