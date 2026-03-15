import streamlit as st
import pandas as pd
from datetime import datetime
import threading
from flask import Flask, jsonify, request
import sqlite3
import os
import json
import re

# הגדרות דף Streamlit
st.set_page_config(page_title="LeadFlow Pro X", layout="wide", page_icon="🏠")

# ייבוא פונקציות העזר והמסד מהקובץ המקורי שלך - engines.py
try:
    from engines import (
        setup_page_styling, get_stats, api_update_har_data,
        init_db, get_leads_data, add_interaction, find_lead_by_any
    )
except ImportError:
    st.error("שגיאה: קובץ engines.py חסר או פגום. וודא שהוא נמצא באותה תיקייה של app.py.")
    st.stop()

# החלת עיצוב (מצב לילה/יום)
theme = setup_page_styling()


# ==========================================
# פונקציות עזר פנימיות ל-API
# ==========================================

def clean_ai_json(text):
    """מחלץ JSON תקין מתשובת AI, כולל ניקוי תגיות Markdown"""
    try:
        if not text: return {}
        # הסרת סימני קוד של Markdown אם קיימים
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}
    except:
        return {}


# ==========================================
# API Endpoints (Flask - Port 5050)
# ==========================================
app = Flask(__name__)


@app.route('/', methods=['GET'])
def health():
    return jsonify({"status": "active", "version": "7.1_FIXED_ENGINES"}), 200


@app.route('/stats', methods=['GET'])
def api_get_stats_route():
    """מספק נתונים לדוח הבוקר של טלגרם באמצעות get_stats מ-engines"""
    try:
        stats = get_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/text_note', methods=['POST'])
def api_text_note():
    """קליטת הערת טקסט מטלגרם עם זיהוי חכם"""
    try:
        data = request.json
        conn = init_db()
        target_id = find_lead_by_any(conn, name=data.get('client_name'), phone=data.get('phone')) or data.get(
            'lead_id') or 1

        if data.get('text_content'):
            add_interaction(conn, target_id, "הערה מטלגרם", data.get('text_content'))
            conn.close()
            return jsonify({"status": "success", "lead_id": target_id}), 200

        conn.close()
        return jsonify({"status": "error", "message": "No content"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/interactions/add', methods=['POST'])
def api_add_interaction():
    """קליטת סיכומי קול או אינטראקציות מ-n8n"""
    try:
        data = request.json
        conn = init_db()
        target_id = find_lead_by_any(conn, name=data.get('client_name'), phone=data.get('phone')) or data.get(
            'lead_id') or 1

        if data.get('summary'):
            add_interaction(conn, target_id, data.get('type', 'סיכום AI'), data.get('summary'))
            conn.close()
            return jsonify({"status": "success", "lead_id": target_id}), 200

        conn.close()
        return jsonify({"status": "error"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/update_lead', methods=['POST'])
def api_update_lead_ocr():
    """קליטת OCR מלאה: שם, ת.ז, תאריך לידה, הנפקה ותוקף"""
    try:
        data = request.json
        if 'text' in data:
            extracted = clean_ai_json(data['text'])
            data.update(extracted)

        full_name = data.get('full_name') or data.get('name') or 'לקוח חדש (סריקה)'
        id_num = data.get('id_number', '')
        birth = data.get('birth_date', '')
        issued = data.get('issue_date', '')
        expiry = data.get('expiry_date', '')

        notes = f"--- סריקת תעודת זהות אוטומטית ({datetime.now().strftime('%d/%m/%Y')}) ---\n"
        notes += f"🆔 מספר זהות: {id_num}\n"
        notes += f"🎂 תאריך לידה: {birth}\n"
        notes += f"📅 תאריך הנפקה: {issued}\n"
        notes += f"⏳ תוקף עד: {expiry}"

        db_birth = None
        if birth and '/' in birth:
            try:
                db_birth = datetime.strptime(birth, '%d/%m/%Y').strftime('%Y-%m-%d')
            except:
                db_birth = birth

        conn = init_db()
        conn.execute("INSERT INTO leads (name, birth_date, notes, source, status) VALUES (?,?,?,?,?)",
                     (full_name, db_birth, notes, "סריקת תעודת זהות", 'חדש'))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": f"Lead {full_name} created with birth date"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/leads/add', methods=['POST'])
def api_add_new_lead():
    """הזרקת ליד חדש מ-Webhook חיצוני"""
    try:
        data = request.json
        conn = init_db()
        conn.execute("INSERT INTO leads (name, phone, email, source, status) VALUES (?,?,?,?,?)",
                     (data.get('name', 'ללא שם'), data.get('phone', ''), data.get('email', ''),
                      data.get('source', 'External'), 'חדש'))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/process_har', methods=['POST'])
def api_process_har_route():
    """עדכון סטטוס עיבוד קובץ HAR"""
    try:
        data = request.json
        lead_id = data.get('lead_id', 1)
        success = api_update_har_data(lead_id, [{"type": "בדיקה אוטומטית", "company": "מערכת HAR", "prem": 0}])
        if success:
            return jsonify({"status": "success"}), 200
        return jsonify({"status": "error"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# הרצת שרת ה-API בתהליך נפרד (Daemon)
@st.cache_resource
def start_api_server():
    def run():
        import logging
        logging.getLogger('werkzeug').setLevel(logging.ERROR)
        app.run(port=5050, host='0.0.0.0', debug=False, use_reloader=False)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread


start_api_server()

# ==========================================
# UI Layout - Streamlit Dashboard
# ==========================================
if 'auth_status' not in st.session_state: st.session_state['auth_status'] = False

if not st.session_state['auth_status']:
    st.title("🔒 LeadFlow Pro - כניסה")
    with st.container():
        with st.form("login_form"):
            u = st.text_input("שם משתמש")
            p = st.text_input("סיסמה", type="password")
            if st.form_submit_button("התחבר", type="primary"):
                if u == "shon" and p == "1234":
                    st.session_state['auth_status'] = True
                    st.rerun()
                else:
                    st.error("פרטים שגויים")
    st.stop()

# כותרת ראשית
col_header, col_logout = st.columns([7, 1])
with col_header:
    st.title("🏠 דשבורד מנהלים - LeadFlow")
with col_logout:
    if st.button("🚪 התנתק", use_container_width=True):
        st.session_state['auth_status'] = False
        st.rerun()

st.success("🛰️ המערכת מחוברת ומוכנה לקליטת נתונים בפורט 5050.")

# הצגת נתונים מהירה מהמאגר
conn = init_db()
df_leads = get_leads_data(conn)
conn.close()

if not df_leads.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("👥 סה'כ לידים", len(df_leads))
    m2.metric("⏳ בטיפול פעיל", len(df_leads[df_leads['status'] == 'בטיפול']))
    m3.metric("💰 עמלות פוטנציאליות", f"₪{df_leads['estimated_commission'].sum():,.0f}")

    st.divider()
    st.subheader("📋 לידים אחרונים שנכנסו")

    # מציג רק עמודות שקיימות כדי למנוע קריסות אם חסרות עמודות ישנות
    display_cols = ['id', 'name', 'phone', 'status', 'created_at']
    existing_cols = [c for c in display_cols if c in df_leads.columns]

    st.dataframe(df_leads[existing_cols].head(10), use_container_width=True, hide_index=True)
else:
    st.info("אין לידים להצגה כרגע. המערכת מחכה לקלט מ-n8n.")