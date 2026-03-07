import streamlit as st
import threading
from flask import Flask, jsonify

# Import necessary functions
from engines import init_db, get_stats, setup_page_styling

# ==========================================
# 1. הגדרות ועיצוב גלובלי
# ==========================================
st.set_page_config(
    page_title="LeadFlow Pro X - Ultimate",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# הפעלת העיצוב הגלובלי ומצב הלילה
theme = setup_page_styling()

# --- Database Connection ---
conn = init_db()

# --- API Server ---
app = Flask(__name__)
@app.route('/stats')
def api_stats():
    data = get_stats()
    return jsonify(data)

def run_api():
    app.run(port=8502, host='0.0.0.0', debug=False, use_reloader=False)

if not any(t.name == "n8n_api" for t in threading.enumerate()):
    threading.Thread(target=run_api, name="n8n_api", daemon=True).start()

# ==========================================
# 2. Main Home Page
# ==========================================
st.title("🏠 ברוכים הבאים ל-LeadFlow Pro X Ultimate")

st.markdown(f"""
<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            padding: 40px; border-radius: 15px; text-align: center; color: white; margin-bottom: 30px;'>
    <h1 style='color: white; margin: 0;'>💎 LeadFlow Pro X Ultimate</h1>
    <p style='font-size: 1.2em; margin-top: 10px; color: white;'>
        מערכת ניהול לידים מתקדמת עם AI, אוטומציות ותובנות בזמן אמת
    </p>
</div>
""", unsafe_allow_html=True)

st.header("ניווט")
st.info(
    "האפליקציה אורגנה מחדש במבנה של Multi-Page App.\n\n"
    "אנא השתמש בתפריט הניווט שנוצר אוטומטית בסרגל הצד כדי לעבור בין הדפים השונים."
)
