import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import math

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="לוח עבודה - Kanban", page_icon="📌")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")


# --- 3. פונקציות גיבוי מקומיות (מניעת ImportErrors) ---
# במקרה שהמנוע חסר, הדף ישתמש בפונקציות האלו ולא יקרוס
def fallback_wa_link(phone, msg=""):
    import urllib.parse
    clean = ''.join(filter(str.isdigit, str(phone)))
    if clean.startswith('0'): clean = '972' + clean[1:]
    return f"https://wa.me/{clean}?text={urllib.parse.quote(msg)}"


def fallback_cal_link(title, date_obj, details=""):
    return "https://calendar.google.com"


# --- 4. ייבוא בטוח מהמנוע ---
try:
    from engines import (
        init_db, get_leads_data, get_interactions, get_files, get_tasks,
        add_interaction, add_task, save_file,
        AIEngine, N8nIntegration, setup_page_styling
    )

    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבי ליבה ב-engines.py. פרטים: {e}")
    st.stop()

# ניסיון ייבוא פונקציות חיצוניות עם Fallback
try:
    from engines import generate_whatsapp_link
except ImportError:
    generate_whatsapp_link = fallback_wa_link

try:
    from engines import generate_google_calendar_link
except ImportError:
    generate_google_calendar_link = fallback_cal_link

# הגנה על ספריית תמלול קול
try:
    import speech_recognition as sr

    HAS_SR = True
except ImportError:
    HAS_SR = False

# --- קבועים ---
ITEMS_PER_PAGE = 10
STATUS_OPTIONS = ["חדש", "בטיפול", "לא עונה", "נמכר", "לא רלוונטי", "פגישה תואמה"]

# --- חיבור למסד נתונים ---
try:
    conn = init_db()
    df = get_leads_data(conn)
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    df = pd.DataFrame()

# --- ממשק הלוח ---
st.title("📌 לוח עבודה - Kanban Board")

# חיפוש בטוח
search_kanban = st.text_input("🔍 חיפוש חופשי בלוח", placeholder="הקלד שם או טלפון לחילוץ מהיר...")
if search_kanban and not df.empty:
    df = df[df.apply(lambda row: search_kanban.lower() in str(row.to_dict()).lower(), axis=1)]

if df.empty:
    st.info("📭 אין לידים להצגה כרגע. תוכל להוסיף ליד חדש כדי לראות אותו כאן.")
else:
    # מנגנון דפדוף בטוח
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

    # הגדרת עמודות הלוח
    statuses_to_display = ["חדש", "בטיפול", "לא עונה", "נמכר"]
    colors = ["#FF6B6B", "#FFA500", "#95A5A6", "#4CAF50"]
    cols = st.columns(len(statuses_to_display))

    for i, status in enumerate(statuses_to_display):
        # כותרת העמודה עם כמות לידים
        status_leads = df[df['status'] == status]
        cols[i].markdown(
            f"<div style='text-align:center; background-color:{colors[i]}; color:white; padding:10px; border-radius:8px; margin-bottom:10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'><b>{status} ({len(status_leads)})</b></div>",
            unsafe_allow_html=True)

        page_leads = status_leads.iloc[start_idx:end_idx]

        with cols[i].container():
            for idx, row in page_leads.iterrows():

                # שליפת המלצת AI מוגנת
                try:
                    next_action = AIEngine.suggest_next_action(row.to_dict())
                except Exception:
                    next_action = "פעולה לא זמינה"

                # כרטיס הליד (UI)
                bg_color = theme.get('card', '#ffffff')
                text_color = theme.get('text', '#000000')
                border_color = theme.get('border', '#e0e0e0')

                st.markdown(f"""
                    <div style='background-color:{bg_color}; border:1px solid {border_color}; padding:15px; border-radius:10px; margin-bottom:15px; border-right:5px solid {colors[i]}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
                        <h5 style='margin:0; color:{text_color}; font-weight:bold;'>{row.get('name', 'ללא שם')}</h5>
                        <p style='margin:5px 0; color:gray; font-size:0.9em;'>📞 {row.get('phone', 'אין מספר')}</p>
                        <p style='margin:5px 0; font-size:0.85em; color:#4CAF50; font-weight:bold;'>💡 {next_action}</p>
                    </div>
                """, unsafe_allow_html=True)

                # אזור ניהול מתקפל
                with st.expander(f"⚙️ פעולות: {row.get('name', 'לקוח')}"):

                    # 1. שינוי סטטוס מהיר
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

                            try:
                                N8nIntegration.notify_status_change({
                                    "lead_id": row['id'], "name": row['name'],
                                    "old_status": current_status, "new_status": new_status
                                })
                            except Exception:
                                pass  # התעלם משגיאות רשת ל-n8n כדי לא לתקוע את הממשק

                            st.toast(f"הסטטוס שונה ל '{new_status}'")
                            time.sleep(0.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"שגיאה בעדכון סטטוס: {e}")

                    # 2. לשוניות ניהול
                    tabs = st.tabs(["💬 תקשורת", "🎙️ היסטוריה", "📎 קבצים", "✅ משימות"])

                    # --- לשונית: תקשורת ---
                    with tabs[0]:
                        safe_phone = row.get('phone', '')
                        wa_link = generate_whatsapp_link(safe_phone, f"שלום {row.get('name', '')}, ")
                        st.link_button("💬 שלח WhatsApp", wa_link, use_container_width=True)

                        safe_email = row.get('email')
                        if pd.notna(safe_email) and safe_email:
                            st.link_button("📧 שלח אימייל", f"mailto:{safe_email}", use_container_width=True)

                        cal_link = generate_google_calendar_link(f"פגישה: {row.get('name', '')}", datetime.now().date(),
                                                                 details=f"טלפון: {safe_phone}")
                        st.link_button("📅 קבע פגישה ביומן", cal_link, use_container_width=True)

                    # --- לשונית: היסטוריה (ותמלול מוגן) ---
                    with tabs[1]:
                        voice_mode = st.radio("בחר פעולה:", ["הקלטה קולית", "טקסט רגיל"], horizontal=True,
                                              key=f"v_mode_{row['id']}")

                        if voice_mode == "טקסט רגיל":
                            with st.form(key=f"note_form_{row['id']}"):
                                new_note = st.text_area("הוסף סיכום שיחה:")
                                sent = st.selectbox("סנטימנט", ["ניטרלי", "חיובי", "שלילי"])
                                if st.form_submit_button("💾 שמור"):
                                    try:
                                        add_interaction(conn, row['id'], "ידני", new_note, sent)
                                        st.success("נשמר!")
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"שגיאה: {e}")
                        else:
                            if not HAS_SR:
                                st.warning(
                                    "⚠️ ספריית התמלול (speechRecognition) חסרה. התקן אותה בעזרת pip install SpeechRecognition")
                            else:
                                audio_input = st.audio_input("הקלט סיכום שיחה", key=f"rec_{row['id']}")
                                if audio_input and st.button("💾 תמלל ושמור", key=f"save_audio_{row['id']}"):
                                    with st.spinner("מפענח אודיו..."):
                                        try:
                                            r = sr.Recognizer()
                                            with sr.AudioFile(audio_input) as source:
                                                audio_data = r.record(source)
                                                transcript = r.recognize_google(audio_data, language="he-IL")
                                        except Exception as e:
                                            transcript = f"הקלטה נשמרה (נכשל תמלול: {str(e)})"

                                    try:
                                        add_interaction(conn, row['id'], "הקלטה", f"תמלול: {transcript}")
                                        st.success("הקלטה נשמרה!")
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"שגיאה בשמירה: {e}")

                        st.divider()
                        st.caption("**היסטוריית אינטראקציות:**")
                        try:
                            interactions = get_interactions(conn, row['id'])
                            if not interactions.empty:
                                for _, inter in interactions.iterrows():
                                    icon = "🎙️" if "הקלטה" in str(inter.get('type', '')) else "📝"
                                    st.caption(
                                        f"{icon} **{str(inter.get('date', ''))[:16]}** | {inter.get('summary', '')}")
                            else:
                                st.caption("אין היסטוריה.")
                        except Exception:
                            st.caption("שגיאה בטעינת היסטוריה.")

                    # --- לשונית: קבצים ---
                    with tabs[2]:
                        try:
                            files = get_files(conn, row['id'])
                            if not files.empty:
                                for _, f in files.iterrows():
                                    st.markdown(f"📄 `{f.get('filename', 'קובץ')}`")
                            else:
                                st.caption("אין קבצים משויכים.")
                        except:
                            pass

                        uploaded_file = st.file_uploader("העלה קובץ חדש", key=f"up_{row['id']}")
                        if uploaded_file and st.button("שמור מסמך", key=f"save_f_{row['id']}"):
                            try:
                                save_file(conn, row['id'], uploaded_file)
                                st.success("נשמר!")
                                time.sleep(0.5)
                                st.rerun()
                            except Exception as e:
                                st.error("שגיאה בשמירה.")

                    # --- לשונית: משימות ---
                    with tabs[3]:
                        try:
                            tasks = get_tasks(conn, row['id'])
                            if not tasks.empty:
                                task_cols = [c for c in ['title', 'due_date'] if c in tasks.columns]
                                st.dataframe(tasks[task_cols], hide_index=True, use_container_width=True)
                            else:
                                st.caption("אין משימות פתוחות.")
                        except:
                            pass

                        with st.form(key=f"t_form_{row['id']}"):
                            t_title = st.text_input("משימה חדשה:")
                            t_due = st.date_input("תאריך יעד", value=date.today())
                            if st.form_submit_button("➕ הוסף משימה"):
                                if t_title:
                                    try:
                                        add_task(conn, row['id'], t_title, "בינוני", t_due.strftime('%Y-%m-%d'),
                                                 t_title)
                                        st.success("נוסף!")
                                        time.sleep(0.5)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"שגיאה: {e}")
                                else:
                                    st.warning("הזן כותרת משימה.")

if conn:
    conn.close()