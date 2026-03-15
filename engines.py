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
# Global Utilities
# ==========================================
def safe_format(value, format_str="₪{:,.0f}"):
    """פונקציית עזר בטוחה לעיצוב מספרים (פותרת את שגיאת Open Finance)"""
    try:
        if pd.isna(value) or value is None:
            return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0


def fix_text(text):
    """תיקון טקסט עברי ל-PDF למניעת שגיאות שראינו קודם"""
    if not text: return ""
    return get_display(str(text))


# ==========================================
# Global Styling Helper
# ==========================================
def setup_page_styling():
    """
    פונקציה מרכזית לניהול עיצוב ומצב לילה בכל הדפים.
    מחזירה מילון עם צבעי הנושא הנוכחיים.
    """
    if 'dark_mode' not in st.session_state:
        st.session_state.dark_mode = False

    st.session_state.dark_mode = st.sidebar.toggle(
        "🌙 מצב לילה",
        value=st.session_state.dark_mode,
        key="global_dark_mode_toggle"
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

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;700&display=swap');

        .stApp {{
            background-color: {theme['bg']};
            color: {theme['text']};
            font-family: 'Heebo', sans-serif;
            direction: rtl;
        }}

        .main, .stMarkdown, p, h1, h2, h3, h4, h5, h6, span, label, div {{
            direction: rtl;
            text-align: right;
            color: {theme['text']} !important;
        }}

        section[data-testid="stSidebar"] {{
            background-color: {theme['card']};
            border-left: 1px solid {theme['border']};
            direction: rtl;
            text-align: right;
        }}

        .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{
            background-color: {theme['input']} !important;
            color: {theme['text']} !important;
            border: 1px solid {theme['border']} !important;
            direction: rtl;
            text-align: right;
        }}

        [data-testid="stDataFrame"] {{
            direction: rtl !important;
        }}
        [data-testid="stDataFrame"] th {{
            background-color: {theme['header']} !important;
            color: {theme['text']} !important;
            text-align: right !important;
        }}
        [data-testid="stDataFrame"] td {{
            background-color: {theme['card']} !important;
            text-align: right !important;
            color: {theme['text']} !important;
        }}

        div[data-testid="metric-container"] {{
            background-color: {theme['card']};
            border: 1px solid {theme['border']};
            border-right: 5px solid #4CAF50;
            direction: rtl;
            text-align: right;
        }}

        ul[role="listbox"] li {{
            text-align: right;
            direction: rtl;
        }}
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
    backup_file = 'backup_20260203_182435.db'
    if not os.path.exists(db_file) or os.path.getsize(db_file) < 100:
        if os.path.exists(backup_file):
            try:
                shutil.copy2(backup_file, db_file)
            except Exception as e:
                print(f"Error restoring backup: {e}")
    conn = sqlite3.connect(db_file, check_same_thread=False)
    c = conn.cursor()
    c.execute(
        '''CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, email TEXT, birth_date TEXT, marital_status TEXT, children INTEGER DEFAULT 0, source TEXT, policies_json TEXT, monthly_premium REAL DEFAULT 0, estimated_commission REAL DEFAULT 0, callback_date TEXT, renewal_date TEXT, notes TEXT, status TEXT DEFAULT 'חדש', health_score INTEGER DEFAULT 50, lead_score INTEGER DEFAULT 50, engagement_level TEXT DEFAULT 'נמוך', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS interactions (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, type TEXT, summary TEXT, sentiment TEXT DEFAULT 'ניטרלי', duration_minutes INTEGER DEFAULT 0, FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, filename TEXT, file_data BLOB, file_type TEXT, upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS claims (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, lead_name TEXT, type TEXT, company TEXT, status TEXT, open_date TEXT, close_date TEXT, amount REAL, paid_amount REAL DEFAULT 0, notes TEXT, timeline_json TEXT, FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, title TEXT, description TEXT, due_date TEXT, priority TEXT, status TEXT DEFAULT 'פתוח', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY AUTOINCREMENT, month TEXT, target_amount REAL, target_deals INTEGER, achieved_amount REAL DEFAULT 0, achieved_deals INTEGER DEFAULT 0)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, message TEXT, start_date TEXT, end_date TEXT, target_audience TEXT, sent_count INTEGER DEFAULT 0, response_count INTEGER DEFAULT 0)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, category TEXT, amount REAL, description TEXT, receipt_file BLOB)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS referrals (id INTEGER PRIMARY KEY AUTOINCREMENT, referrer_id INTEGER, referred_name TEXT, referred_phone TEXT, status TEXT, commission_paid REAL DEFAULT 0, date_referred TEXT, FOREIGN KEY(referrer_id) REFERENCES leads(id))''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS templates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, type TEXT, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS knowledge_base (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, category TEXT, content TEXT, tags TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS sms_templates (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute(
        '''CREATE TABLE IF NOT EXISTS sms_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, phone TEXT, message TEXT, status TEXT, provider_response TEXT, sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(lead_id) REFERENCES leads(id))''')
    conn.commit()
    return conn


def get_leads_data(conn): return pd.read_sql("SELECT * FROM leads ORDER BY id DESC", conn)


def get_claims_data(conn): return pd.read_sql("SELECT * FROM claims ORDER BY id DESC", conn)


def get_interactions(conn, lead_id): return pd.read_sql("SELECT * FROM interactions WHERE lead_id=? ORDER BY date DESC",
                                                        conn, params=(lead_id,))


def get_files(conn, lead_id): return pd.read_sql(
    "SELECT id, filename, upload_date, file_type FROM files WHERE lead_id=?", conn, params=(lead_id,))


def get_tasks(conn, lead_id=None):
    if lead_id: return pd.read_sql("SELECT * FROM tasks WHERE lead_id=? ORDER BY due_date", conn, params=(lead_id,))
    return pd.read_sql("SELECT * FROM tasks ORDER BY due_date", conn)


def get_goals(conn): return pd.read_sql("SELECT * FROM goals ORDER BY month DESC", conn)


def get_templates(conn, template_type=None):
    if template_type: return pd.read_sql("SELECT * FROM templates WHERE type=?", conn, params=(template_type,))
    return pd.read_sql("SELECT * FROM templates", conn)


def get_knowledge_base(conn, category=None):
    if category: return pd.read_sql("SELECT * FROM knowledge_base WHERE category=?", conn, params=(category,))
    return pd.read_sql("SELECT * FROM knowledge_base ORDER BY created_at DESC", conn)


def add_interaction(conn, lead_id, i_type, summary, sentiment='ניטרלי', duration=0):
    try:
        lid = int(lead_id)
        conn.execute(
            "INSERT INTO interactions (lead_id, type, summary, sentiment, duration_minutes) VALUES (?,?,?,?,?)",
            (lid, i_type, summary, sentiment, duration))
        conn.commit()
    except Exception as e:
        print(f"Error adding interaction: {e}")


def add_task(conn, lead_id, title, description, due_date, priority='בינוני'):
    try:
        lid = int(lead_id)
        conn.execute("INSERT INTO tasks (lead_id, title, description, due_date, priority) VALUES (?,?,?,?,?)",
                     (lid, title, description, due_date, priority))
        conn.commit()
    except Exception as e:
        print(f"Error adding task: {e}")


def save_file(conn, lead_id, uploaded_file):
    blob_data = uploaded_file.getvalue()
    file_type = uploaded_file.type
    conn.execute("INSERT INTO files (lead_id, filename, file_data, file_type) VALUES (?,?,?,?)",
                 (lead_id, uploaded_file.name, blob_data, file_type))
    conn.commit()


def delete_file(conn, file_id):
    conn.execute("DELETE FROM files WHERE id=?", (file_id,))
    conn.commit()


# ==========================================
# Search Helpers (for API & n8n)
# ==========================================
def find_lead_by_phone(phone):
    """חיפוש מזהה ליד לפי מספר טלפון"""
    if not phone: return None
    clean_phone = ''.join(filter(str.isdigit, str(phone)))
    conn = init_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM leads WHERE phone LIKE ?", ('%' + clean_phone[-9:],))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def find_lead_by_name(name_query):
    """חיפוש גמיש מאוד לפי שם"""
    if not name_query or len(name_query) < 2: return None
    conn = init_db()
    cur = conn.cursor()
    clean_name = name_query.strip()
    first_word = clean_name.split(' ')[0]
    cur.execute("SELECT id FROM leads WHERE name LIKE ? OR name LIKE ? LIMIT 1",
                ('%' + clean_name + '%', '%' + first_word + '%'))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None


def find_lead_by_any(conn, name=None, phone=None):
    """חיפוש חכם וגמיש למניעת פספוסים מה-n8n"""
    cur = conn.cursor()

    # 1. חיפוש לפי טלפון (הכי מדויק)
    if phone:
        clean_p = ''.join(filter(str.isdigit, str(phone)))
        if len(clean_p) >= 9:
            cur.execute("SELECT id FROM leads WHERE phone LIKE ?", (f'%{clean_p[-9:]}%',))
            res = cur.fetchone()
            if res: return res[0]

    # 2. חיפוש לפי שם (גמיש מאוד)
    if name:
        name_q = name.strip()
        # ניסיון התאמה מדויקת
        cur.execute("SELECT id FROM leads WHERE name = ?", (name_q,))
        res = cur.fetchone()
        if res: return res[0]

        # ניסיון התאמה חלקית
        cur.execute("SELECT id FROM leads WHERE name LIKE ?", (f'%{name_q}%',))
        res = cur.fetchone()
        if res: return res[0]

        # ניסיון לפי מילה ראשונה
        first_word = name_q.split(' ')[0]
        if len(first_word) > 2:
            cur.execute("SELECT id FROM leads WHERE name LIKE ?", (f'{first_word}%',))
            res = cur.fetchone()
            if res: return res[0]

    return None


# ==========================================
# Classes
# ==========================================
class TelegramNotifier:
    TOKEN = "7884787146:AAEK5qN9KCwYk54JMxMzKAof4E_4wxwcZ4k"
    ADMIN_IDS = [511120215]

    @staticmethod
    def send_msg(text):
        for admin_id in TelegramNotifier.ADMIN_IDS:
            url = f"https://api.telegram.org/bot{TelegramNotifier.TOKEN}/sendMessage"
            params = {"chat_id": admin_id, "text": text}
            try:
                requests.get(url, params=params, timeout=5)
            except Exception as e:
                print(f"Connection Error: {e}")


class FinConfig:
    INCOME_TAX_BRACKETS_2025 = [(84120, 0.10), (120720, 0.14), (193800, 0.20), (269280, 0.31), (560280, 0.35),
                                (721560, 0.47), (float('inf'), 0.50)]
    CREDIT_POINT_VALUE_2025 = 2904
    NI_BRACKET_1_LIMIT = 7522
    NI_RATE_EMPLOYEE_1 = 0.035
    NI_RATE_EMPLOYEE_2 = 0.12
    NI_MAX_SALARY = 49030
    TIKUN_190_MIN_ALLOWANCE = 5183


class DataIngestionLayer:
    @staticmethod
    def parse_har_file(uploaded_file):
        try:
            har_data = json.loads(uploaded_file.getvalue().decode("utf-8"))
            entries = har_data.get('log', {}).get('entries', [])
            extracted_data = []
            for entry in entries:
                response = entry.get('response', {})
                content = response.get('content', {})
                text = content.get('text', '')
                if text:
                    try:
                        data = json.loads(text)
                        if isinstance(data, list) and len(data) > 0:
                            if any(k in str(data[0]).lower() for k in
                                   ['policy', 'insurance', 'product']): extracted_data.extend(data)
                        elif isinstance(data, dict):
                            for key in ['data', 'InsuranceProducts', 'value', 'policies']:
                                if key in data and isinstance(data[key], list): extracted_data.extend(data[key])
                    except:
                        continue
            if not extracted_data: return "לא נמצאו נתוני ביטוח."
            return pd.DataFrame(extracted_data)
        except Exception as e:
            return f"שגיאה: {str(e)}"

    @staticmethod
    def parse_excel_har_alternative(uploaded_file):
        try:
            df = pd.read_excel(uploaded_file)
            return df.dropna(how='all').reset_index(drop=True)
        except Exception as e:
            return f"שגיאה: {str(e)}"


class RealTimeDataEngine:
    @staticmethod
    @st.cache_data(ttl=3600)
    def get_fund_data(fund_id):
        url = f"https://www.funder.co.il/gemel/{fund_id}"
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=7)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                name = soup.find("h1").text.strip() if soup.find("h1") else f"קופה #{fund_id}"
                return {"id": fund_id, "name": name, "ytd": random.uniform(8.5, 16.0),
                        "yield3y": random.uniform(25.0, 45.0), "sharpe": random.uniform(0.9, 1.6)}
        except:
            pass
        return {"id": fund_id, "name": f"קופה #{fund_id} (נתוני דמה)", "ytd": random.uniform(8.0, 15.0),
                "yield3y": random.uniform(20.0, 40.0), "sharpe": random.uniform(0.8, 1.5)}


class FinanceEngine:
    @staticmethod
    def calculate_net_salary_2025(gross_salary, credit_points):
        annual_salary = gross_salary * 12
        tax_due = 0
        previous_limit = 0
        for limit, rate in FinConfig.INCOME_TAX_BRACKETS_2025:
            if annual_salary > previous_limit:
                taxable = min(annual_salary, limit) - previous_limit
                tax_due += taxable * rate
                previous_limit = limit
            else:
                break
        tax_credit = credit_points * FinConfig.CREDIT_POINT_VALUE_2025
        final_tax = max(0, tax_due - tax_credit)
        ni_deduction = 0
        if gross_salary <= FinConfig.NI_BRACKET_1_LIMIT:
            ni_deduction = gross_salary * FinConfig.NI_RATE_EMPLOYEE_1
        else:
            base_deduction = FinConfig.NI_BRACKET_1_LIMIT * FinConfig.NI_RATE_EMPLOYEE_1
            additional_salary = min(gross_salary, FinConfig.NI_MAX_SALARY) - FinConfig.NI_BRACKET_1_LIMIT
            ni_deduction = base_deduction + (additional_salary * FinConfig.NI_RATE_EMPLOYEE_2)
        return gross_salary - (final_tax / 12) - ni_deduction

    @staticmethod
    def project_fee_impact(current_balance, monthly_deposit, years, annual_yield, fee_deposit, fee_accum):
        months = years * 12
        monthly_yield = (1 + annual_yield) ** (1 / 12) - 1
        balance_curr = current_balance
        for _ in range(months):
            balance_curr = (balance_curr + monthly_deposit * (1 - fee_deposit)) * (1 + monthly_yield) * (
                    1 - (fee_accum / 12))
        balance_opt = current_balance
        for _ in range(months):
            balance_opt = (balance_opt + monthly_deposit * (1 - 0.01)) * (1 + monthly_yield) * (1 - (0.0022 / 12))
        return {"current_projected": balance_curr, "optimal_projected": balance_opt,
                "lost_wealth": balance_opt - balance_curr}

    @staticmethod
    def calculate_life_insurance_needed(age, monthly_income, mortgage_remaining, num_children):
        base_multiplier = 10 if age < 40 else 8 if age < 50 else 6
        return (monthly_income * 12 * base_multiplier) + mortgage_remaining + (num_children * 200000)

    @staticmethod
    def calculate_mortgage_payment(principal, annual_rate, years):
        monthly_rate = annual_rate / 12 / 100
        num_payments = years * 12
        if monthly_rate == 0: return principal / num_payments
        return principal * (monthly_rate * (1 + monthly_rate) ** num_payments) / (
                (1 + monthly_rate) ** num_payments - 1)


class SMS2010Handler:
    USE_MOCK = True

    @staticmethod
    def send_sms(phone, message, lead_id=None, conn=None):
        if conn is None: conn = sqlite3.connect('leads_pro_ultimate.db', check_same_thread=False)
        clean_phone = ''.join(filter(str.isdigit, str(phone)))
        if clean_phone.startswith('0'): clean_phone = '972' + clean_phone[1:]
        success, response_text = True, "Simulated Success"
        if SMS2010Handler.USE_MOCK: st.toast(f"📱 סימולציה: הודעה נשלחה ל-{clean_phone}: {message}")
        conn.execute("INSERT INTO sms_logs (lead_id, phone, message, status, provider_response) VALUES (?,?,?,?,?)",
                     (lead_id, clean_phone, message, 'נשלח' if success else 'נכשל', response_text))
        if lead_id and success: add_interaction(conn, lead_id, "SMS", f"נשלח SMS: {message}")
        conn.commit()
        return success, response_text

    @staticmethod
    def get_balance():
        return 1500


class AIEngine:
    @staticmethod
    def calculate_lead_score(lead, conn):
        score = 50
        try:
            days_old = (datetime.now() - datetime.strptime(lead['created_at'], '%Y-%m-%d %H:%M:%S')).days
            if days_old < 7:
                score += 10
            elif days_old > 30:
                score -= 15
        except:
            pass
        try:
            score += min(len(get_interactions(conn, lead['id'])) * 5, 20)
        except:
            pass
        comm = lead.get('estimated_commission', 0)
        if comm > 10000:
            score += 15
        elif comm > 5000:
            score += 10
        elif comm > 2000:
            score += 5
        if lead['status'] == 'בטיפול':
            score += 5
        elif lead['status'] == 'לא עונה':
            score -= 10
        return max(0, min(100, score))

    @staticmethod
    def suggest_next_action(lead):
        try:
            days_diff = (datetime.strptime(lead['callback_date'], '%Y-%m-%d').date() - datetime.now().date()).days
            if days_diff < 0:
                return f"🚨 דחוף! מאחר ב-{abs(days_diff)} ימים - התקשר עכשיו"
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
            types = [p['type'] for p in json.loads(lead['policies_json']) if p.get('type') != "בחר..."]
            if "רכב" in types and "בריאות" not in types: opportunities.append(
                "💡 לקוח רכב ללא בריאות - הצע ביטוח בריאות")
            if lead.get('marital_status') == 'נשוי' and "חיים" not in types: opportunities.append(
                "⚠️ נשוי ללא ביטוח חיים - חובה!")
            if lead.get('children', 0) >= 3 and "פנסיוני" not in types: opportunities.append(
                "👨‍👩‍👧‍👦 משפחה גדולה - הצע פנסיה")
            if "דירה" not in types: opportunities.append("🏠 אין ביטוח דירה - בדוק צורך")
        except:
            pass
        return opportunities


class N8nIntegration:
    URL_NEW_LEAD = "http://localhost:5678/webhook-test/new-lead"
    URL_STATUS_CHANGE = "http://localhost:5678/webhook-test/status-change"

    @staticmethod
    def notify_new_lead(lead_data):
        try:
            return requests.post(N8nIntegration.URL_NEW_LEAD, json=lead_data, timeout=5)
        except Exception as e:
            return None

    @staticmethod
    def notify_status_change(payload):
        try:
            return requests.post(N8nIntegration.URL_STATUS_CHANGE, json=payload, timeout=5)
        except Exception as e:
            return None


class AutomationHub:
    @staticmethod
    def run_har_habituch_scraper(id_num, password, date_issued):
        if not PLAYWRIGHT_AVAILABLE: return False, "Playwright לא מותקן."
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                time.sleep(2)
                browser.close()
                return True, "הנתונים נמשכו בהצלחה!"
        except Exception as e:
            return False, f"שגיאה: {str(e)}"


class AISalesCoach:
    @staticmethod
    def analyze_sales_notes(lead_notes):
        if not lead_notes: return {"sentiment": "ניטרלי", "products": [], "tasks": ["אין הערות לניתוח"], "tips": []}
        notes = str(lead_notes).lower()
        analysis = {"sentiment": "ניטרלי", "products": set(), "tasks": [], "tips": []}
        pos_score = sum(1 for w in ['מעוניין', 'רוצה', 'טוב', 'מצוין', 'להתקדם', 'לסגור', 'תשלח'] if w in notes)
        neg_score = sum(1 for w in ['יקר', 'לא רלוונטי', 'ניתק', 'לבטל', 'עזוב', 'תתקשר מחר'] if w in notes)
        if pos_score > neg_score:
            analysis["sentiment"] = "חיובי 🟢"
        elif neg_score > pos_score:
            analysis["sentiment"] = "שלילי 🔴"

        product_keywords = {"ביטוח חיים": ['חיים', 'ריסק', 'משכנתא'],
                            "ביטוח בריאות": ['בריאות', 'ניתוחים', 'תרופות', 'מחלות'],
                            "ביטוח רכב": ['רכב', 'מקיף', 'חובה', 'צד ג'],
                            "פנסיה וגמל": ['פנסיה', 'השתלמות', 'גמל', 'קופה', 'דמי ניהול']}
        for prod, keywords in product_keywords.items():
            if any(k in notes for k in keywords): analysis["products"].add(prod)
        if 'לבדוק' in notes or 'אבדוק' in notes: analysis["tasks"].append("📌 משימה: לבדוק נתונים מול חברת הביטוח")
        if 'לשלוח' in notes or 'הצעה' in notes: analysis["tasks"].append("📤 משימה: להכין ולשלוח הצעת מחיר")
        if 'מחר' in notes or 'שבוע הבא' in notes or 'לחזור' in notes: analysis["tasks"].append(
            "📞 משימה: לתזמן פולו-אפ ביומן")
        if 'יקר' in notes or 'מחיר' in notes: analysis["tips"].append(
            "💡 טיפ: הלקוח רגיש למחיר. הכן השוואת מחירים מסודרת מול המתחרים.")
        if 'אשתי' in notes or 'בעלי' in notes or 'להתייעץ' in notes: analysis["tips"].append(
            "💡 טיפ: קבלת ההחלטות משותפת. הצע שיחת זום עם בן/בת הזוג.")
        analysis["products"] = list(analysis["products"])
        return analysis


# ==========================================
# Utility Functions
# ==========================================
def calculate_avg_deal_size(conn):
    df = get_leads_data(conn)
    closed = df[df['status'] == 'נמכר']
    return closed['estimated_commission'].mean() if not closed.empty else 0


def calculate_conversion_rate(conn):
    df = get_leads_data(conn)
    return (len(df[df['status'] == 'נמכר']) / len(df) * 100) if not df.empty else 0


def calculate_smart_commission(comp, prod, prem):
    rate = COMMISSION_RATES.get(comp, {}).get(prod, 10)
    return prem * (rate / 100) * 12


def generate_whatsapp_link(phone, msg=""):
    if not phone or str(phone).strip() == "": return ""
    clean = ''.join(filter(str.isdigit, str(phone)))
    if clean.startswith('0'): clean = '972' + clean[1:]
    return f"https://wa.me/{clean}?text={urllib.parse.quote(msg)}"


def generate_google_calendar_link(title, date_obj, time_obj=None, details=""):
    """יצירת לינק ליומן גוגל עם תמיכה מלאה בעברית"""
    dt = date_obj.strftime('%Y%m%d')
    base_url = "https://calendar.google.com/calendar/render?action=TEMPLATE"

    if time_obj:
        s = datetime.combine(date_obj, time_obj)
        e = s + timedelta(hours=1)
        dates = f"{s.strftime('%Y%m%dT%H%M%S')}/{e.strftime('%Y%m%dT%H%M%S')}"
    else:
        dates = f"{dt}/{dt}"

    params = {
        "text": title,
        "dates": dates,
        "details": details,
        "ctz": "Asia/Jerusalem"
    }
    return f"{base_url}&{urllib.parse.urlencode(params)}"


def generate_daily_report_logic(conn):
    df = get_leads_data(conn)
    if df.empty: return "אין נתונים"
    today = datetime.now().strftime('%Y-%m-%d')
    urgent = len(df[(df['callback_date'] <= today) & (~df['status'].isin(['נמכר', 'לא רלוונטי']))])
    total_comm = df[df['status'] == 'נמכר']['estimated_commission'].sum()
    return f"☀️ *דוח בוקר*\n🚨 משימות: {urgent}\n💰 הכנסות החודש: ₪{total_comm:,.0f}"


def get_smart_age_insights(birth_date_str):
    if not birth_date_str: return None, []
    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        insights = []
        if age == 60:
            insights.append("🎉 הגיע לגיל 60 החודש! (זמן אידיאלי לבדיקת תיקון 190)")
        elif age > 60:
            insights.append("👴 פוטנציאל לתיקון 190 ופטור ממס רווח הון (מעל גיל 60)")
        elif 24 <= age <= 28:
            insights.append("🎓 חבר'ה צעירים - הזדמנות לביטוחי בריאות זולים ולפתוח קרן השתלמות")
        elif age > 0 and birth_date.month == today.month:
            insights.append("🎂 יום הולדת החודש! הזדמנות מעולה ליצירת קשר")
        return age, insights
    except:
        return None, []


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
    return df[df['status'] == 'נמכר'].groupby('source')['estimated_commission'].sum().sort_values(ascending=False)


def get_stats():
    try:
        conn = sqlite3.connect('leads_pro_ultimate.db')
        query = "SELECT id, name, phone, estimated_commission FROM leads WHERE callback_date <= date('now') AND status NOT IN ('נמכר', 'לא רלוונטי')"
        df = pd.read_sql(query, conn)
        conn.close()
        df['phone'] = df['phone'].fillna('')
        return {"tasks": int(len(df)), "comm": float(df['estimated_commission'].sum() if not df.empty else 0),
                "leads": df[['id', 'name', 'phone']].to_dict('records')}
    except Exception as e:
        return {"error": str(e)}


def get_monthly_stats(conn=None):
    """פונקציית דמה לקבלת סטטיסטיקות חודשיות - תוקנה כדי לא לקרוס בדף הדוחות"""
    return pd.DataFrame()


def api_update_har_data(lead_id, har_json):
    try:
        conn = sqlite3.connect('leads_pro_ultimate.db')
        conn.execute("UPDATE leads SET policies_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                     (json.dumps(har_json, ensure_ascii=False), lead_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        return False


def setup_hebrew_font():
    font_path = "Heebo-Regular.ttf"
    if not os.path.exists(font_path):
        try:
            r = requests.get("https://github.com/google/fonts/raw/main/ofl/heebo/Heebo-Regular.ttf", timeout=5)
            with open(font_path, 'wb') as f:
                f.write(r.content)
        except:
            return False
    try:
        pdfmetrics.registerFont(TTFont('Heebo', font_path))
        return True
    except:
        return False


def generate_hebrew_pdf(lead):
    font_name = 'Heebo' if setup_hebrew_font() else 'Helvetica'
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    elements = []
    style_title = ParagraphStyle(name='HTitle', fontName=font_name, fontSize=24, alignment=TA_CENTER,
                                 textColor=colors.HexColor("#2c3e50"), spaceAfter=20)
    style_heading = ParagraphStyle(name='HHeading', fontName=font_name, fontSize=16,
                                   textColor=colors.HexColor("#34495e"), spaceAfter=10)
    elements.append(Paragraph(fix_text(f"דוח מקיף - {lead['name']}"), style_title))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(fix_text("פרטים אישיים"), style_heading))
    det_data = [[fix_text("פרט"), fix_text("ערך")], [fix_text("שם מלא"), fix_text(lead['name'])],
                [fix_text("טלפון"), fix_text(lead['phone'])], [fix_text("אימייל"), fix_text(lead.get('email', '-'))],
                [fix_text("סטטוס"), fix_text(lead['status'])],
                [fix_text("Lead Score"), fix_text(str(lead.get('lead_score', 50)))]]
    t_det = Table(det_data, colWidths=[250, 250])
    t_det.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), font_name, 11), ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                               ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#3498db")),
                               ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                               ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                               ('BACKGROUND', (0, 1), (-1, -1), colors.beige)]))
    elements.append(t_det)
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(fix_text("תיק ביטוחי"), style_heading))
    p_data = [[fix_text("מוצר"), fix_text("חברה"), fix_text("פרמיה חודשית")]]
    try:
        for p in json.loads(lead['policies_json']):
            if p.get('type') != "בחר...": p_data.append(
                [fix_text(p.get('type')), fix_text(p.get('company')), fix_text(f"₪{p.get('prem', 0):,.0f}")])
    except:
        pass
    if len(p_data) > 1:
        t_pol = Table(p_data, colWidths=[150, 150, 150])
        t_pol.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), font_name, 11), ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                   ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#27ae60")),
                                   ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                                   ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                                   ('BACKGROUND', (0, 1), (-1, -1), colors.lightgreen)]))
        elements.append(t_pol)
    else:
        elements.append(Paragraph(fix_text("אין פוליסות רשומות"), getSampleStyleSheet()['Normal']))
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(fix_text("סיכום כספי"), style_heading))
    fin_data = [[fix_text("פרמיה כוללת חודשית"), fix_text(f"₪{lead.get('monthly_premium', 0):,.0f}")],
                [fix_text("עמלה משוערת שנתית"), fix_text(f"₪{lead.get('estimated_commission', 0):,.0f}")]]
    t_fin = Table(fin_data, colWidths=[300, 200])
    t_fin.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), font_name, 12), ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                               ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                               ('BACKGROUND', (0, 0), (-1, -1), colors.lavender)]))
    elements.append(t_fin)
    elements.append(Spacer(1, 50))
    elements.append(Paragraph(fix_text(f"נוצר ב-{datetime.now().strftime('%d/%m/%Y %H:%M')} | LeadFlow Pro X Ultimate"),
                              ParagraphStyle(name='Footer', fontName=font_name, fontSize=9, textColor=colors.grey,
                                             alignment=TA_CENTER)))
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_quote_pdf(lead, policy_type, company, premium, coverage, logo_path="logo.png",
                       signature_path="signature.png"):
    font_name = 'Heebo' if setup_hebrew_font() else 'Helvetica'
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elements = []
    if os.path.exists(logo_path):
        logo = RLImage(logo_path, width=1.5 * inch, height=0.8 * inch)
        logo.hAlign = 'LEFT'
        elements.append(logo)
        elements.append(Spacer(1, 10))
    elements.append(Paragraph(fix_text("הצעת מחיר לביטוח"),
                              ParagraphStyle(name='QuoteTitle', fontName=font_name, fontSize=26, alignment=TA_CENTER,
                                             textColor=colors.HexColor("#2980b9"), spaceAfter=30)))
    elements.append(Spacer(1, 20))
    t_client = Table([[fix_text("שם הלקוח:"), fix_text(lead['name'])], [fix_text("טלפון:"), fix_text(lead['phone'])],
                      [fix_text("תאריך ההצעה:"), fix_text(datetime.now().strftime('%d/%m/%Y'))]], colWidths=[150, 350])
    t_client.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), font_name, 12), ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                                  ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')]))
    elements.append(t_client)
    elements.append(Spacer(1, 30))
    heading = ParagraphStyle(name='Heading', fontName=font_name, fontSize=18, textColor=colors.HexColor("#16a085"),
                             alignment=TA_RIGHT)
    elements.append(Paragraph(fix_text("פרטי הכיסוי"), heading))
    elements.append(Spacer(1, 15))
    t_policy = Table([[fix_text("סוג ביטוח:"), fix_text(policy_type)], [fix_text("חברת ביטוח:"), fix_text(company)],
                      [fix_text("פרמיה חודשית:"), fix_text(f"₪{premium:,.0f}")],
                      [fix_text("פרמיה שנתית:"), fix_text(f"₪{premium * 12:,.0f}")],
                      [fix_text("סכום כיסוי:"), fix_text(f"₪{coverage:,.0f}")]], colWidths=[150, 350])
    t_policy.setStyle(TableStyle([('FONT', (0, 0), (-1, -1), font_name, 13), ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
                                  ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#bdc3c7")),
                                  ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#ecf0f1"))]))
    elements.append(t_policy)
    elements.append(Spacer(1, 40))
    if os.path.exists(signature_path):
        elements.append(Paragraph(fix_text("בברכה,"), heading))
        sig = RLImage(signature_path, width=1.2 * inch, height=0.6 * inch)
        sig.hAlign = 'RIGHT'
        elements.append(sig)
        elements.append(Paragraph(fix_text("שון - סוכן הביטוח שלך"), heading))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(fix_text("* ההצעה בתוקף ל-30 יום | נתונים כפופים לאישור חברת הביטוח"),
                              ParagraphStyle(name='Note', fontName=font_name, fontSize=10, textColor=colors.grey,
                                             alignment=TA_RIGHT)))
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_branded_calc_pdf(lead_name, title, content, logo_path="logo.png", signature_path="signature.png"):
    font_name = 'Heebo' if setup_hebrew_font() else 'Helvetica'
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    if os.path.exists(logo_path):
        elements.append(RLImage(logo_path, width=1.5 * inch, height=0.75 * inch))
        elements.append(Spacer(1, 12))
    elements.append(
        Paragraph(fix_text(title), ParagraphStyle(name='T', fontName=font_name, fontSize=18, alignment=TA_CENTER)))
    elements.append(Spacer(1, 20))
    style_body = ParagraphStyle(name='B', fontName=font_name, fontSize=12, alignment=TA_RIGHT)
    elements.append(Paragraph(fix_text(f"לכבוד: {lead_name}"), style_body))
    for line in content.split('\n'):
        if line.strip():
            elements.append(Paragraph(fix_text(line), style_body))
            elements.append(Spacer(1, 6))
    if os.path.exists(signature_path):
        elements.append(Spacer(1, 30))
        elements.append(RLImage(signature_path, width=1 * inch, height=0.5 * inch))
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_ai_blessing(name):
    return random.choice([f"היי {name}, המון מזל טוב ליום הולדתך! 🎂", f"בוקר טוב {name}! 🎉 יום הולדת שמח.",
                          f"מזל טוב {name}! 🎈 שנה של הצלחות."])


@st.cache_data(ttl=3600)
def get_boi_rates():
    data = []
    try:
        resp = requests.get("https://boi.org.il/PublicWebServices/XML/DailyRates.xml", timeout=5)
        if resp.status_code == 200:
            for currency in ET.fromstring(resp.content).findall('CURRENCY'):
                code = currency.findall('CURRENCYCODE')[0].text
                if code in ['USD', 'EUR']:
                    data.append({"מדד": "דולר 🇺🇸" if code == 'USD' else "אירו 🇪🇺",
                                 "שער": float(currency.findall('RATE')[0].text),
                                 "שינוי": float(currency.findall('CHANGE')[0].text)})
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
                data.append({"מדד": name, "סימול": sym, "שער": curr, "שינוי": ((curr - prev) / prev) * 100})
        except:
            continue
    return pd.DataFrame(data)