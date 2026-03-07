import streamlit as st

from engines import init_db, get_leads_data, AISalesCoach, AIEngine

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="AI Sales Coach")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="coach_dark_mode")
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
st.title("🧠 AI Sales Coach")
st.subheader("ניתוח חכם ותובנות לסגירת עסקאות")

df = get_leads_data(conn)
if df.empty:
    st.warning("אין לידים במערכת לניתוח.")
else:
    selected_coach_lead = st.selectbox("בחר ליד לניתוח:", df['id'].tolist(), format_func=lambda x: df[df['id'] == x]['name'].values[0])
    lead_data = df[df['id'] == selected_coach_lead].iloc[0]

    if st.button("🔍 נתח אינטראקציות ותן טיפים לסגירה"):
        with st.spinner("ה-AI מנתח את התיק..."):
            analysis = AISalesCoach.analyze_sales_notes(lead_data['notes'])
            st.metric("סנטימנט בשיחה", analysis.get("sentiment", "ניטרלי"))
            
            if analysis.get("tasks"):
                st.write("**משימות אוטומטיות שנגזרו:**")
                for t in analysis["tasks"]:
                    st.info(t)
            
            if analysis.get("tips"):
                st.write("**טיפים לסגירה:**")
                for t in analysis["tips"]:
                    st.success(t)
