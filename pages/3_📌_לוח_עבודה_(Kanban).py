import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import math
import speech_recognition as sr

# --- 1. הגדרת העמוד (חובה להיות הפקודה הראשונה) ---
st.set_page_config(layout="wide", page_title="לוח עבודה - Kanban", page_icon="📌")

# --- 2. אבטחה וניהול זיכרון ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. טעינה מאובטחת של המנועים ---
try:
    from engines import (
        init_db, get_leads_data, get_interactions, get_files, get_tasks,
        add_interaction, add_task, save_file,
        AIEngine, N8nIntegration, generate_whatsapp_link,
        generate_google_calendar_link, setup_page_styling
    )
except ImportError as e:
    st.error(f"שגיאה בטעינת קובצי המנוע (engines.py). ודא שהקובץ קיים בתיקייה הראשית. פרטים: {e}")
    st.stop()

# --- החלת עיצוב פרויקט ---
theme = setup_page_styling()

# --- קבועים ---
ITEMS_PER_PAGE = 10
STATUS_OPTIONS = ["חדש", "בטיפול", "לא עונה", "נמכר", "לא רלוונטי", "פגישה תואמה"]

# אתחול חיבור למסד נתונים
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור למסד הנתונים: {e}")
    st.stop()

# --- תוכן הדף ---
st.title("📌 לוח עבודה - Kanban Board")

# שליפת נתונים בטוחה
try:
    df = get_leads_data(conn)
except Exception as e:
    st.error(f"שגיאה בשליפת נתונים ממסד הנתונים: {e}")
    df = pd.DataFrame()

# חיפוש
search_kanban = st.text_input("🔍 חיפוש", placeholder="הקלד שם, טלפון או הערות...")
if search_kanban and not df.empty:
    # חיפוש בטוח המונע קריסה על ערכים ריקים
    df = df[df.apply(lambda row: search_kanban.lower() in str(row.to_dict()).lower(), axis=1)]

if df.empty:
    st.info("📭 אין לידים להצגה התואמים לחיפוש או למסנן.")
else:
    # מנגנון דפדוף (Pagination)
    if 'kanban_page' not in st.session_state:
        st.session_state.kanban_page = 0

    total_pages = math.ceil(len(df) / ITEMS_PER_PAGE)
    if st.session_state.kanban_page >= total_pages and total_pages > 0:
        st.session_state.kanban_page = 0

    pcol1, pcol2, pcol3 = st.columns([1, 8, 1])
    if pcol1.button("⬅️ הקודם", key="kprev"):
        st.session_state.kanban_page = max(0, st.session_state.kanban_page - 1)
        st.rerun()

    pcol2.markdown(
        f"<div style='text-align:center; font-weight:bold;'>עמוד {st.session_state.kanban_page + 1} מתוך {max(1, total_pages)}</div>",
        unsafe_allow_html=True)

    if pcol3.button("הבא ➡️", key="knext"):
        st.session_state.kanban_page = min(total_pages - 1, st.session_state.kanban_page + 1)
        st.rerun()

    start_idx = st.session_state.kanban_page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE

    # הגדרת עמודות הקנבן
    statuses_to_display = ["חדש", "בטיפול", "לא עונה", "נמכר"]
    colors = ["#FF6B6B", "#FFA500", "#95A5A6", "#4CAF50"]
    cols = st.columns(len(statuses_to_display))

    for i, status in enumerate(statuses_to_display):
        # כותרת העמודה
        cols[i].markdown(
            f"<div style='text-align:center; background-color:{colors[i]}; color:white; padding:10px; border-radius:8px; margin-bottom:10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'><b>{status}</b></div>",
            unsafe_allow_html=True)

        status_leads = df[df['status'] == status].iloc[start_idx:end_idx]

        with cols[i].container():
            for idx, row in status_leads.iterrows():

                # שליפת המלצת AI בטוחה
                try:
                    next_action = AIEngine.suggest_next_action(row)
                except Exception:
                    next_action = "הצעת AI לא זמינה כרגע"

                # כרטיס הליד (עיצוב מותאם)
                card_bg = theme.get('card', '#ffffff') if isinstance(theme, dict) else '#ffffff'
                card_text = theme.get('text', '#333333') if isinstance(theme, dict) else '#333333'
                card_border = theme.get('border', '#e0e0e0') if isinstance(theme, dict) else '#e0e0e0'

                st.markdown(f"""
                    <div style='background-color:{card_bg}; border:1px solid {card_border}; padding:15px; border-radius:10px; margin-bottom:15px; border-right:4px solid {colors[i]}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                        <h5 style='margin:0; color:{card_text}; font-weight:bold;'>{row.get('name', 'ללא שם')}</h5>
                        <p style='margin:5px 0; color:gray; font-size:0.9em;'>📞 {row.get('phone', 'אין מספר')}</p>
                        <p style='margin:5px 0; font-size:0.85em; color:#4CAF50; font-weight:bold;'>💡 {next_action}</p>
                    </div>
                """, unsafe_allow_html=True)

                # אזור ניהול
                with st.expander(f"⚙️ ניהול: {row.get('name', '')}"):

                    # שינוי סטטוס מהיר
                    current_status = row.get('status', 'חדש')
                    current_status_index = STATUS_OPTIONS.index(
                        current_status) if current_status in STATUS_OPTIONS else 0

                    new_status = st.selectbox("שנה סטטוס:", STATUS_OPTIONS, index=current_status_index,
                                              key=f"status_{row['id']}")

                    if new_status != current_status:
                        try:
                            conn.execute("UPDATE leads SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                         (new_status, row['id']))
                            conn.commit()

                            # שליחת התראה ל-n8n באופן בטוח
                            try:
                                N8nIntegration.notify_status_change({
                                    "lead_id": row['id'], "name": row['name'],
                                    "old_status": current_status, "new_status": new_status
                                })
                            except Exception:
                                st.toast("הסטטוס עודכן ב-DB אך ההתראה ל-n8n נכשלה.")

                            st.toast(f"העברת את {row.get('name', '')} לסטטוס '{new_status}'")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"שגיאה בעדכון הסטטוס: {e}")

                    # לשוניות ניהול
                    tabs = st.tabs(["💬 תקשורת", "🎙️ היסטוריה והקלטות", "📎 קבצים", "✅ משימות"])

                    # --- לשונית 1: תקשורת ---
                    with tabs[0]:
                        st.link_button("💬 שלח הודעת WhatsApp",
                                       generate_whatsapp_link(row.get('phone', ''), f"שלום {row.get('name', '')}, "),
                                       use_container_width=True)

                        email = row.get('email')
                        if pd.notna(email) and email != "":
                            st.link_button("📧 שלח מייל", f"mailto:{email}", use_container_width=True)

                        try:
                            cal_link = generate_google_calendar_link(f"פגישה: {row.get('name', '')}",
                                                                     datetime.now().date(),
                                                                     details=f"טלפון: {row.get('phone', '')}")
                            st.link_button("📅 קבע פגישה ביומן", cal_link, use_container_width=True)
                        except Exception:
                            st.warning("לא ניתן לייצר קישור ליומן.")

                    # --- לשונית 2: היסטוריה והקלטות ---
                    with tabs[1]:
                        st.markdown("**תיעוד שיחה**")
                        voice_mode = st.radio("בחר פעולה:", ["הקלטה מהמיקרופון", "העלאת קובץ קיים", "טקסט רגיל"],
                                              horizontal=True, key=f"v_mode_{row['id']}")

                        if voice_mode == "טקסט רגיל":
                            with st.form(key=f"note_form_{row['id']}"):
                                new_note = st.text_area("הוסף הערה:")
                                sent = st.selectbox("סנטימנט השיחה", ["ניטרלי", "חיובי", "שלילי"])
                                if st.form_submit_button("שמור הערה"):
                                    try:
                                        add_interaction(conn, row['id'], "ידני", new_note, sent)
                                        st.success("הערה נשמרה בהצלחה!")
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"שגיאה בשמירת הערה: {e}")
                        else:
                            audio_file_to_process = None
                            if voice_mode == "הקלטה מהמיקרופון":
                                audio_input = st.audio_input("הקלט סיכום שיחה", key=f"rec_{row['id']}")
                                if audio_input: audio_file_to_process = audio_input
                            else:
                                uploaded_audio = st.file_uploader("העלה קובץ אודיו (WAV/MP3)",
                                                                  type=['wav', 'mp3', 'm4a'], key=f"up_aud_{row['id']}")
                                if uploaded_audio: audio_file_to_process = uploaded_audio

                            if audio_file_to_process is not None:
                                if st.button("💾 תמלל ושמור בתיק", key=f"save_audio_{row['id']}"):
                                    transcript_text = "הקלטה נשמרה (ללא תמלול)"
                                    with st.spinner("מנתח שמע ומתמלל..."):
                                        try:
                                            r = sr.Recognizer()
                                            with sr.AudioFile(audio_file_to_process) as source:
                                                audio_data = r.record(source)
                                                transcript_text = r.recognize_google(audio_data, language="he-IL")
                                        except Exception as e:
                                            transcript_text = f"הקלטה נשמרה (שגיאת תמלול: {str(e)})"

                                    try:
                                        add_interaction(conn, row['id'], "הקלטה קולית", f"תמלול: {transcript_text}")
                                        st.success("הקלטה נשמרה בהצלחה בתיק הלקוח!")
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"שגיאה בשמירה ל-DB: {e}")

                        st.divider()
                        st.markdown("**היסטוריית אינטראקציות:**")
                        try:
                            interactions = get_interactions(conn, row['id'])
                            if not interactions.empty:
                                for _, inter in interactions.iterrows():
                                    icon = "🎙️" if "הקלטה" in str(inter.get('type', '')) else "📝"
                                    st.caption(
                                        f"{icon} **{str(inter.get('date', ''))[:16]}** | {inter.get('summary', '')}")
                            else:
                                st.caption("אין פעולות קודמות.")
                        except Exception:
                            st.caption("לא ניתן לטעון היסטוריית פעולות.")

                    # --- לשונית 3: קבצים ---
                    with tabs[2]:
                        try:
                            files = get_files(conn, row['id'])
                            if not files.empty:
                                for _, f in files.iterrows():
                                    st.markdown(f"📄 `{f.get('filename', 'קובץ ללא שם')}`")
                            else:
                                st.caption("אין קבצים מצורפים ללקוח זה.")
                        except Exception:
                            pass

                        uploaded_file = st.file_uploader("העלה מסמך חדש", key=f"upload_{row['id']}")
                        if uploaded_file and st.button("שמור מסמך", key=f"savefile_{row['id']}"):
                            try:
                                save_file(conn, row['id'], uploaded_file)
                                st.success("המסמך נשמר!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"שגיאה בשמירת מסמך: {e}")

                    # --- לשונית 4: משימות ---
                    with tabs[3]:
                        try:
                            tasks = get_tasks(conn, row['id'])
                            if not tasks.empty:
                                task_cols = [c for c in ['title', 'due_date'] if c in tasks.columns]
                                st.dataframe(tasks[task_cols], hide_index=True, use_container_width=True)
                            else:
                                st.caption("אין משימות פתוחות.")
                        except Exception:
                            pass

                        with st.form(key=f"task_form_{row['id']}"):
                            task_title = st.text_input("תיאור המשימה החדשה:")
                            task_due = st.date_input("תאריך יעד", value=date.today())
                            if st.form_submit_button("➕ הוסף משימה"):
                                if task_title:
                                    try:
                                        add_task(conn, row['id'], task_title, "", task_due.strftime('%Y-%m-%d'))
                                        st.success("המשימה נוספה!")
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"שגיאה ביצירת משימה: {e}")
                                else:
                                    st.warning("נא להזין תיאור משימה.")