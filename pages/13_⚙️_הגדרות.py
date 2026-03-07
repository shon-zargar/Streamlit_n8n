import streamlit as st
from datetime import datetime, timedelta
import shutil
import io
import pandas as pd
import os

from engines import init_db, send_telegram_alert, get_leads_data, get_claims_data, setup_page_styling

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="הגדרות")

# --- Global Styling (Fixing the theme persistence issue) ---
theme = setup_page_styling()

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("⚙️ הגדרות מערכת")
settings_tabs = st.tabs(["🔔 התראות", "💾 גיבויים", "📊 נתונים"])

with settings_tabs[0]:
    st.header("🔔 הגדרות התראות")
    with st.form("telegram_settings"):
        st.subheader("Telegram Bot")
        tg_token_input = st.text_input("Bot Token", value=st.session_state.get('tg_token', ''), type="password")
        tg_chat_input = st.text_input("Chat ID", value=st.session_state.get('tg_chat_id', ''))
        if st.form_submit_button("💾 שמור"):
            st.session_state['tg_token'] = tg_token_input
            st.session_state['tg_chat_id'] = tg_chat_input
            st.success("✅ נשמר!")

with settings_tabs[1]:
    st.header("💾 גיבויים")
    if st.button("💾 צור גיבוי מלא", type="primary"):
        backup_filename = f"leadflow_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        try:
            shutil.copy2('leads_pro_ultimate.db', backup_filename)
            with open(backup_filename, 'rb') as f:
                st.download_button("📥 הורד גיבוי", f, backup_filename, "application/x-sqlite3")
            st.success(f"✅ גיבוי נוצר: {backup_filename}")
        except Exception as e:
            st.error(f"שגיאה ביצירת גיבוי: {e}")

    st.divider()
    st.subheader("שחזור מגיבוי")
    uploaded_backup = st.file_uploader("העלה קובץ גיבוי (.db)", type=['db'])
    if uploaded_backup:
        if st.button("⚠️ שחזר נתונים (דורס את הקיים!)", type="secondary"):
            try:
                with open('leads_pro_ultimate.db', 'wb') as f:
                    f.write(uploaded_backup.getvalue())
                st.success("✅ הנתונים שוחזרו בהצלחה! אנא רענן את הדף.")
            except Exception as e:
                st.error(f"שגיאה בשחזור: {e}")

with settings_tabs[2]:
    st.header("📊 ניהול נתונים")
    st.warning("⚠️ פעולות אלו הן בלתי הפיכות!")
    with st.form("delete_old"):
        days_old = st.number_input("מחק לידים ישנים מעל X ימים", 30, 365, 90)
        if st.form_submit_button("🗑️ מחק לידים ישנים"):
            cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime('%Y-%m-%d')
            deleted = conn.execute("DELETE FROM leads WHERE created_at < ?", (cutoff_date,))
            conn.commit()
            st.success(f"נמחקו {deleted.rowcount} לידים")
