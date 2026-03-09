import streamlit as st
import pandas as pd
from datetime import datetime, date
import time

# ייבוא הפונקציות מהמנוע שלך
from engines import init_db, setup_page_styling, N8nIntegration

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="ניהול משימות ויומן")
try:
    setup_page_styling()
except:
    pass

st.title("📅 יומן ומשימות (Follow-ups)")

conn = init_db()

# --- 1. הוספת משימה (סעיף 2: סנכרון ליומן גוגל) ---
st.subheader("➕ צור משימה חדשה")
with st.expander("לחץ כאן כדי להוסיף משימה לליד קיים", expanded=False):
    leads_df = pd.read_sql("SELECT id, name, phone FROM leads ORDER BY name ASC", conn)

    if leads_df.empty:
        st.warning("אין לידים במערכת.")
    else:
        with st.form("add_task_form"):
            col1, col2, col3 = st.columns([2, 3, 1])
            lead_options = leads_df.apply(lambda row: f"{row['name']} - {row['phone']} (ID:{row['id']})",
                                          axis=1).tolist()
            selected_lead_str = col1.selectbox("בחר ליד:", lead_options)
            task_desc = col2.text_input("תיאור המשימה")
            due_date = col3.date_input("תאריך לביצוע:", date.today())

            submitted = st.form_submit_button("💾 שמור וסנכרן ליומן", type="primary")

            if submitted and task_desc:
                lead_id = int(selected_lead_str.split("(ID:")[1].replace(")", ""))
                lead_name = selected_lead_str.split(" - ")[0]

                # שמירה ב-DB המקומי
                conn.execute('INSERT INTO tasks (lead_id, task_description, due_date) VALUES (?, ?, ?)',
                             (lead_id, task_desc, due_date.strftime('%Y-%m-%d')))
                conn.commit()

                # --- סעיף 2: שליחה ל-n8n ליצירת אירוע ביומן גוגל ---
                task_payload = {
                    "event_type": "new_task_calendar",
                    "lead_name": lead_name,
                    "task_description": task_desc,
                    "due_date": due_date.strftime('%Y-%m-%d'),
                    "location": "חולון"  # ברירת מחדל שלך
                }
                N8nIntegration.send_webhook("TASK_WEBHOOK_URL", task_payload)

                st.success("✅ המשימה נשמרה וסונכרנה ליומן!")
                time.sleep(1)
                st.rerun()

st.divider()

# --- 2. תצוגת משימות (סעיף 3: הודעת סטטוס ללקוח בסיום) ---
st.subheader("📋 משימות פתוחות לביצוע")
query = '''
    SELECT t.id as task_id, l.name as lead_name, l.phone as lead_phone, l.email as lead_email, 
           t.task_description, t.due_date 
    FROM tasks t
    JOIN leads l ON t.lead_id = l.id
    WHERE t.is_completed = 0
    ORDER BY t.due_date ASC
'''
tasks_df = pd.read_sql(query, conn)

if not tasks_df.empty:
    for index, row in tasks_df.iterrows():
        col_t1, col_t2, col_t3, col_t4 = st.columns([4, 2, 2, 1])

        col_t1.markdown(f"**{row['task_description']}**")
        col_t2.markdown(f"👤 {row['lead_name']}")
        col_t3.markdown(f"📅 {row['due_date']}")

        # כפתור סיום משימה
        if col_t4.button("✅ בוצע", key=f"done_{row['task_id']}"):
            # עדכון ב-DB
            conn.execute("UPDATE tasks SET is_completed = 1 WHERE id = ?", (row['task_id'],))
            conn.commit()

            # --- סעיף 3: שליחה ל-n8n לשליחת הודעת "תודה/סיום" ללקוח ---
            completion_payload = {
                "event_type": "task_completed_notify",
                "lead_name": row['lead_name'],
                "lead_phone": row['lead_phone'],
                "lead_email": row['lead_email'],
                "task_done": row['task_description']
            }
            N8nIntegration.send_webhook("NOTIFY_WEBHOOK_URL", completion_payload)

            st.toast(f"הודעת עדכון נשלחה ל{row['lead_name']}!", icon="📩")
            time.sleep(1)
            st.rerun()

conn.close()