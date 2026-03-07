import streamlit as st
import time

from engines import init_db, get_templates

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="תבניות")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="templates_dark_mode")
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
st.title("📝 ניהול תבניות")

with st.expander("➕ יצירת תבנית חדשה"):
    with st.form("new_template"):
        temp_name = st.text_input("שם התבנית")
        temp_type = st.selectbox("סוג", ["WhatsApp", "Email", "SMS"])
        temp_content = st.text_area("תוכן", placeholder="שלום {name}, ...")
        if st.form_submit_button("💾 שמור תבנית"):
            conn.execute("INSERT INTO templates (name, type, content) VALUES (?, ?, ?)", (temp_name, temp_type, temp_content))
            conn.commit()
            st.success("✅ תבנית נשמרה!")
            time.sleep(0.5)
            st.rerun()

templates = get_templates(conn)
if not templates.empty:
    st.subheader("📚 תבניות שמורות")
    for _, temp in templates.iterrows():
        with st.expander(f"{temp['name']} ({temp['type']})"):
            st.code(temp['content'])
            if st.button("🗑️ מחק", key=f"del_temp_{temp['id']}"):
                conn.execute("DELETE FROM templates WHERE id=?", (temp['id'],))
                conn.commit()
                st.rerun()
else:
    st.info("אין תבניות שמורות")
