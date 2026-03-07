import streamlit as st

from engines import init_db, get_leads_data, AutomationHub, add_interaction

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Automation Hub")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="auto_dark_mode")
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
st.title("🤖 Automation Hub (Playwright)")
st.subheader("משיכת נתונים אוטומטית מהר הביטוח")

df = get_leads_data(conn)
if df.empty:
    st.warning("אין לקוחות במערכת לשיוך הנתונים.")
else:
    target_lead = st.selectbox("בחר לקוח לשיוך הנתונים:", df['id'].tolist(), format_func=lambda x: df[df['id'] == x]['name'].values[0])
    with st.form("playwright_form"):
        id_number = st.text_input("תעודת זהות")
        issue_date = st.date_input("תאריך הנפקת תעודת זהות")
        if st.form_submit_button("🚀 הפעל אוטומציה"):
            if id_number:
                with st.spinner("מפעיל Playwright ברקע..."):
                    success, result_msg = AutomationHub.run_har_habituch_scraper(id_number, "dummy_pass", issue_date)
                    if success:
                        st.success(f"✅ הפעולה הושלמה: {result_msg}")
                        add_interaction(conn, target_lead, "אוטומציה", "משיכת נתונים אוטומטית מהר הביטוח הושלמה")
                    else:
                        st.error(f"❌ תקלה באוטומציה: {result_msg}")
            else:
                st.error("חובה להזין תעודת זהות")
