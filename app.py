import streamlit as st
import pandas as pd
from datetime import datetime
import random
import threading
from flask import Flask, jsonify, request
import json
import sqlite3
import os

# ==========================================
# 1. Page Configuration (חייב להיות הראשון!)
# ==========================================
st.set_page_config(
    page_title="LeadFlow Pro X - Ultimate",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==========================================
# 2. אתחול Session State (למניעת KeyErrors)
# ==========================================
def init_session_state():
    # אתחול נתיב שורש
    if 'root_path' not in st.session_state:
        st.session_state['root_path'] = os.getcwd()

    # אתחול טבלת לידים אם אינה קיימת (מונע קריסה בדפים המסתמכים עליה)
    if 'leads' not in st.session_state:
        st.session_state['leads'] = pd.DataFrame(columns=[
            'id', 'name', 'phone', 'email', 'source', 'policies_json',
            'callback_date', 'notes', 'status', 'lead_score', 'created_at', 'estimated_commission'
        ])

    # אתחול טבלת משימות
    if 'tasks' not in st.session_state:
        st.session_state['tasks'] = []

    # עקיפת או הגדרת סטטוס חיבור (אופציונלי למטרות פיתוח)
    if 'auth_status' not in st.session_state:
        st.session_state['auth_status'] = True


init_session_state()

# ייבוא פונקציות עזר (מומלץ לבצע לאחר set_page_config ואתחול ראשוני)
try:
    from engines import (
        init_db, get_stats, setup_page_styling, get_leads_data,
        calculate_conversion_rate
    )

    # הפעלת עיצוב המערכת
    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאה בטעינת קובץ המנוע (engines.py). אנא ודא שהוא נמצא בתיקיית השורש. פרטים: {e}")
    st.stop()

# --- חיבור למסד הנתונים ---
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאה בחיבור למסד הנתונים: {e}")
    conn = None

# ==========================================
# 3. הגדרות שרת ה-API (Flask) באמצעות Threading
# ==========================================
app = Flask(__name__)


@app.route('/stats', methods=['GET'])
def api_stats():
    data = get_stats()
    return jsonify(data)


@app.route('/api/leads/add', methods=['POST'])
def api_add_lead():
    data = request.json
    if not data:
        return jsonify({"error": "לא התקבלו נתונים"}), 400

    name = data.get('name', 'ללא שם')
    phone = data.get('phone', '')
    source = data.get('source', 'Telegram')
    email = data.get('email', '')
    notes = data.get('notes', 'נוסף דרך הטלגרם')

    try:
        db_conn = sqlite3.connect('leads_pro_ultimate.db', check_same_thread=False)
        cursor = db_conn.cursor()
        policies_json = json.dumps([{"type": "בחר...", "company": "בחר...", "prem": 0}], ensure_ascii=False)
        callback_date = datetime.now().strftime('%Y-%m-%d')

        cursor.execute("""
            INSERT INTO leads (name, phone, email, source, policies_json, callback_date, notes, status, lead_score) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, phone, email, source, policies_json, callback_date, notes, 'חדש', 50))

        db_conn.commit()
        new_lead_id = cursor.lastrowid
        db_conn.close()

        return jsonify({"status": "success", "lead_id": new_lead_id, "message": "הליד נוסף בהצלחה!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/tasks/add', methods=['POST'])
def api_add_task():
    data = request.json
    lead_id = data.get('lead_id')
    title = data.get('title')
    description = data.get('description', '')
    due_date = data.get('due_date', datetime.now().strftime('%Y-%m-%d'))
    priority = data.get('priority', 'בינוני')

    if not lead_id or not title:
        return jsonify({"error": "חובה לשלוח מזהה ליד וכותרת למשימה"}), 400

    try:
        db_conn = sqlite3.connect('leads_pro_ultimate.db', check_same_thread=False)
        db_conn.execute("INSERT INTO tasks (lead_id, title, description, due_date, priority) VALUES (?,?,?,?,?)",
                        (lead_id, title, description, due_date, priority))
        db_conn.commit()
        db_conn.close()
        return jsonify({"status": "success", "message": "המשימה נוספה בהצלחה!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/interactions/add', methods=['POST'])
def api_add_interaction():
    data = request.json
    lead_id = data.get('lead_id')
    i_type = data.get('type', 'אוטומציה')
    summary = data.get('summary')

    if not lead_id or not summary:
        return jsonify({"error": "חובה לשלוח מזהה ליד ותקציר פעולה"}), 400

    try:
        db_conn = sqlite3.connect('leads_pro_ultimate.db', check_same_thread=False)
        db_conn.execute(
            "INSERT INTO interactions (lead_id, type, summary, sentiment, duration_minutes) VALUES (?,?,?,?,?)",
            (lead_id, i_type, summary, 'ניטרלי', 0))
        db_conn.commit()
        db_conn.close()
        return jsonify({"status": "success", "message": "הפעולה תועדה בהצלחה!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/update_lead', methods=['POST'])
def update_lead():
    try:
        data = request.json
        full_name = data.get('full_name', '').strip()
        id_number = data.get('id_number', '').strip()
        expiry_date = data.get('expiry_date', '').strip()

        db_conn = sqlite3.connect('leads_pro_ultimate.db')
        cursor = db_conn.cursor()

        search_term = full_name.split()[0] if full_name else ""
        cursor.execute('SELECT name FROM leads WHERE name LIKE ?', (f"%{search_term}%",))
        result = cursor.fetchone()

        if result:
            actual_name = result[0]
            cursor.execute('''
                UPDATE leads 
                SET id_number = ?, expiry_date = ? 
                WHERE name = ?
            ''', (id_number, expiry_date, actual_name))
            db_conn.commit()
            msg = f"Updated lead: {actual_name}"
        else:
            msg = f"No lead found containing: {search_term}"

        db_conn.close()
        return jsonify({"status": "success", "message": msg}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


def run_api():
    app.run(port=8502, host='0.0.0.0', debug=False, use_reloader=False)


# הפעלת השרת רק אם השרשור לא קיים עדיין (חשוב בסביבת Streamlit)
if not any(t.name == "n8n_api" for t in threading.enumerate()):
    threading.Thread(target=run_api, name="n8n_api", daemon=True).start()

# ==========================================
# 4. תוכן דף הבית
# ==========================================
st.title("🏠 ברוכים הבאים ל-LeadFlow Pro X Ultimate")

st.markdown("""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 40px; border-radius: 15px; text-align: center; color: white; margin-bottom: 30px;'>
    <h1 style='color: white; margin: 0;'>💎 LeadFlow Pro X Ultimate</h1>
    <p style='font-size: 1.2em; margin-top: 10px; color: white;'>
        מערכת ניהול לידים מתקדמת עם AI, אוטומציות ותובנות בזמן אמת
    </p>
</div>
""", unsafe_allow_html=True)

# --- פעולות מהירות ---
st.subheader("⚡ פעולות מהירות")
qcol1, qcol2, qcol3, qcol4 = st.columns(4)

with qcol1:
    if st.button("➕ ליד חדש", use_container_width=True, type="primary"):
        st.switch_page("pages/9_➕_ליד_חדש.py")
with qcol2:
    if st.button("📊 דשבורד", use_container_width=True):
        st.switch_page("pages/1_📊_דשבורד_מנהלים.py")
with qcol3:
    if st.button("🎯 Focus", use_container_width=True):
        st.switch_page("pages/10_🎯_Focus_Mode.py")
with qcol4:
    if st.button("📋 טבלת לידים", use_container_width=True):
        st.switch_page("pages/4_📋_טבלת_לידים.py")

st.divider()

# --- סיכום יומי ---
col1, col2, col3, col4 = st.columns(4)

if conn:
    df_home = get_leads_data(conn)
else:
    df_home = pd.DataFrame()

if not df_home.empty:
    today = datetime.now().strftime('%Y-%m-%d')
    # חישוב הלידים הדחופים
    if 'callback_date' in df_home.columns and 'status' in df_home.columns:
        urgent_today = len(
            df_home[(df_home['callback_date'] <= today) & (~df_home['status'].isin(['נמכר', 'לא רלוונטי']))])
    else:
        urgent_today = 0

    current_month_start = datetime.now().replace(day=1).strftime('%Y-%m-%d')

    # חישוב מכירות החודש והכנסות
    if 'status' in df_home.columns and 'created_at' in df_home.columns and 'estimated_commission' in df_home.columns:
        month_sales_df = df_home[(df_home['status'] == 'נמכר') & (df_home['created_at'] >= current_month_start)]
        month_sales = len(month_sales_df)
        month_revenue = month_sales_df['estimated_commission'].sum()
    else:
        month_sales = 0
        month_revenue = 0

    col1.metric("🚨 דחופים להיום", urgent_today)
    col2.metric("💰 הכנסות החודש", f"₪{month_revenue:,.0f}")
    col3.metric("✅ מכירות החודש", month_sales)

    conversion_rate = calculate_conversion_rate(conn) if conn else 0.0
    col4.metric("📊 Conversion Rate", f"{conversion_rate:.1f}%")
else:
    st.info("לא נמצאו נתונים להצגה בסיכום היומי.")

st.divider()

# --- פעילות אחרונה ---
st.subheader("🕐 פעילות אחרונה")
if not df_home.empty:
    columns_to_show = ['name', 'phone', 'status', 'callback_date', 'estimated_commission']
    # וידוא שכל העמודות הנדרשות קיימות ב-DataFrame
    available_cols = [col for col in columns_to_show if col in df_home.columns]

    if available_cols:
        recent = df_home.head(5)[available_cols]
        # מילון תרגום לשמות עמודות בעברית (רק לאלו שקיימות)
        heb_columns = {
            'name': 'שם', 'phone': 'טלפון', 'status': 'סטטוס',
            'callback_date': 'חזרה', 'estimated_commission': 'עמלה'
        }
        recent.columns = [heb_columns.get(c, c) for c in available_cols]
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.warning("הנתונים הקיימים אינם מכילים את העמודות הנדרשות לתצוגת פעילות אחרונה.")
else:
    st.info("אין לידים במערכת. התחל בהוספת ליד ראשון!")

st.divider()

# --- טיפים מהירים ---
st.subheader("💡 טיפים מהירים")
tips = [
    "השתמש ב-Focus Mode לניהול משימות יומיות ממוקד.",
    "הגדר יעדים חודשיים כדי לעקוב אחרי ההתקדמות.",
    "השתמש בתבניות להאצת התקשורת עם לקוחות.",
    "בדוק את 'הבלש הביטוחי' לזיהוי הזדמנויות cross-sell.",
    "גבה את המערכת באופן קבוע דרך מסך ההגדרות."
]
st.info(f"💡 {random.choice(tips)}")