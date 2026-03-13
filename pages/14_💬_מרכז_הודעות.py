import streamlit as st
import pandas as pd
from datetime import datetime
import time

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="מרכז הודעות", page_icon="💬")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. ייבוא בטוח מהמנוע (עם Fallbacks) ---
try:
    from engines import (
        init_db, get_leads_data, setup_page_styling,
        SMS2010Handler, add_interaction, generate_whatsapp_link
    )

    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבים ב-engines.py. פרטים: {e}")


    # יצירת מחלקת גיבוי מקומית כדי למנוע קריסה של הדף
    class SMS2010Handler:
        @staticmethod
        def get_balance(): return "שגיאת חיבור"

        @staticmethod
        def send_sms(phone, msg): return {"status": "failed"}


    def generate_whatsapp_link(phone, msg):
        return f"https://wa.me/{phone}"


    theme = {"card": "#fff", "text": "#000", "border": "#ddd"}

# --- חיבור למסד נתונים ---
try:
    conn = init_db()
    df_leads = get_leads_data(conn)
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None
    df_leads = pd.DataFrame()

# --- 4. ממשק המשתמש ---
st.title("💬 מרכז הודעות וקמפיינים")

# שליפה בטוחה של יתרת ה-SMS כדי למנוע את שגיאת ה-AttributeError
try:
    balance = SMS2010Handler.get_balance()
except AttributeError:
    balance = "לא זמין (שגיאת מנוע)"

st.caption(f"מחובר למערכת שליחת הודעות | יתרה נוכחית: **{balance}** הודעות SMS")

tabs = st.tabs(["📱 הודעה אישית (SMS / WhatsApp)", "📢 קמפיין מרוכז (Bulk)", "📜 היסטוריית קמפיינים"])

# --- TAB 1: הודעה אישית ---
with tabs[0]:
    st.header("שליחת הודעה ללקוח ספציפי")

    if df_leads.empty or 'id' not in df_leads.columns or 'name' not in df_leads.columns:
        st.warning("אין לקוחות במערכת. אנא הוסף לידים כדי לשלוח הודעות.")
    else:
        with st.container(border=True):
            col1, col2 = st.columns([1, 2])

            with col1:
                # יצירת מילון לשליפה נוחה
                lead_dict = dict(zip(df_leads['id'], df_leads['name']))
                selected_lead_id = st.selectbox("בחר נמען:", list(lead_dict.keys()),
                                                format_func=lambda x: f"{lead_dict[x]}", key="single_msg_target")

                # שליפת טלפון הלקוח
                lead_phone = df_leads[df_leads['id'] == selected_lead_id]['phone'].values[
                    0] if 'phone' in df_leads.columns else ""
                st.info(f"📞 מספר טלפון: {lead_phone or 'לא מוזן'}")

                msg_platform = st.radio("פלטפורמה:", ["SMS", "WhatsApp"], horizontal=True)

            with col2:
                message_text = st.text_area("תוכן ההודעה:", height=150, placeholder="הקלד את הודעתך כאן...")

                if st.button("🚀 שלח הודעה", type="primary", use_container_width=True):
                    if not lead_phone:
                        st.error("ללקוח זה לא מוזן מספר טלפון תקין.")
                    elif not message_text.strip():
                        st.warning("לא ניתן לשלוח הודעה ריקה.")
                    else:
                        with st.spinner("שולח..."):
                            if msg_platform == "SMS":
                                try:
                                    res = SMS2010Handler.send_sms(lead_phone, message_text)
                                    if res and res.get("status") != "failed":
                                        st.success(f"ה-SMS נשלח בהצלחה ל-{lead_dict[selected_lead_id]}!")
                                        add_interaction(conn, selected_lead_id, "SMS נשלח", f"תוכן: {message_text}")
                                    else:
                                        st.error("שגיאה בשליחת ה-SMS מול ספק השירות.")
                                except Exception as e:
                                    st.error(f"תקלה בשליחת SMS: {e}")
                            else:
                                # WhatsApp logic
                                wa_link = generate_whatsapp_link(lead_phone, message_text)
                                st.success("הקישור לוואטסאפ מוכן!")
                                st.link_button("פתח וואטסאפ לשליחה", wa_link)
                                add_interaction(conn, selected_lead_id, "WhatsApp נשלח", f"תוכן: {message_text}")

# --- TAB 2: קמפיין מרוכז ---
with tabs[1]:
    st.header("הפצת קמפיין מרוכז (SMS)")

    if df_leads.empty:
        st.warning("אין לידים במערכת לבניית קמפיין.")
    else:
        st.write("בחר את קהל היעד שלך לשליחת הודעת תפוצה:")

        # מסננים לקמפיין
        ccol1, ccol2 = st.columns(2)
        with ccol1:
            available_statuses = df_leads['status'].unique().tolist() if 'status' in df_leads.columns else []
            target_statuses = st.multiselect("סנן לפי סטטוס ליד:", available_statuses, default=available_statuses)

        with ccol2:
            campaign_text = st.text_area("תוכן הקמפיין (SMS בלבד):", height=100)

        # סינון הלקוחות בפועל
        target_audience = df_leads
        if target_statuses and 'status' in df_leads.columns:
            target_audience = df_leads[df_leads['status'].isin(target_statuses)]

        # סינון לידים בלי טלפון
        if 'phone' in target_audience.columns:
            target_audience = target_audience.dropna(subset=['phone'])
            target_audience = target_audience[target_audience['phone'].str.strip() != '']

        st.info(f"👥 קהל יעד משוער לאחר סינון: **{len(target_audience)}** לקוחות בעלי מספר טלפון.")

        if st.button("🔥 הפעל קמפיין", type="primary"):
            if len(target_audience) == 0:
                st.error("אין נמענים תקינים בקבוצה שבחרת.")
            elif not campaign_text.strip():
                st.warning("נא להזין את תוכן הקמפיין.")
            else:
                progress_bar = st.progress(0)
                success_count = 0

                for i, (idx, row) in enumerate(target_audience.iterrows()):
                    try:
                        # שליחה (בפועל או סימולציה)
                        SMS2010Handler.send_sms(row['phone'], campaign_text)
                        success_count += 1
                        # תיעוד בתיק הלקוח
                        add_interaction(conn, row['id'], "קמפיין SMS", f"קמפיין: {campaign_text}")
                    except Exception:
                        pass  # ממשיכים הלאה כדי לא לתקוע את כל הקמפיין

                    # עדכון הבר
                    progress_bar.progress((i + 1) / len(target_audience))
                    time.sleep(0.1)  # מניעת חסימת Rate Limit

                st.success(f"הקמפיין הסתיים! נשלחו {success_count} מתוך {len(target_audience)} הודעות.")
                st.balloons()

# --- TAB 3: היסטוריה ---
with tabs[2]:
    st.header("היסטוריית הודעות אחרונות")
    st.info("יוצג כאן פירוט ההודעות שנשלחו לאחרונה מתוך מאגר האינטראקציות.")

    if conn:
        try:
            # משיכת אינטראקציות מסוג SMS או WhatsApp
            history_df = pd.read_sql(
                "SELECT leads.name, interactions.type, interactions.summary, interactions.date FROM interactions JOIN leads ON interactions.lead_id = leads.id WHERE type LIKE '%SMS%' OR type LIKE '%WhatsApp%' ORDER BY date DESC LIMIT 50",
                conn)

            if not history_df.empty:
                # שינוי שמות עמודות לעברית
                history_df.columns = ["שם לקוח", "סוג", "תוכן", "תאריך ושעה"]
                st.dataframe(history_df, use_container_width=True, hide_index=True)
            else:
                st.caption("לא נמצאו הודעות שנשלחו לאחרונה.")
        except Exception:
            st.caption("שגיאה בטעינת היסטוריה מול בסיס הנתונים.")

if conn:
    conn.close()