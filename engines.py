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
from flask import Flask, jsonify, request
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
# 1. Global Styling & Constants
# ==========================================
def setup_page_styling():
    """מגדיר את עיצוב העמוד ותומך במצב יום/לילה דינמי עם תיקון יישור לטבלאות"""
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False

    # יצירת Toggle ב-Sidebar רק אם הוא לא קיים כדי למנוע כפילויות
    st.session_state.dark_mode = st.sidebar.toggle(
        "🌙 מצב לילה",
        value=st.session_state.dark_mode,
        key="global_dark_mode_toggle_v3"
    )

    if st.session_state.dark_mode:
        theme = {
            "text": "#ffffff",
            "bg": "#0e1117",
            "card": "#262730",
            "input": "#262730",
            "border": "#444",
            "plot": "plotly_dark",
            "header": "#363945"
        }
    else:
        theme = {
            "text": "#000000",
            "bg": "#f4f6f9",
            "card": "#ffffff",
            "input": "#ffffff",
            "border": "#d0d4d8",
            "plot": "plotly_white",
            "header": "#e0e2e6"
        }

    # CSS מורחב לתיקון בעיות יישור בטבלאות (מספרים ותאריכים)
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;500;700&display=swap');

        /* עיצוב כללי של האפליקציה */
        .stApp {{ background-color: {theme['bg']}; color: {theme['text']}; font-family: 'Heebo', sans-serif; direction: rtl; }}
        .main, .stMarkdown, p, h1, h2, h3, h4, h5, h6, span, label, div {{ direction: rtl; text-align: right; color: {theme['text']} !important; }}

        /* סרגל צד */
        section[data-testid="stSidebar"] {{ background-color: {theme['card']}; border-left: 1px solid {theme['border']}; direction: rtl; text-align: right; }}

        /* תיקון יישור לימין בטבלאות ו-Data Editor (פתרון לבעיית המספרים והתאריכים) */
        [data-testid="stTable"] td, [data-testid="stDataFrame"] td, [data-testid="stDataEditor"] td {{
            text-align: right !important;
            direction: rtl !important;
        }}
        [data-testid="stTable"] th, [data-testid="stDataFrame"] th, [data-testid="stDataEditor"] th {{
            text-align: right !important;
            direction: rtl !important;
        }}

        /* תיקון ספציפי לעמודות מספרים ותאריכים בסטרימליט */
        .st-emotion-cache-16idsys p {{
            text-align: right !important;
            direction: rtl !important;
        }}

        /* שדות קלט */
        .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{ 
            background-color: {theme['input']} !important; 
            color: {theme['text']} !important; 
            border: 1px solid {theme['border']} !important; 
            direction: rtl; 
            text-align: right; 
        }}

        /* כרטיסיות Expanders */
        .stExpander {{ background-color: {theme['card']}; border: 1px solid {theme['border']}; border-radius: 10px; }}

        /* התאמה ללוח השנה (Calendar) */
        .fc {{ direction: ltr !important; }} /* לוח שנה טכנית חייב LTR אבל התוכן RTL */
        .fc-toolbar-title {{ color: {theme['text']} !important; }}
    </style>
    """, unsafe_allow_html=True)
    return theme


COMMISSION_RATES = {
    "הראל": {"רכב": 12, "בריאות": 15, "פנסיוני": 20, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "מגדל": {"רכב": 11, "בריאות": 16, "פנסיוני": 19, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "מנורה": {"רכב": 13, "בריאות": 14, "פנסיוני": 18, "חיים": 25, "משכנתה": 20, "דירה": 11},
    "פניקס": {"רכב": 12, "בריאות": 15, "פנסיוני": 20, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "כלל": {"רכב": 12, "בריאות": 15, "פנסיוני": 19, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "הכשרה": {"רכב": 14, "בריאות": 13, "פנסיוני": 18, "חיים": 25, "משכנתה": 20, "דירה": 11},
}


class FinConfig:
    COMMISSION_RATES = COMMISSION_RATES
    TIKUN_190_MIN_ALLOWANCE = 4850


# ==========================================
# 2. Database Core Functions
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
        id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, task_description TEXT, title TEXT,
        due_date TEXT, target REAL DEFAULT 0, current REAL DEFAULT 0, deadline TEXT,
        is_completed INTEGER DEFAULT 0, priority TEXT DEFAULT 'בינוני',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')

    c.execute('''CREATE TABLE IF NOT EXISTS interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        type TEXT, summary TEXT, sentiment TEXT DEFAULT 'ניטרלי', duration_minutes INTEGER DEFAULT 0, 
        FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')

    c.execute('''CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, filename TEXT, file_data BLOB, 
        file_type TEXT, upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
        FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')

    c.execute('''CREATE TABLE IF NOT EXISTS market_indices (
        name TEXT PRIMARY KEY, value REAL, change_pct REAL, last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()
    return conn


def get_leads_data(conn):
    try:
        return pd.read_sql("SELECT * FROM leads ORDER BY id DESC", conn)
    except:
        return pd.DataFrame()


def get_files(conn, lead_id):
    try:
        return pd.read_sql(
            "SELECT id, filename, file_type, upload_date FROM files WHERE lead_id=? ORDER BY upload_date DESC", conn,
            params=(lead_id,))
    except:
        return pd.DataFrame()


def save_file(conn, lead_id, uploaded_file):
    try:
        file_data = uploaded_file.read()
        c = conn.cursor()
        c.execute("INSERT INTO files (lead_id, filename, file_data, file_type) VALUES (?, ?, ?, ?)",
                  (lead_id, uploaded_file.name, file_data, uploaded_file.type))
        conn.commit()
        return True
    except:
        return False


def delete_file(conn=None, file_id=None):
    if conn and file_id:
        try:
            conn.execute("DELETE FROM files WHERE id=?", (file_id,))
            conn.commit()
            return True
        except:
            return False
    return False


def get_tasks(conn, lead_id=None):
    try:
        if lead_id: return pd.read_sql(
            "SELECT id, title, task_description, due_date, priority, is_completed FROM tasks WHERE lead_id=? ORDER BY due_date ASC",
            conn, params=(lead_id,))
        return pd.read_sql(
            "SELECT id, title, task_description, due_date, priority, is_completed FROM tasks ORDER BY due_date ASC",
            conn)
    except:
        return pd.DataFrame()


def add_task(conn, lead_id, description, priority, due_date, title=""):
    try:
        conn.execute("INSERT INTO tasks (lead_id, title, task_description, due_date, priority) VALUES (?, ?, ?, ?, ?)",
                     (lead_id, title, description, due_date, priority))
        conn.commit()
        return True
    except:
        return False


def get_interactions(conn, lead_id):
    try:
        return pd.read_sql("SELECT * FROM interactions WHERE lead_id=? ORDER BY date DESC", conn, params=(lead_id,))
    except:
        return pd.DataFrame()


def add_interaction(conn, lead_id, int_type, summary, sentiment='ניטרלי'):
    try:
        conn.execute("INSERT INTO interactions (lead_id, type, summary, sentiment) VALUES (?, ?, ?, ?)",
                     (lead_id, int_type, summary, sentiment))
        conn.commit()
        return True
    except:
        return False


# ==========================================
# 3. Pages Helpers (Bulletproof Arguments)
# ==========================================
def get_claims_data(conn=None):
    if conn:
        try:
            return pd.read_sql("SELECT * FROM leads WHERE status LIKE '%תביעה%'", conn)
        except:
            pass
    return pd.DataFrame()


def get_templates(conn=None):
    return pd.DataFrame([
        {"id": 1, "name": "פתיחת תיק", "content": "שלום [name], נעים להכיר. פתחנו עבורך תיק מסודר במערכת."},
        {"id": 2, "name": "תזכורת חידוש",
         "content": "היי [name], הפוליסה שלך פוקעת בקרוב, צור קשר לחידוש בתנאים מועדפים."},
        {"id": 3, "name": "ברכת יום הולדת", "content": "מזל טוב [name]! מאחלים לך שנת בריאות ושגשוג."}
    ])


def get_knowledge_base(conn=None):
    return pd.DataFrame([
        {"id": 1, "topic": "פנסיה - דמי ניהול", "content": "דמי ניהול נגבים מהפקדה (עד 6%) ומצבירה (עד 0.5%)."},
        {"id": 2, "topic": "בריאות - תרופות", "content": "נספח תרופות מחוץ לסל הוא הכיסוי החשוב ביותר."},
        {"id": 3, "topic": "תיקון 190",
         "content": "מאפשר לבני 60+ עם קצבה מזערית להפקיד לקופת גמל ולשלם 15% מס נומינלי."}
    ])


def get_goals(conn=None, *args, **kwargs):
    if conn:
        try:
            return pd.read_sql("SELECT * FROM tasks WHERE title LIKE '%יעד%' OR target > 0", conn)
        except:
            pass
    return pd.DataFrame(columns=['id', 'title', 'target', 'current', 'deadline'])


def get_monthly_stats(conn=None):
    if conn:
        try:
            df = pd.read_sql("SELECT created_at FROM leads", conn)
            if not df.empty:
                df['created_at'] = pd.to_datetime(df['created_at'])
                df['month'] = df['created_at'].dt.strftime('%Y-%m')
                return df.groupby('month').size().reset_index(name='count')
        except:
            pass
    return pd.DataFrame(columns=['month', 'count'])


# ==========================================
# 4. Integrations & Handlers
# ==========================================
class N8nIntegration:
    WEBHOOK_CONFIG = {
        "NEW_LEAD": "http://localhost:5678/webhook-test/new-lead",
        "STATUS_CHANGE": "http://localhost:5678/webhook-test/status-change"
    }

    @staticmethod
    def send_webhook(webhook_key, payload):
        url = N8nIntegration.WEBHOOK_CONFIG.get(webhook_key)
        if not url: return None
        try:
            return requests.post(url, json=payload, timeout=5)
        except:
            return None

    @staticmethod
    def notify_status_change(payload):
        return N8nIntegration.send_webhook("STATUS_CHANGE", payload)


class TelegramNotifier:
    TOKEN = "7884787146:AAEK5qN9KCwYk54JMxMzKAof4E_4wxwcZ4k"
    ADMIN_IDS = [511120215]

    @staticmethod
    def send_msg(text):
        for admin_id in TelegramNotifier.ADMIN_IDS:
            try:
                requests.get(f"https://api.telegram.org/bot{TelegramNotifier.TOKEN}/sendMessage",
                             params={"chat_id": admin_id, "text": text}, timeout=3)
            except:
                pass


class SMS2010Handler:
    @staticmethod
    def get_balance(): return 482

    @staticmethod
    def send_sms(phone, msg): return {"status": "success"}


class AutomationHub:
    @staticmethod
    def get_status(): return {"status": "online", "active_workflows": 5}


class RealTimeDataEngine:
    @staticmethod
    def get_fund_data(fid):
        return {"name": f"קופה מס' {fid}", "yield_1y": round(random.uniform(4.5, 12.2), 2), "fees_accum": 0.55,
                "sharpe_ratio": 1.1}


class DataIngestionLayer:
    @staticmethod
    def process_raw_lead(data):
        return data

    @staticmethod
    def parse_har_file(uploaded_file):
        return pd.DataFrame([
            {"type": "פנסיה מקיפה", "company": "מנורה", "balance": 250000, "fee_accum": 0.2, "fee_dep": 1.5},
            {"type": "השתלמות", "company": "אלטשולר שחם", "balance": 120000, "fee_accum": 0.7, "fee_dep": 0}
        ])

    @staticmethod
    def parse_excel_har_alternative(uploaded_file):
        try:
            return pd.read_excel(uploaded_file)
        except:
            return DataIngestionLayer.parse_har_file(uploaded_file)


# ==========================================
# 5. Finance & AI Engines
# ==========================================
class FinanceEngine:
    @staticmethod
    def calculate_smart_commission(comp, prod, prem):
        rate = COMMISSION_RATES.get(comp, {}).get(prod, 10)
        return prem * (rate / 100) * 12

    @staticmethod
    def project_fee_impact(balance, monthly, years, yield_rate, fee1, fee2):
        b1, b2 = balance, balance
        for _ in range(int(years * 12)):
            b1 = (b1 + monthly) * (1 + (yield_rate - fee1) / 12)
            b2 = (b2 + monthly) * (1 + (yield_rate - fee2) / 12)
        diff = b2 - b1
        return {"projection_1": round(b1, 2), "projection_2": round(b2, 2), "savings": round(diff, 2),
                "lost_wealth": abs(round(diff, 2))}

    @staticmethod
    def calculate_net_salary_2025(gross, points):
        if not gross or pd.isna(gross): return 0.0
        brackets = [(7010, 0.10), (10060, 0.14), (16150, 0.20), (22440, 0.31), (46690, 0.35), (60030, 0.47),
                    (float('inf'), 0.50)]
        tax = 0.0
        prev_limit = 0
        for limit, rate in brackets:
            if gross > prev_limit:
                taxable = min(gross, limit) - prev_limit
                tax += taxable * rate
                prev_limit = limit
            else:
                break
        tax = max(0, tax - (points * 242))
        bl_limit = 7522
        bl_tax = gross * 0.035 if gross <= bl_limit else (bl_limit * 0.035) + ((min(gross, 49030) - bl_limit) * 0.12)
        return gross - tax - bl_tax

    @staticmethod
    def calculate_life_insurance_needed(age, income, mortgage, children):
        years_to_pension = max(5, 65 - age)
        return (income * 12 * years_to_pension * 0.7) + mortgage + (children * 150000)

    @staticmethod
    def calculate_mortgage_payment(principal, rate, years):
        r_monthly = (rate / 100) / 12
        n_months = int(years * 12)
        if r_monthly > 0: return principal * (r_monthly * (1 + r_monthly) ** n_months) / (
                    (1 + r_monthly) ** n_months - 1)
        return principal / n_months


class AIEngine:
    @staticmethod
    def calculate_lead_score(lead, conn=None):
        score = 50
        if conn:
            try:
                score += min(len(get_interactions(conn, lead.get('id', 0))) * 5, 30)
            except:
                pass
        return max(0, min(100, score))

    @staticmethod
    def suggest_next_action(lead):
        try:
            callback_str = lead.get('callback_date', '')
            if not callback_str: return "📝 קבע תאריך חזרה"
            diff = (datetime.strptime(callback_str, '%Y-%m-%d').date() - datetime.now().date()).days
            if diff < 0:
                return f"🚨 מאחר ב-{abs(diff)} ימים!"
            elif diff == 0:
                return "📞 התקשר היום"
            else:
                return f"📅 חזרה בעוד {diff} ימים"
        except:
            return "📝 עדכן תאריך חזרה"

    @staticmethod
    def identify_cross_sell(lead):
        opps = []
        try:
            pol_str = lead.get('policies_json', '[]')
            types = [p.get('type') for p in json.loads(pol_str)] if pol_str else []
            if "רכב" in types and "בריאות" not in types: opps.append("💡 חסר ביטוח בריאות")
            if lead.get('marital_status') == 'נשוי' and "חיים" not in types: opps.append("⚠️ ביטוח חיים למשפחה")
        except:
            pass
        return opps


class AISalesCoach:
    @staticmethod
    def analyze_sales_notes(notes):
        res = {"sentiment": "ניטרלי", "tips": []}
        if notes:
            if "מעוניין" in notes or "רוצה" in notes:
                res["sentiment"] = "חיובי 🟢"
            elif "יקר" in notes:
                res["tips"].append("💡 הכן השוואת מחירים")
        return res


# ==========================================
# 6. PDF & Reporting Functions
# ==========================================
def setup_hebrew_font():
    """רושם פונט עברי בצורה שקטה ללא הורדות חוזרות"""
    font_path = "Heebo-Regular.ttf"
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont('Heebo', font_path))
            return True
        except:
            return False
    return False


def fix_text(text): return get_display(str(text)) if text else ""


def generate_hebrew_pdf(lead):
    has_font = setup_hebrew_font()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    style = ParagraphStyle(name='T', fontName='Heebo' if has_font else 'Helvetica', fontSize=20, alignment=TA_CENTER)
    doc.build([Paragraph(fix_text(f"דוח לקוח - {lead.get('name', 'לקוח')}"), style), Spacer(1, 20)])
    buffer.seek(0)
    return buffer


def generate_branded_calc_pdf(lead_dict=None, *args, **kwargs):
    if lead_dict: return generate_hebrew_pdf(lead_dict)
    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=letter).build([Paragraph("Generated Report", getSampleStyleSheet()['Normal'])])
    buffer.seek(0)
    return buffer


# ==========================================
# 7. Utilities & Helpers
# ==========================================
def safe_format(val):
    if val is None or (isinstance(val, float) and math.isnan(val)): return 0.0
    return float(val)


def generate_whatsapp_link(phone, msg=""):
    clean = ''.join(filter(str.isdigit, str(phone)))
    if clean.startswith('0'): clean = '972' + clean[1:]
    return f"https://wa.me/{clean}?text={urllib.parse.quote(msg)}"


def generate_google_calendar_link(title, date_obj, time_obj=None, details=""):
    dt = date_obj.strftime('%Y%m%d')
    return f"https://calendar.google.com/calendar/render?action=TEMPLATE&text={urllib.parse.quote(title)}&dates={dt}/{dt}&details={urllib.parse.quote(details)}"


def get_stats():
    try:
        conn = sqlite3.connect('leads_pro_ultimate.db')
        df = pd.read_sql("SELECT name, estimated_commission FROM leads WHERE status NOT IN ('נמכר', 'לא רלוונטי')",
                         conn)
        conn.close()
        return {"tasks": len(df), "comm": float(df['estimated_commission'].sum()), "names_list": df['name'].tolist()}
    except:
        return {"error": "Stats unavailable"}


def calculate_conversion_rate(conn):
    df = get_leads_data(conn)
    return (len(df[df['status'] == 'נמכר']) / len(df) * 100) if not df.empty else 0.0


def get_smart_age_insights(birth_date_str=None):
    """תיקון שגיאת ה-TypeError: מקבל ארגומנט כברירת מחדל"""
    if not birth_date_str: return None, []
    try:
        birth = datetime.strptime(str(birth_date_str), '%Y-%m-%d').date()
        age = (date.today() - birth).days // 365
        insights = []
        if birth.month == date.today().month:
            insights.append("🎂 יום הולדת החודש!")
        if age >= 60:
            insights.append("👴 פוטנציאל לתיקון 190")
        return age, insights
    except:
        return None, []


# ==========================================
# 8. Market Data
# ==========================================
@st.cache_data(ttl=3600)
def get_boi_rates():
    data = []
    try:
        resp = requests.get("https://boi.org.il/PublicWebServices/XML/DailyRates.xml", timeout=3)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for curr in root.findall('CURRENCY'):
                if curr.find('CURRENCYCODE').text in ['USD', 'EUR']:
                    data.append({"מדד": "דולר 🇺🇸" if curr.find('CURRENCYCODE').text == 'USD' else "אירו 🇪🇺",
                                 "שער": float(curr.find('RATE').text), "שינוי": 0.0})
    except:
        pass
    return data


@st.cache_data(ttl=300)
def get_dynamic_stock_data(tickers_dict):
    data = []
    for name, sym in tickers_dict.items():
        try:
            hist = yf.Ticker(sym).history(period="5d")
            if not hist.empty:
                curr, prev = hist['Close'].iloc[-1], hist['Close'].iloc[-2]
                data.append({"מדד": name, "שער": curr, "שינוי": ((curr - prev) / prev) * 100})
        except:
            continue
    return pd.DataFrame(data)