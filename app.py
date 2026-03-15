import streamlit as st
import pandas as pd
from datetime import datetime
import threading
from flask import Flask, jsonify, request
import sqlite3
import os
import json
import base64

# --- Page Config ---
st.set_page_config(page_title="LeadFlow Pro X", layout="wide", page_icon="🏠")

# ייבוא פונקציות מהשכבות השונות (כולל מנוע החיפוש החכם)
from engines import (
    setup_page_styling, get_stats, api_update_har_data,
    init_db, get_leads_data, add_interaction, find_lead_by_any
)

# הגדרת עיצוב וחיבור
theme = setup_page_styling()

app = Flask(__name__)


# ==========================================
# API Endpoints (Flask - Port 5050)
# ==========================================

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "service": "LeadFlow API"}), 200


@app.route('/stats', methods=['GET'])
def api_stats():
    return jsonify(get_stats()), 200


@app.route('/api/text_note', methods=['POST'])
def api_text_note():
    """קליטת הערת טקסט מ-n8n ושיוך חכם ללקוח"""
    try:
        data = request.json
        conn = init_db()

        # ניסיון זיהוי חכם לפי שם או טלפון
        target_id = find_lead_by_any(conn, name=data.get('client_name'), phone=data.get('phone'))

        # אם לא מצאנו התאמה, נשתמש ב-ID שנשלח, או 1 כברירת מחדל
        if not target_id:
            target_id = data.get('lead_id') or 1

        if data.get('text_content'):
            add_interaction(conn, target_id, "הערה מטלגרם", data.get('text_content'))
            conn.close()
            return jsonify({"status": "success", "message": f"Note added to lead {target_id}"}), 200

        conn.close()
        return jsonify({"status": "error", "message": "No text content provided"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/interactions/add', methods=['POST'])
def api_add_interaction():
    """קליטת סיכומי שיחה מ-Gemini/n8n ושיוך חכם ללקוח"""
    try:
        data = request.json
        conn = init_db()

        # ניסיון זיהוי חכם לפי שם או טלפון
        target_id = find_lead_by_any(conn, name=data.get('client_name'), phone=data.get('phone'))

        if not target_id:
            target_id = data.get('lead_id') or 1

        if data.get('summary'):
            add_interaction(conn, target_id, data.get('type', 'סיכום קולי AI'), data.get('summary'))
            conn.close()
            return jsonify({"status": "success", "message": f"Summary added to lead {target_id}"}), 200

        conn.close()
        return jsonify({"status": "error", "message": "No summary provided"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/leads/add', methods=['POST'])
def api_add_lead():
    """הזרקת ליד חדש מ-n8n"""
    try:
        data = request.json
        conn = init_db()
        conn.execute("INSERT INTO leads (name, phone, email, source, status) VALUES (?,?,?,?,?)",
                     (data.get('name', 'ללא שם'), data.get('phone', ''), data.get('email', ''),
                      data.get('source', 'Telegram'), 'חדש'))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/process_har', methods=['POST'])
def api_process_har():
    """עיבוד קובץ HAR והרחבת נתוני פוליסה"""
    try:
        data = request.json
        success = api_update_har_data(data.get('lead_id', 1), [{"type": "אוטומטי", "company": "HAR", "prem": 0}])
        return jsonify({"status": "success" if success else "error"}), 200
    except:
        return jsonify({"status": "error"}), 500


# ==========================================
# API Runner (חסין-רענונים)
# ==========================================
@st.cache_resource
def start_flask_api():
    def run_api():
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        try:
            app.run(port=5050, host='0.0.0.0', debug=False, use_reloader=False)
        except Exception as e:
            print(f"Flask API Error: {e}")

    thread = threading.Thread(target=run_api, name="FlaskAPI", daemon=True)
    thread.start()
    return thread


start_flask_api()

# ==========================================
# מנגנון התחברות (Login)
# ==========================================
if 'auth_status' not in st.session_state:
    st.session_state['auth_status'] = False

if not st.session_state['auth_status']:
    st.title("🔒 התחברות ל-LeadFlow CRM")
    with st.container():
        st.markdown("<div style='max-width: 400px; margin: 0 auto;'>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("שם משתמש")
            password = st.text_input("סיסמה", type="password")
            submit = st.form_submit_button("הכנס למערכת", type="primary")

            if submit:
                if (username == "shon" and password == "1234"):
                    st.session_state['auth_status'] = True
                    st.rerun()
                else:
                    st.error("שם משתמש או סיסמה שגויים!")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# UI Layout (Streamlit)
# ==========================================
col_title, col_logout = st.columns([8, 1])
with col_title:
    st.title("🏠 דשבורד מנהלים - LeadFlow Pro")
with col_logout:
    if st.button("🚪 התנתק", use_container_width=True):
        st.session_state['auth_status'] = False
        st.rerun()

with st.expander("🔌 סטטוס אוטומציות (n8n)", expanded=False):
    st.success("✅ שרת ה-API פעיל בפורט 5050. חיפוש חכם (לפי שם וטלפון) מופעל!")

conn = init_db()
df = get_leads_data(conn)
conn.close()

if not df.empty:
    st.markdown("### 📊 נתוני מפתח")
    m1, m2, m3, m4 = st.columns(4)

    total_leads = len(df)
    in_progress = len(df[df['status'] == 'בטיפול'])
    sold_df = df[df['status'] == 'נמכר']
    sold = len(sold_df)
    total_comm = sold_df['estimated_commission'].sum() if not sold_df.empty else 0

    m1.metric("👥 סך הכל לידים", total_leads)
    m2.metric("⏳ בטיפול", in_progress)
    m3.metric("✅ עסקאות שנסגרו", sold)
    m4.metric("💰 הכנסות סגורות", f"₪{total_comm:,.0f}")

    st.divider()
    st.subheader("📋 לידים אחרונים")

    display_df = df[['id', 'name', 'phone', 'source', 'status', 'estimated_commission']].head(10).copy()
    display_df.columns = ['מזהה', 'שם לקוח', 'טלפון', 'מקור', 'סטטוס', 'עמלה']

    st.dataframe(display_df, use_container_width=True, hide_index=True)
else:
    st.info("אין לידים להצגה כרגע.")