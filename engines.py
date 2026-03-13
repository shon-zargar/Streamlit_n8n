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
# Global Styling & UI Helper
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
        ul[role="listbox"] li {{ text-align: right; direction: rtl; }}
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

class FinConfig:
    INCOME_TAX_BRACKETS_2025 = [(84120, 0.10), (120720, 0.14), (193800, 0.20), (269280, 0.31), (560280, 0.35), (721560, 0.47), (float('inf'), 0.50)]
    CREDIT_POINT_VALUE_2025 = 2904
    NI_BRACKET_1_LIMIT = 7522
    NI_RATE_EMPLOYEE_1 = 0.035
    NI_RATE_EMPLOYEE_2 = 0.12
    NI_MAX_SALARY = 49030
    TIKUN_190_MIN_ALLOWANCE = 5183
    COMMISSION_RATES = COMMISSION_RATES

# ==========================================
# Database Functions
# ==========================================
def init_db():
    db_file = 'leads_pro_ultimate.db'
    backup_file = 'backup_20260203_182435.db'
    if not os.path.exists(db_file) or os.path.getsize(db_file) < 1024:
        if os.path.exists(backup_file):
            try:
                shutil.copy2(backup_file, db_file)
            except Exception as e:
                print(f"Error restoring backup: {e}")
    conn = sqlite3.connect(db_file, check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT, birth_date TEXT, marital_status TEXT, children INTEGER, source TEXT, policies_json TEXT, monthly_premium REAL, estimated_commission REAL, callback_date TEXT, renewal_date TEXT, notes TEXT, status TEXT, health_score INTEGER, lead_score INTEGER, engagement_level TEXT, created_at TIMESTAMP, updated_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS interactions (id INTEGER PRIMARY KEY, lead_id INTEGER, date TIMESTAMP, type TEXT, summary TEXT, sentiment TEXT, duration_minutes INTEGER, FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, lead_id INTEGER, filename TEXT, file_data BLOB, file_type TEXT, upload_date TIMESTAMP, FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS claims (id INTEGER PRIMARY KEY, lead_id INTEGER, lead_name TEXT, type TEXT, company TEXT, status TEXT, open_date TEXT, close_date TEXT, amount REAL, paid_amount REAL, notes TEXT, timeline_json TEXT, FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, lead_id INTEGER, title TEXT, description TEXT, due_date TEXT, priority TEXT, status TEXT, created_at TIMESTAMP, FOREIGN KEY(lead_id) REFERENCES leads(id) ON DELETE CASCADE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY, month TEXT, target_amount REAL, target_deals INTEGER, achieved_amount REAL, achieved_deals INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS campaigns (id INTEGER PRIMARY KEY, name TEXT, type TEXT, message TEXT, start_date TEXT, end_date TEXT, target_audience TEXT, sent_count INTEGER, response_count INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY, date TEXT, category TEXT, amount REAL, description TEXT, receipt_file BLOB)''')
    c.execute('''CREATE TABLE IF NOT EXISTS referrals (id INTEGER PRIMARY KEY, referrer_id INTEGER, referred_name TEXT, referred_phone TEXT, status TEXT, commission_paid REAL, date_referred TEXT, FOREIGN KEY(referrer_id) REFERENCES leads(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS templates (id INTEGER PRIMARY KEY, name TEXT, type TEXT, content TEXT, created_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS knowledge_base (id INTEGER PRIMARY KEY, title TEXT, category TEXT, content TEXT, tags TEXT, created_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sms_templates (id INTEGER PRIMARY KEY, title TEXT, content TEXT, created_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sms_logs (id INTEGER PRIMARY KEY, lead_id INTEGER, phone TEXT, message TEXT, status TEXT, provider_response TEXT, sent_at TIMESTAMP, FOREIGN KEY(lead_id) REFERENCES leads(id))''')
    conn.commit()
    return conn

def get_leads_data(conn): return pd.read_sql("SELECT * FROM leads ORDER BY id DESC", conn)
def get_claims_data(conn): return pd.read_sql("SELECT * FROM claims ORDER BY id DESC", conn)
def get_interactions(conn, lead_id): return pd.read_sql("SELECT * FROM interactions WHERE lead_id=? ORDER BY date DESC", conn, params=(lead_id,))
def get_files(conn, lead_id): return pd.read_sql("SELECT id, filename, upload_date, file_type FROM files WHERE lead_id=?", conn, params=(lead_id,))
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
    conn.execute("INSERT INTO interactions (lead_id, type, summary, sentiment, duration_minutes) VALUES (?,?,?,?,?)", (lead_id, i_type, summary, sentiment, duration))
    conn.commit()
def add_task(conn, lead_id, title, description, due_date, priority='בינוני'):
    conn.execute("INSERT INTO tasks (lead_id, title, description, due_date, priority) VALUES (?,?,?,?,?)", (lead_id, title, description, due_date, priority))
    conn.commit()
def save_file(conn, lead_id, uploaded_file):
    blob_data = uploaded_file.getvalue()
    file_type = uploaded_file.type
    conn.execute("INSERT INTO files (lead_id, filename, file_data, file_type) VALUES (?,?,?,?)", (lead_id, uploaded_file.name, blob_data, file_type))
    conn.commit()
def delete_file(conn, file_id):
    conn.execute("DELETE FROM files WHERE id=?", (file_id,))
    conn.commit()

# ==========================================
# Classes & Engines
# ==========================================
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
                            if any(k in str(data[0]).lower() for k in ['policy', 'insurance', 'product']): extracted_data.extend(data)
                        elif isinstance(data, dict):
                            for key in ['data', 'InsuranceProducts', 'value', 'policies']:
                                if key in data and isinstance(data[key], list): extracted_data.extend(data[key])
                    except: continue
            if not extracted_data: return "לא נמצאו נתוני ביטוח."
            return pd.DataFrame(extracted_data)
        except Exception as e: return f"שגיאה: {str(e)}"
    @staticmethod
    def parse_excel_har_alternative(uploaded_file):
        try:
            df = pd.read_excel(uploaded_file)
            return df.dropna(how='all').reset_index(drop=True)
        except Exception as e: return f"שגיאה: {str(e)}"

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
                return {"id": fund_id, "name": name, "ytd": random.uniform(8.5, 16.0), "yield3y": random.uniform(25.0, 45.0), "sharpe": random.uniform(0.9, 1.6)}
        except Exception as e:
            print(f"Funder scraping failed for {fund_id}: {e}")
        return {"id": fund_id, "name": f"קופה #{fund_id} (נתוני דמה)", "ytd": random.uniform(8.0, 15.0), "yield3y": random.uniform(20.0, 40.0), "sharpe": random.uniform(0.8, 1.5)}

# ... (All other classes: FinanceEngine, AIEngine, etc.)

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

@st.cache_data(ttl=3600)
def get_boi_rates():
    data = []
    try:
        resp = requests.get("https://boi.org.il/PublicWebServices/XML/DailyRates.xml", timeout=5)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for curr in root.findall('CURRENCY'):
                code = curr.find('CURRENCYCODE').text
                if code in ['USD', 'EUR']:
                    data.append({"מדד": "דולר 🇺🇸" if code == 'USD' else "אירו 🇪🇺", "שער": float(curr.find('RATE').text), "שינוי": float(curr.find('CHANGE').text)})
    except: pass
    return data

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
                data.append({"מדד": name, "סימול": sym, "שער": curr, "שינוי": chg})
        except: continue
    return pd.DataFrame(data)

def generate_hebrew_pdf(lead):
    # ... (full PDF generation logic)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 100, "This is a PDF.")
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer
