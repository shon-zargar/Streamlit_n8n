import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="ניהול תביעות", page_icon="🏥")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. ייבוא בטוח מהמנוע ---
try:
    from engines import (
        init_db, get_claims_data, get_leads_data,
        setup_page_styling, add_interaction
    )

    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבים ב-engines.py. פרטים: {e}")


    # פונקציות גיבוי למניעת קריסה
    def get_claims_data(conn=None):
        return pd.DataFrame()


    def get_leads_data(conn=None):
        return pd.DataFrame()


    def add_interaction(c, l, t, s):
        pass


    theme = {}

# --- חיבור למסד נתונים ---
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None

# --- 4. ממשק המשתמש ---
st.title("🏥 מרכז ניהול תביעות")
st.markdown("מעקב, טיפול ועדכון סטטוס לתביעות ביטוח של לקוחות המשרד.")

# משיכת נתונים בטוחה
with st.spinner("שואב נתוני תביעות..."):
    claims_df = pd.DataFrame()
    all_leads_df = pd.DataFrame()
    if conn:
        try:
            # שימוש ב-try/except נוסף כדי לטפל ב-TypeError הישן אם במקרה המנוע לא התעדכן
            try:
                claims_df = get_claims_data(conn)
            except TypeError:
                claims_df = get_claims_data()  # ניסיון שני ללא ארגומנטים

            all_leads_df = get_leads_data(conn)
        except Exception as e:
            st.error(f"שגיאה בשליפת הנתונים: {e}")

# סטטיסטיקות מהירות
if not claims_df.empty:
    col1, col2, col3 = st.columns(3)
    col1.metric("סה״כ תביעות מטופלות", len(claims_df))

    open_claims = len(claims_df[claims_df['status'].str.contains('פתוחה|בטיפול|תביעה', na=False)])
    col2.metric("תביעות פתוחות", open_claims)

    closed_claims = len(claims_df[claims_df['status'].str.contains('נסגרה|שולמה', na=False)])
    col3.metric("תביעות שנסגרו/שולמו", closed_claims)
else:
    st.info("אין תביעות פתוחות כרגע במערכת.")

st.divider()

tabs = st.tabs(["📋 רשימת תביעות", "➕ פתיחת תביעה חדשה", "🔄 עדכון סטטוס תביעה"])

# --- TAB 1: רשימת תביעות ---
with tabs[0]:
    st.subheader("סטטוס תביעות פעילות")
    if not claims_df.empty:
        # סינון עמודות רלוונטיות לתצוגה
        cols_to_show = ['id', 'name', 'phone', 'status', 'callback_date']
        available_cols = [c for c in cols_to_show if c in claims_df.columns]

        display_df = claims_df[available_cols].copy()

        # תרגום כותרות
        heb_cols = {'id': 'מזהה לקוח', 'name': 'שם', 'phone': 'טלפון', 'status': 'סטטוס תביעה',
                    'callback_date': 'תאריך מעקב'}
        display_df.rename(columns=heb_cols, inplace=True)

        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.caption("כאשר תפתח תביעה ללקוח, היא תופיע כאן.")

# --- TAB 2: פתיחת תביעה חדשה ---
with tabs[1]:
    st.subheader("פתיחת הליך תביעה ללקוח קיים")
    if all_leads_df.empty:
        st.warning("אין לקוחות במערכת. הוסף לקוחות קודם בדף 'ליד חדש'.")
    else:
        with st.container(border=True):
            lead_dict = dict(zip(all_leads_df['id'], all_leads_df['name']))
            selected_lead_id = st.selectbox("בחר לקוח פוגע/תובע:", list(lead_dict.keys()),
                                            format_func=lambda x: f"{lead_dict[x]} (ID: {x})")

            claim_type = st.selectbox("סוג תביעה:",
                                      ["בריאות - ניתוח/ייעוץ", "בריאות - תרופות", "רכב - מקיף", "רכב - צד ג'",
                                       "חיים / אובדן כושר עבודה", "דירה", "אחר"])
            claim_desc = st.text_area("תיאור האירוע / סיבת התביעה:")

            if st.button("🚨 פתח תיק תביעה", type="primary"):
                if claim_desc:
                    try:
                        # עדכון הסטטוס למילה שמכילה "תביעה" כדי שישאב אוטומטית לדף הזה
                        new_status = f"תביעה: {claim_type}"
                        conn.execute("UPDATE leads SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                     (new_status, selected_lead_id))
                        conn.commit()

                        # הוספת אינטראקציה שמתעדת את פתיחת התביעה
                        add_interaction(conn, selected_lead_id, "פתיחת תביעה",
                                        f"סוג: {claim_type} | תיאור: {claim_desc}")

                        st.success("תיק התביעה נפתח בהצלחה! הסטטוס עודכן.")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"שגיאה בעדכון הנתונים: {e}")
                else:
                    st.warning("אנא הזן תיאור קצר לתביעה.")

# --- TAB 3: עדכון סטטוס תביעה ---
with tabs[2]:
    st.subheader("עדכון התקדמות מול חברת הביטוח")
    if claims_df.empty:
        st.warning("אין תביעות פעילות לעדכון.")
    else:
        with st.container(border=True):
            claim_dict = dict(zip(claims_df['id'], claims_df['lead_name']))
            claim_target_id = st.selectbox("בחר תיק תביעה לעדכון:", list(claim_dict.keys()),
                                           format_func=lambda x: f"{claim_dict[x]} (ID: {x})")

            new_claim_status = st.selectbox("סטטוס מעודכן:", [
                "תביעה בטיפול - ממתין למסמכים",
                "תביעה הוגשה לחברה - ממתין לאישור",
                "תביעה אושרה - ממתין לתשלום",
                "תביעה שולמה / נסגרה (הצלחה)",
                "תביעה נדחתה"
            ])

            status_note = st.text_input("הערת חתם / עדכון (אופציונלי):")

            if st.button("💾 עדכן סטטוס", type="secondary"):
                try:
                    conn.execute("UPDATE leads SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                 (new_claim_status, claim_target_id))
                    conn.commit()

                    if status_note:
                        add_interaction(conn, claim_target_id, "עדכון תביעה", status_note)

                    st.success("סטטוס התביעה עודכן בהצלחה!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"שגיאה בעדכון התביעה: {e}")

if conn:
    conn.close()