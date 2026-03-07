import streamlit as st
import time

from engines import init_db, get_knowledge_base

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="בסיס ידע")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="kb_dark_mode")
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
st.title("📚 מרכז ידע ולמידה")

with st.expander("➕ הוספת מאמר"):
    with st.form("new_article"):
        art_title = st.text_input("כותרת")
        art_category = st.selectbox("קטגוריה", ["מוצרי ביטוח", "טכניקות מכירה", "חוקים ותקנות", "אחר"])
        art_content = st.text_area("תוכן", height=200)
        if st.form_submit_button("💾 שמור מאמר"):
            conn.execute("INSERT INTO knowledge_base (title, category, content) VALUES (?, ?, ?)", (art_title, art_category, art_content))
            conn.commit()
            st.success("✅ מאמר נשמר!")
            time.sleep(0.5)
            st.rerun()

kb = get_knowledge_base(conn)
if not kb.empty:
    cat_filter = st.selectbox("סינון לפי קטגוריה", ["הכל"] + kb['category'].unique().tolist())
    if cat_filter != "הכל":
        kb = kb[kb['category'] == cat_filter]
    
    st.subheader(f"📖 מאמרים ({len(kb)})")
    for _, article in kb.iterrows():
        with st.expander(f"📄 {article['title']}"):
            st.markdown(article['content'])
else:
    st.info("אין מאמרים בבסיס הידע")
