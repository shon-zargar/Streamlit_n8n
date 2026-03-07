import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import math
import speech_recognition as sr

from engines import (
    init_db, get_leads_data, get_interactions, get_files, get_tasks,
    add_interaction, add_task, save_file,
    AIEngine, N8nIntegration, generate_whatsapp_link,
    generate_google_calendar_link, setup_page_styling
)

# --- Page Configuration & Styling ---
st.set_page_config(layout="wide", page_title="לוח עבודה")
theme = setup_page_styling()

# --- Constants & DB ---
ITEMS_PER_PAGE = 10  # מונע שגיאת NameError
STATUS_OPTIONS = ["חדש", "בטיפול", "לא עונה", "נמכר", "לא רלוונטי", "פגישה תואמה"]
conn = init_db()

# --- Main Page ---
st.title("📌 לוח עבודה - Kanban Board")

df = get_leads_data(conn)

# Search
search_kanban = st.text_input("🔍 חיפוש", placeholder="הקלד שם, טלפון או הערות...")
if search_kanban:
    df = df[df.apply(lambda row: search_kanban.lower() in str(row).lower(), axis=1)]

if df.empty:
    st.info("אין לידים להצגה")
else:
    # Pagination
    if 'kanban_page' not in st.session_state:
        st.session_state.kanban_page = 0

    total_pages = math.ceil(len(df) / ITEMS_PER_PAGE)
    if st.session_state.kanban_page >= total_pages and total_pages > 0:
        st.session_state.kanban_page = 0

    pcol1, pcol2, pcol3 = st.columns([1, 8, 1])
    if pcol1.button("⬅️", key="kprev"):
        st.session_state.kanban_page = max(0, st.session_state.kanban_page - 1)
        st.rerun()
    pcol2.markdown(
        f"<div style='text-align:center;'>עמוד {st.session_state.kanban_page + 1}/{max(1, total_pages)}</div>",
        unsafe_allow_html=True)
    if pcol3.button("➡️", key="knext"):
        st.session_state.kanban_page = min(total_pages - 1, st.session_state.kanban_page + 1)
        st.rerun()

    start_idx = st.session_state.kanban_page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE

    # Kanban Columns
    statuses_to_display = ["חדש", "בטיפול", "לא עונה", "נמכר"]
    colors = ["#FF6B6B", "#FFA500", "#95A5A6", "#4CAF50"]
    cols = st.columns(len(statuses_to_display))

    for i, status in enumerate(statuses_to_display):
        cols[i].markdown(
            f"<div style='text-align:center; background-color:{colors[i]}; color:white; padding:10px; border-radius:8px; margin-bottom:10px;'><b>{status}</b></div>",
            unsafe_allow_html=True)

        status_leads = df[df['status'] == status].iloc[start_idx:end_idx]

        with cols[i].container():
            for idx, row in status_leads.iterrows():

                next_action = AIEngine.suggest_next_action(row)
                st.markdown(f"""
                    <div style='background-color:{theme['card']}; border:1px solid {theme['border']}; padding:15px; border-radius:10px; margin-bottom:15px; border-right:4px solid {colors[i]};'>
                        <h5 style='margin:0; color:{theme['text']};'>{row['name']}</h5>
                        <p style='margin:5px 0; color:gray;'>📞 {row['phone']}</p>
                        <p style='margin:5px 0; font-size:0.85em; color:#4CAF50;'>{next_action}</p>
                    </div>
                """, unsafe_allow_html=True)

                with st.expander("⚙️ ניהול ופעולות"):
                    # Quick Status Change
                    current_status_index = STATUS_OPTIONS.index(row['status']) if row['status'] in STATUS_OPTIONS else 0
                    new_status = st.selectbox("שנה סטטוס", STATUS_OPTIONS, index=current_status_index,
                                              key=f"status_{row['id']}")

                    if new_status != row['status']:
                        conn.execute("UPDATE leads SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                                     (new_status, row['id']))
                        conn.commit()
                        N8nIntegration.notify_status_change(
                            {"lead_id": row['id'], "name": row['name'], "old_status": row['status'],
                             "new_status": new_status})
                        st.toast(f"העברת את {row['name']} לסטטוס '{new_status}'")
                        time.sleep(1)
                        st.rerun()

                    # All other management functions in tabs
                    tabs = st.tabs(["💬 תקשורת", "🎙️ היסטוריה והקלטות", "📎 קבצים", "✅ משימות"])

                    with tabs[0]:  # Communication
                        st.link_button("💬 WhatsApp", generate_whatsapp_link(row['phone'], f"שלום {row['name']}, "),
                                       use_container_width=True)
                        if row['email']:
                            st.link_button("📧 שלח מייל", f"mailto:{row['email']}", use_container_width=True)
                        cal_link = generate_google_calendar_link(f"פגישה: {row['name']}", datetime.now().date(),
                                                                 details=f"טלפון: {row['phone']}")
                        st.link_button("📅 קבע פגישה ביומן", cal_link, use_container_width=True)

                    with tabs[1]:  # History & Voice Notes (RESTORED!)
                        st.subheader("תיעוד שיחה")
                        voice_mode = st.radio("בחר פעולה:", ["הקלטה מהמיקרופון", "העלאת קובץ קיים", "טקסט רגיל"],
                                              horizontal=True, key=f"v_mode_{row['id']}")

                        if voice_mode == "טקסט רגיל":
                            with st.form(key=f"note_form_{row['id']}"):
                                new_note = st.text_area("הוסף הערה:")
                                sent = st.selectbox("סנטימנט", ["ניטרלי", "חיובי", "שלילי"])
                                if st.form_submit_button("שמור הערה"):
                                    add_interaction(conn, row['id'], "ידני", new_note, sent)
                                    st.rerun()
                        else:
                            audio_file_to_process = None
                            if voice_mode == "הקלטה מהמיקרופון":
                                audio_input = st.audio_input("לחץ להקלטת סיכום שיחה", key=f"rec_{row['id']}")
                                if audio_input: audio_file_to_process = audio_input
                            else:
                                uploaded_audio = st.file_uploader("העלה הקלטה (WAV/MP3)", type=['wav', 'mp3', 'm4a'],
                                                                  key=f"up_aud_{row['id']}")
                                if uploaded_audio: audio_file_to_process = uploaded_audio

                            if audio_file_to_process is not None:
                                if st.button("💾 תמלל ושמור בתיק", key=f"save_audio_{row['id']}"):
                                    transcript_text = "הקלטה נשמרה (ללא תמלול)"
                                    with st.spinner("מנסה לתמלל..."):
                                        try:
                                            r = sr.Recognizer()
                                            with sr.AudioFile(audio_file_to_process) as source:
                                                audio_data = r.record(source)
                                                transcript_text = r.recognize_google(audio_data, language="he-IL")
                                        except Exception as e:
                                            transcript_text = f"שגיאת תמלול: {str(e)}"

                                    add_interaction(conn, row['id'], "הקלטה קולית", f"תמלול: {transcript_text}")
                                    st.success("נשמר!")
                                    time.sleep(1)
                                    st.rerun()

                        st.divider()
                        st.write("פעולות קודמות:")
                        interactions = get_interactions(conn, row['id'])
                        for _, inter in interactions.iterrows():
                            icon = "🎙️" if "הקלטה" in inter['type'] else "📝"
                            st.caption(f"{icon} **{inter['date'][:16]}** | {inter['summary']}")

                    with tabs[2]:  # Files
                        files = get_files(conn, row['id'])
                        if not files.empty:
                            for _, f in files.iterrows():
                                st.write(f"📄 {f['filename']}")
                        uploaded_file = st.file_uploader("העלה קובץ", key=f"upload_{row['id']}")
                        if uploaded_file and st.button("שמור קובץ", key=f"savefile_{row['id']}"):
                            save_file(conn, row['id'], uploaded_file)
                            st.rerun()

                    with tabs[3]:  # Tasks
                        tasks = get_tasks(conn, row['id'])
                        if not tasks.empty:
                            st.dataframe(tasks[['title', 'due_date']], hide_index=True, use_container_width=True)
                        with st.form(key=f"task_form_{row['id']}"):
                            task_title = st.text_input("הוסף משימה:")
                            task_due = st.date_input("תאריך יעד", value=date.today())
                            if st.form_submit_button("שמור משימה"):
                                add_task(conn, row['id'], task_title, "", task_due.strftime('%Y-%m-%d'))
                                st.rerun()