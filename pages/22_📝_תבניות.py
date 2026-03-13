import streamlit as st
import pandas as pd
import time

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="תבניות", page_icon="📝")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. ייבוא בטוח מהמנוע ---
try:
    from engines import init_db, get_templates, setup_page_styling

    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבים ב-engines.py. פרטים: {e}")


    # פונקציית גיבוי למניעת קריסה מוחלטת
    def get_templates(conn=None):
        return pd.DataFrame([
            {"id": 1, "name": "הודעת שגיאה", "content": "חסר חיבור למנוע התבניות המרכזי."}
        ])

# --- חיבור למסד נתונים ---
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None

# --- 4. ממשק המשתמש ---
st.title("📝 מאגר תבניות טקסט")
st.markdown("כאן תוכל למצוא תבניות הודעה מוכנות מראש (WhatsApp, אימייל, SMS) לשימוש מהיר מול הלקוחות שלך.")

# --- 5. משיכת נתונים בטוחה ---
with st.spinner("טוען תבניות מהמערכת..."):
    try:
        # טיפול ב-TypeError למקרה שהמנוע הישן עדיין רץ בזיכרון
        try:
            df_templates = get_templates(conn)
        except TypeError:
            df_templates = get_templates()
    except Exception as e:
        st.error(f"שגיאה בשליפת תבניות: {e}")
        df_templates = pd.DataFrame()

# --- 6. תצוגת התבניות ---
if df_templates.empty:
    st.info("📭 אין תבניות במערכת כרגע. תוכל להוסיף תבניות חדשות דרך מנוע הניהול.")
else:
    st.success(f"נטענו {len(df_templates)} תבניות בהצלחה.")
    st.divider()

    # תצוגת רשת (Grid) של 3 עמודות
    cols = st.columns(3)

    for index, row in df_templates.iterrows():
        # שימוש במכולה מעוצבת לכל תבנית
        with cols[index % 3].container(border=True):
            template_name = row.get('name', f"תבנית מספר {index + 1}")
            template_content = row.get('content', '')

            st.subheader(f"📌 {template_name}")

            # Text area מאפשר למשתמש להעתיק את הטקסט בקלות
            st.text_area(
                "תוכן ההודעה (העתק לשימוש):",
                value=template_content,
                height=150,
                key=f"tpl_{row.get('id', index)}"
            )

            # כפתור פעולה קטן שנותן פידבק
            if st.button("✅ העתקתי את התוכן", key=f"btn_{row.get('id', index)}", use_container_width=True):
                st.toast("מצוין! כעת תוכל להדביק את התבנית בוואטסאפ או במייל.")
                time.sleep(0.5)

if conn:
    conn.close()