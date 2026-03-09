import streamlit as st
import pandas as pd
import requests
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import urllib.parse
import json
import io
import speech_recognition as sr
import math
import os
import time
import random
import yfinance as yf
import xml.etree.ElementTree as ET
from collections import defaultdict
import hashlib
import asyncio
from telegram import Bot
import base64
import threading
from flask import Flask, jsonify
from bs4 import BeautifulSoup
import shutil

# --- Optional Imports Handling ---
try:
    from streamlit_calendar import calendar
except ImportError:
    calendar = None
try:
    from playwright.sync_api import sync_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from reportlab.lib.units import inch

try:
    from haralyzer import HarParser
except ImportError:
    HarParser = None
try:
    from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
except ImportError:
    AgGrid = None
try:
    from bidi.algorithm import get_display
except ImportError:
    def get_display(text):
        return str(text)[::-1]


# ==========================================
# Global Styling Helper
# ==========================================
def setup_page_styling():
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False

    st.session_state.dark_mode = st.sidebar.toggle(
        "🌙 מצב לילה",
        value=st.session_state.dark_mode,
        key="global_dark_mode_toggle"
    )

    if st.session_state.dark_mode:
        theme = {"text": "#ffffff", "bg": "#0e1117", "card": "#262730", "input": "#262730", "border": "#444",
                 "plot": "plotly_dark", "header": "#363945"}
    else:
        theme = {"text": "#000000", "bg": "#f4f6f9", "card": "#ffffff", "input": "#ffffff", "border": "#d0d4d8",
                 "plot": "plotly_white", "header": "#e0e2e6"}

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700&display=swap');
        .stApp {{ background-color: {theme['bg']}; color: {theme['text']}; font-family: 'Heebo', sans-serif; direction: rtl; }}
        .main, .stMarkdown, p, h1, h2, h3, h4, h5, h6, span, label, div {{ direction: rtl; text-align: right; color: {theme['text']} !important; }}
        section[data-testid="stSidebar"] {{ background-color: {theme['card']}; border-left: 1px solid {theme['border']}; direction: rtl; text-align: right; }}
        .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{ background-color: {theme['input']} !important; color: {theme['text']} !important; border: 1px solid {theme['border']} !important; direction: rtl; text-align: right; }}
        [data-testid="stDataFrame"] {{ direction: rtl !important; }}
    </style>
    """, unsafe_allow_html=True)
    return theme


# ==========================================
# Constants
# ==========================================
COMMISSION_RATES = {
    "הראל": {"רכב": 12, "בריאות": 15, "פנסיוני": 20, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "מגדל": {"רכב": 11, "בריאות": 16, "פנסיוני": 19, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "מנורה": {"רכב": 13, "בריאות": 14, "פנסיוני": 18, "חיים": 25, "משכנתה": 20, "דירה": 11},
    "פניקס": {"רכב": 12, "בריאות": 15, "פנסיוני": 20, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "כלל": {"רכב": 12, "בריאות": 15, "פנסיוני": 19, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "הכשרה": {"רכב": 14, "בריאות": 13, "פנסיוני": 18, "חיים": 25, "משכנתה": 20, "דירה": 11},
}


# ==========================================
# Database Functions
# ==========================================
def init_db():
    db_file = 'leads_pro_ultimate.db'
    conn = sqlite3.connect(db_file, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, id_number TEXT, issue_date TEXT, 
        expiry_date TEXT, email TEXT, birth_date TEXT, marital_status TEXT, children INTEGER DEFAULT 0, 
        source TEXT, policies_json TEXT, monthly_premium REAL DEFAULT 0, estimated_commission REAL DEFAULT 0, 
        callback_date TEXT, renewal_date TEXT, notes TEXT, status TEXT DEFAULT 'חדש', 
        health_score INTEGER DEFAULT 50, lead_score INTEGER DEFAULT 50, engagement_level TEXT DEFAULT 'נמוך', 
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, task_description TEXT, 
        due_date TEXT, is_completed INTEGER DEFAULT 0, priority TEXT DEFAULT 'בינוני',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')

    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        type TEXT, summary TEXT, sentiment TEXT DEFAULT 'ניטרלי', duration_minutes INTEGER DEFAULT 0, 
        FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')

    c.execute('''CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, filename TEXT, file_data BLOB, 
        file_type TEXT, upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')
    conn.commit()
    return conn


def get_files(conn, lead_id):
    try:
        query = "SELECT id, filename, file_type, upload_date FROM files WHERE lead_id=? ORDER BY upload_date DESC"
        return pd.read_sql(query, conn, params=(lead_id,))
    except Exception as e:
        print(f"Error fetching files: {e}")
        return pd.DataFrame()


def save_file(conn, lead_id, uploaded_file):
    try:
        file_data = uploaded_file.read()
        c = conn.cursor()
        c.execute("INSERT INTO files (lead_id, filename, file_data, file_type) VALUES (?, ?, ?, ?)",
                  (lead_id, uploaded_file.name, file_data, uploaded_file.type))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False


def get_tasks(conn, lead_id=None):
    try:
        if lead_id:
            query = "SELECT id, task_description as title, due_date, priority, is_completed FROM tasks WHERE lead_id=? ORDER BY due_date ASC"
            return pd.read_sql(query, conn, params=(lead_id,))
        else:
            query = "SELECT id, task_description as title, due_date, priority, is_completed FROM tasks ORDER BY due_date ASC"
            return pd.read_sql(query, conn)
    except Exception as e:
        print(f"Error fetching tasks: {e}")
        return pd.DataFrame()


def add_task(conn, lead_id, description, priority, due_date):
    try:
        c = conn.cursor()
        c.execute("INSERT INTO tasks (lead_id, task_description, due_date, priority) VALUES (?, ?, ?, ?)",
                  (lead_id, description, due_date, priority))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding task: {e}")
        return False


def get_leads_data(conn):
    return pd.read_sql("SELECT * FROM leads ORDER BY id DESC", conn)


def get_interactions(conn, lead_id):
    return pd.read_sql("SELECT * FROM interactions WHERE lead_id=? ORDER BY date DESC", conn, params=(lead_id,))


def add_interaction(conn, lead_id, int_type, summary, sentiment='ניטרלי'):
    try:
        c = conn.cursor()
        c.execute("INSERT INTO interactions (lead_id, type, summary, sentiment) VALUES (?, ?, ?, ?)",
                  (lead_id, int_type, summary, sentiment))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding interaction: {e}")
        return False


# ==========================================
# Integration Classes
# ==========================================
class N8nIntegration:
    WEBHOOK_CONFIG = {
        "NEW_LEAD": "http://localhost:5678/webhook-test/new-lead",
        "STATUS_CHANGE": "http://localhost:5678/webhook-test/status-change",
        "TASK_WEBHOOK_URL": "http://localhost:5678/webhook-test/crm-tasks-gateway",
        "NOTIFY_WEBHOOK_URL": "http://localhost:5678/webhook-test/crm-tasks-gateway"
    }

    @staticmethod
    def send_webhook(webhook_key, payload):
        url = N8nIntegration.WEBHOOK_CONFIG.get(webhook_key)
        if not url: return None
        try:
            return requests.post(url, json=payload, timeout=7)
        except Exception as e:
            print(f"❌ n8n Error: {e}")
            return None

    @staticmethod
    def notify_new_lead(lead_data):
        return N8nIntegration.send_webhook("NEW_LEAD", lead_data)

    @staticmethod
    def notify_status_change(payload):
        return N8nIntegration.send_webhook("STATUS_CHANGE", payload)


class TelegramNotifier:
    TOKEN = "7884787146:AAEK5qN9KCwYk54JMxMzKAof4E_4wxwcZ4k"
    ADMIN_IDS = [511120215]

    @staticmethod
    def send_msg(text):
        for admin_id in TelegramNotifier.ADMIN_IDS:
            url = f"https://api.telegram.org/bot{TelegramNotifier.TOKEN}/sendMessage"
            try:
                requests.get(url, params={"chat_id": admin_id, "text": text}, timeout=5)
            except:
                pass


# ==========================================
# Finance & AI Engines
# ==========================================
class FinanceEngine:
    @staticmethod
    def calculate_smart_commission(comp, prod, prem):
        rate = COMMISSION_RATES.get(comp, {}).get(prod, 10)
        return prem * (rate / 100) * 12


class AIEngine:
    @staticmethod
    def calculate_lead_score(lead, conn):
        score = 50
        try:
            interactions = len(get_interactions(conn, lead['id']))
            score += min(interactions * 5, 30)
        except:
            pass
        return max(0, min(100, score))

    @staticmethod
    def suggest_next_action(lead):
        try:
            callback = datetime.strptime(lead.get('callback_date', ''), '%Y-%m-%d').date()
            today = datetime.now().date()
            days_diff = (callback - today).days
            if days_diff < 0:
                return f"🚨 דחוף! מאחר ב-{abs(days_diff)} ימים"
            elif days_diff == 0:
                return "📞 התקשר היום"
            elif days_diff == 1:
                return "⏰ התקשר מחר"
            else:
                return f"📅 מתוכנן ל-{days_diff} ימים"
        except:
            return "📝 עדכן תאריך חזרה"

    @staticmethod
    def identify_cross_sell(lead):
        opportunities = []
        try:
            policies = json.loads(lead.get('policies_json', '[]'))
            types = [p.get('type') for p in policies if p.get('type') != "בחר..."]
            if "רכב" in types and "בריאות" not in types: opportunities.append("💡 הצעה לביטוח בריאות")
            if lead.get('marital_status') == 'נשוי' and "חיים" not in types: opportunities.append("⚠️ חובה ביטוח חיים")
            if int(lead.get('children', 0)) >= 3 and "פנסיוני" not in types: opportunities.append(
                "👨‍👩‍👧‍👦 בדוק פנסיה למשפחה")
            if "דירה" not in types: opportunities.append("🏠 הצעה לביטוח דירה")
        except:
            pass
        return opportunities


class AISalesCoach:
    @staticmethod
    def analyze_sales_notes(lead_notes):
        if not lead_notes: return {"sentiment": "ניטרלי", "products": [], "tasks": ["אין הערות"], "tips": []}
        notes = str(lead_notes).lower()
        analysis = {"sentiment": "ניטרלי", "products": set(), "tasks": [], "tips": []}
        pos_words = ['מעוניין', 'רוצה', 'טוב', 'מצוין', 'לסגור']
        neg_words = ['יקר', 'לבטל', 'עזוב']
        pos_score = sum(1 for w in pos_words if w in notes)
        neg_score = sum(1 for w in neg_words if w in notes)
        if pos_score > neg_score:
            analysis["sentiment"] = "חיובי 🟢"
        elif neg_score > pos_score:
            analysis["sentiment"] = "שלילי 🔴"
        if 'לבדוק' in notes: analysis["tasks"].append("📌 בדיקת נתונים מול חברה")
        if 'לשלוח' in notes: analysis["tasks"].append("📤 הכנת הצעה")
        if 'יקר' in notes: analysis["tips"].append("💡 הכן השוואת מחירים")
        return analysis


def get_smart_age_insights(birth_date_str):
    if not birth_date_str: return None, []
    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        insights = []
        if age >= 60: insights.append("👴 פוטנציאל לתיקון 190")
        if birth_date.month == today.month: insights.append("🎂 יום הולדת החודש!")
        return age, insights
    except:
        return None, []


# ==========================================
# PDF & Reporting Functions
# ==========================================
def setup_hebrew_font():
    font_path = "Heebo-Regular.ttf"
    if not os.path.exists(font_path):
        try:
            url = "https://github.com/google/fonts/raw/main/ofl/heebo/Heebo-Regular.ttf"
            r = requests.get(url, timeout=5)
            with open(font_path, 'wb') as f:
                f.write(r.content)
        except:
            return False
    try:
        pdfmetrics.registerFont(TTFont('Heebo', font_path))
        return True
    except:
        return False


def fix_text(text): return get_display(str(text)) if text else ""


def generate_hebrew_pdf(lead):
    has_font = setup_hebrew_font()
    font_name = 'Heebo' if has_font else 'Helvetica'
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    title_style = ParagraphStyle(name='T', fontName=font_name, fontSize=20, alignment=TA_CENTER)
    elements = [Paragraph(fix_text(f"דוח לקוח - {lead['name']}"), title_style), Spacer(1, 20)]
    doc.build(elements)
    buffer.seek(0)
    return buffer


# ==========================================
# Market Data Functions
# ==========================================
@st.cache_data(ttl=3600)
def get_boi_rates():
    data = []
    try:
        resp = requests.get("https://boi.org.il/PublicWebServices/XML/DailyRates.xml", timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for currency in root.findall('CURRENCY'):
                code = currency.find('CURRENCYCODE').text
                if code in ['USD', 'EUR']:
                    data.append(
                        {"מדד": "דולר 🇺🇸" if code == 'USD' else "אירו 🇪🇺", "שער": float(currency.find('RATE').text)})
    except:
        pass
    return data


# ==========================================
# Utility Functions
# ==========================================
def get_stats():
    try:
        conn = sqlite3.connect('leads_pro_ultimate.db')
        query = "SELECT name, estimated_commission FROM leads WHERE callback_date <= date('now') AND status NOT IN ('נמכר', 'לא רלוונטי')"
        df = pd.read_sql(query, conn)
        conn.close()
        return json.dumps(
            {"tasks": len(df), "comm": float(df['estimated_commission'].sum()), "names_list": df['name'].tolist()},
            ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


def calculate_avg_deal_size(conn):
    df = get_leads_data(conn)
    closed = df[df['status'] == 'נמכר']
    return closed['estimated_commission'].mean() if not closed.empty else 0


def calculate_conversion_rate(conn):
    df = get_leads_data(conn)
    return (len(df[df['status'] == 'נמכר']) / len(df) * 100) if not df.empty else 0


def generate_whatsapp_link(phone, msg=""):
    clean = ''.join(filter(str.isdigit, str(phone)))
    if clean.startswith('0'): clean = '972' + clean[1:]
    return f"https://wa.me/{clean}?text={urllib.parse.quote(msg)}"


def generate_google_calendar_link(title, date_obj, time_obj=None, details=""):
    base = "https://calendar.google.com/calendar/render?action=TEMPLATE"
    dt = date_obj.strftime('%Y%m%d')
    dates = f"{dt}/{dt}"
    if time_obj:
        s = datetime.combine(date_obj, time_obj)
        e = s + timedelta(hours=1)
        dates = f"{s.strftime('%Y%m%dT%H%M%S')}/{e.strftime('%Y%m%dT%H%M%S')}"
    return f"{base}&text={urllib.parse.quote(title)}&dates={dates}&details={urllib.parse.quote(details)}&ctz=Asia/Jerusalem"


def generate_daily_report_logic(conn):
    df = get_leads_data(conn)
    if df.empty: return "אין נתונים"
    today = datetime.now().strftime('%Y-%m-%d')
    urgent = len(df[(df['callback_date'] <= today) & (~df['status'].isin(['נמכר', 'לא רלוונטי']))])
    total_comm = df[df['status'] == 'נמכר']['estimated_commission'].sum()
    return f"☀️ *דוח בוקר*\n🚨 משימות: {urgent}\n💰 הכנסות החודש: ₪{total_comm:,.0f}"


def send_telegram_alert(token, chat_id, msg):
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": msg},
                      timeout=5)
        return True
    except:
        return False


def get_top_sources(conn):
    df = get_leads_data(conn)
    if df.empty: return pd.DataFrame()
    closed = df[df['status'] == 'נמכר']
    return closed.groupby('source')['estimated_commission'].sum().sort_values(ascending=False)


def generate_ai_blessing(name):
    opts = [f"היי {name}, מזל טוב! 🎂", f"יום הולדת שמח {name}! 🎉"]
    return random.choice(opts)


@st.cache_data(ttl=300)
def get_dynamic_stock_data(tickers_dict):
    data = []
    for name, sym in tickers_dict.items():
        try:
            t = yf.Ticker(sym)
            hist = t.history(period="5d")
            if not hist.empty:
                curr = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                chg = ((curr - prev) / prev) * 100
                data.append({"מדד": name, "שער": curr, "שינוי": chg})
        except:
            continue
    return pd.DataFrame(data)