import streamlit as st
import base64

from engines import init_db, get_leads_data

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="פורטל לקוחות")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="portal_dark_mode")
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
st.title("🔗 מחולל לינק ללקוח")
df = get_leads_data(conn)
if not df.empty:
    selected_lead = st.selectbox("בחר לקוח:", df['id'].tolist(), format_func=lambda x: df[df['id']==x]['name'].values[0])
    if selected_lead:
        token = base64.b64encode(str(selected_lead).encode()).decode()
        # Replace with your actual Streamlit Cloud URL
        link = f"https://your-app.streamlit.app/?portal_token={token}" 
        st.code(link)
        st.info("שלח את הלינק הזה ללקוח בוואטסאפ")
else:
    st.warning("אין לקוחות במערכת.")
