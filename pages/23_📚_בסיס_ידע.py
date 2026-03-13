import streamlit as st
import pandas as pd

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="בסיס ידע", page_icon="📚")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. ייבוא בטוח מהמנוע ---
try:
    from engines import init_db, get_knowledge_base, setup_page_styling

    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבים ב-engines.py. פרטים: {e}")


    # פונקציית גיבוי למניעת קריסה
    def get_knowledge_base(conn=None):
        return pd.DataFrame([
            {"id": 1, "topic": "שגיאת מערכת", "content": "המנוע המרכזי לא נטען כראוי. לא ניתן להציג מידע."}
        ])


    theme = {}

# --- חיבור למסד נתונים ---
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None

# --- 4. ממשק המשתמש ---
st.title("📚 בסיס ידע מקצועי")
st.markdown("מאגר מידע, מאמרים מקצועיים, וסיכומי פוליסות לשליפה מהירה במהלך שיחות עם לקוחות.")

# --- 5. משיכת נתונים בטוחה ---
with st.spinner("טוען את מאגר המידע..."):
    try:
        # טיפול ב-TypeError למקרה שהמנוע הישן עדיין רץ בזיכרון השרת
        try:
            df_kb = get_knowledge_base(conn)
        except TypeError:
            df_kb = get_knowledge_base()
    except Exception as e:
        st.error(f"שגיאה בשליפת המידע: {e}")
        df_kb = pd.DataFrame()

# --- 6. תצוגת בסיס הידע ---
if df_kb.empty:
    st.info("📭 מאגר המידע ריק כרגע.")
else:
    # יצירת סרגל חיפוש חכם שלא קורס אם יש נתונים חסרים
    search_term = st.text_input("🔍 חפש במאגר (לפי נושא או תוכן):",
                                placeholder="למשל: פנסיה, אובדן כושר עבודה, בריאות...")

    # סינון הנתונים
    if search_term:
        # מסנן שורות שכוללות את מילת החיפוש בכל עמודה שהיא
        mask = df_kb.apply(lambda row: search_term.lower() in str(row.to_dict()).lower(), axis=1)
        display_df = df_kb[mask]
        st.caption(f"נמצאו {len(display_df)} תוצאות רלוונטיות עבור '{search_term}'")
    else:
        display_df = df_kb

    st.divider()

    if display_df.empty:
        st.warning("לא נמצאו מאמרים התואמים את החיפוש שלך.")
    else:
        # תצוגה בצורת אקורדיונים (Expanders) נוחים וקריאים
        for index, row in display_df.iterrows():
            topic = row.get('topic', 'ללא נושא')
            content = row.get('content', 'אין תוכן')

            with st.expander(f"📖 {topic}"):
                st.write(content)

                # מציג את התוכן בתיבת טקסט כדי שיהיה קל להעתיק ולשלוח ללקוח
                st.text_area("העתק טקסט מהיר לשליחה ללקוח:", value=content, height=100,
                             key=f"kb_txt_{row.get('id', index)}")

if conn:
    conn.close()