import streamlit as st
import sqlite3
import json
from datetime import datetime, date
import time

# --- 1. הגדרת העמוד ---
st.set_page_config(layout="wide", page_title="ליד חדש", page_icon="➕")

# --- 2. אבטחה וניהול זיכרון ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. טעינה מאובטחת של המנוע ---
try:
    from engines import init_db, setup_page_styling

    setup_page_styling()
except ImportError:
    st.error("שגיאה בטעינת קובצי המערכת (engines.py). ודא שאתה מריץ מהתיקייה הראשית.")
    st.stop()

st.title("➕ הוספת ליד חדש למערכת")
st.markdown("מלא את פרטי הלקוח. שדות המסומנים ב-**(*)** הם חובה. את שאר הנתונים תוכל להשלים מאוחר יותר מכרטיס הלקוח.")

# --- טופס הזנת נתונים מורחב ---
with st.form("new_lead_form", clear_on_submit=False):
    # --- פרטי קשר ---
    st.subheader("📞 פרטי יצירת קשר")
    col1, col2, col3, col4 = st.columns(4)
    name = col1.text_input("שם מלא *", placeholder="ישראל ישראלי")
    phone = col2.text_input("טלפון *", placeholder="050-0000000")
    email = col3.text_input("כתובת אימייל", placeholder="example@gmail.com")
    source_options = ["פייסבוק", "גוגל", "חבר מביא חבר", "אינסטגרם", "טיקטוק", "וואטסאפ", "שיחה נכנסת", "אתר אינטרנט",
                      "אחר"]
    source = col4.selectbox("מקור הגעה", source_options)

    st.divider()

    # --- פרטי זיהוי ודמוגרפיה ---
    st.subheader("🪪 פרטי זיהוי ודמוגרפיה")
    col_id1, col_id2, col_id3 = st.columns(3)
    id_number = col_id1.text_input("מספר תעודת זהות")
    issue_date = col_id2.text_input("תאריך הנפקה (לדוגמה: 01/01/2020)")
    expiry_date = col_id3.text_input("תאריך תוקף (לדוגמה: 01/01/2030)")

    col_dem1, col_dem2, col_dem3 = st.columns(3)
    birth_date = col_dem1.date_input("תאריך לידה", value=None, min_value=date(1920, 1, 1),
                                     max_value=datetime.now().date())
    marital_status = col_dem2.selectbox("סטטוס משפחתי", ["", "רווק/ה", "נשוי/ה", "גרוש/ה", "אלמן/ה"])
    children = col_dem3.number_input("מספר ילדים", min_value=0, max_value=20, value=0, step=1)

    st.divider()

    # --- תזמון והערות ---
    st.subheader("🗓️ תזמון והערות")
    col_time1, col_time2 = st.columns(2)
    callback_date = col_time1.date_input("תאריך לחזרה מתוכנן", value=datetime.now().date())
    renewal_date = col_time2.date_input("תאריך לחידוש ביטוח (אופציונלי)", value=None)

    notes = st.text_area("הערות ראשוניות (מה הלקוח מחפש? צרכים מיוחדים?)", height=100)

    st.divider()

    # --- כפתור שמירה ---
    submit_btn = st.form_submit_button("💾 שמור וצור תיק לקוח", type="primary", use_container_width=True)

    if submit_btn:
        # בדיקת ולידציה לשדות חובה
        if not name or not phone:
            st.error("⚠️ נא למלא את שדות החובה: שם וטלפון.")
        else:
            with st.spinner("מקים תיק לקוח ושומר נתונים..."):
                try:
                    conn = init_db()
                    cursor = conn.cursor()

                    # יצירת מבנה ברירת מחדל לפוליסות כדי למנוע קריסה בכרטיס הלקוח
                    policies_json = json.dumps([{"type": "בחר...", "company": "בחר...", "prem": 0}], ensure_ascii=False)

                    # המרת תאריכים למחרוזות שמתאימות ל-SQLite
                    b_date_str = birth_date.strftime('%Y-%m-%d') if birth_date else None
                    c_date_str = callback_date.strftime('%Y-%m-%d') if callback_date else datetime.now().strftime(
                        '%Y-%m-%d')
                    r_date_str = renewal_date.strftime('%Y-%m-%d') if renewal_date else None

                    # הכנסה בטוחה ומלאה למסד הנתונים
                    cursor.execute("""
                        INSERT INTO leads (
                            name, phone, email, source, id_number, issue_date, expiry_date,
                            birth_date, marital_status, children, policies_json, 
                            callback_date, renewal_date, notes, status, lead_score, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        name.strip(),
                        phone.strip(),
                        email.strip(),
                        source,
                        id_number.strip(),
                        issue_date.strip(),
                        expiry_date.strip(),
                        b_date_str,
                        marital_status,
                        children,
                        policies_json,
                        c_date_str,
                        r_date_str,
                        notes.strip(),
                        'חדש',
                        50  # הציון ההתחלתי שנתת במנוע ה-AI
                    ))

                    conn.commit()
                    conn.close()

                    st.success(f"🎉 הליד '{name}' נוסף בהצלחה למערכת!")
                    time.sleep(1.5)  # השהייה קלה לקריאת ההודעה

                    # הקפצה אוטומטית לטבלת הלידים!
                    st.switch_page("pages/4_📋_טבלת_לידים.py")

                except Exception as e:
                    st.error(f"❌ אירעה שגיאה בשמירת הליד במסד הנתונים: {e}")