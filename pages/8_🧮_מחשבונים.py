import streamlit as st
import pandas as pd
from datetime import date, datetime
import math
import io

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="מחשבונים", page_icon="🧮")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. ייבוא בטוח מתוך המנוע ---
try:
    from engines import (
        init_db, get_leads_data, add_interaction, save_file,
        generate_branded_calc_pdf, setup_page_styling
    )

    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבים ב-engines.py. {e}")
    st.stop()


# --- 4. פונקציות חישוב מקומיות ועצמאיות (מונע קריסות של חוסר במנוע) ---
def safe_format(val):
    if val is None or (isinstance(val, float) and math.isnan(val)): return 0.0
    return float(val)


def calc_mortgage(principal, rate, m_years):
    r_monthly = (rate / 100) / 12
    n_months = int(m_years * 12)
    if r_monthly > 0:
        return principal * (r_monthly * (1 + r_monthly) ** n_months) / ((1 + r_monthly) ** n_months - 1)
    return principal / n_months


def calc_life_insurance(age, income, mortgage, children):
    years_to_pension = max(5, 65 - age)
    income_replacement = income * 12 * years_to_pension * 0.7
    child_support = children * 150000
    return income_replacement + mortgage + child_support


def calc_fee_impact(balance, monthly, years, yield_rate, fee_current, fee_target):
    b_curr, b_targ = balance, balance
    for _ in range(int(years * 12)):
        b_curr = (b_curr + monthly) * (1 + (yield_rate - fee_current) / 12)
        b_targ = (b_targ + monthly) * (1 + (yield_rate - fee_target) / 12)
    return b_curr, b_targ, abs(b_targ - b_curr)


# מילון עמלות מקומי לגיבוי
LOCAL_COMMISSION_RATES = {
    "הראל": {"רכב": 12, "בריאות": 15, "פנסיוני": 20, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "מגדל": {"רכב": 11, "בריאות": 16, "פנסיוני": 19, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "מנורה": {"רכב": 13, "בריאות": 14, "פנסיוני": 18, "חיים": 25, "משכנתה": 20, "דירה": 11},
    "פניקס": {"רכב": 12, "בריאות": 15, "פנסיוני": 20, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "כלל": {"רכב": 12, "בריאות": 15, "פנסיוני": 19, "חיים": 25, "משכנתה": 20, "דירה": 10},
    "הכשרה": {"רכב": 14, "בריאות": 13, "פנסיוני": 18, "חיים": 25, "משכנתה": 20, "דירה": 11},
}

# --- חיבור למסד נתונים ---
try:
    conn = init_db()
except Exception:
    conn = None

st.title("🧮 מחשבוני ביטוח ופיננסים")
st.caption("כלי עזר לחישוב עמלות, השפעת דמי ניהול וביטוח חיים.")

tabs = st.tabs(["📉 הפסד דמי ניהול", "💡 ביטוח חיים", "🏠 משכנתה", "💰 עמלות"])

# --- TAB 1: דמי ניהול ---
with tabs[0]:
    st.header("📉 השפעת דמי ניהול על הצבירה")
    st.markdown("מחשבון זה מדגים ללקוח כמה כסף הוא מאבד בגלל דמי ניהול גבוהים.")

    col1, col2, col3 = st.columns(3)
    balance = col1.number_input("צבירה נוכחית (₪)", min_value=0, value=100000, step=10000, key="fee_bal")
    monthly = col2.number_input("הפקדה חודשית (₪)", min_value=0, value=2000, step=100, key="fee_mon")
    years = col3.slider("תקופת חישוב (בשנים)", min_value=1, max_value=40, value=20, key="fee_yrs")

    col4, col5, col6 = st.columns(3)
    yield_rate = col4.number_input("תשואה שנתית משוערת (%)", min_value=0.0, max_value=15.0, value=5.0, step=0.5,
                                   key="fee_yld") / 100
    fee_current = col5.number_input("דמי ניהול נוכחיים מצבירה (%)", min_value=0.0, max_value=3.0, value=0.8, step=0.05,
                                    key="fee_curr") / 100
    fee_target = col6.number_input("דמי ניהול יעד מצבירה (%)", min_value=0.0, max_value=3.0, value=0.4, step=0.05,
                                   key="fee_trg") / 100

    if st.button("חשב השפעה", type="primary", key="btn_fee"):
        b_curr, b_targ, lost_wealth = calc_fee_impact(balance, monthly, years, yield_rate, fee_current, fee_target)

        st.divider()
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("צבירה בתנאים נוכחיים", f"₪{safe_format(b_curr):,.0f}")
        res_col2.metric("צבירה בתנאי יעד", f"₪{safe_format(b_targ):,.0f}")
        res_col3.metric("💸 הפסד צפוי", f"₪{safe_format(lost_wealth):,.0f}", delta=f"-₪{safe_format(lost_wealth):,.0f}",
                        delta_color="inverse")

# --- TAB 2: ביטוח חיים ---
with tabs[1]:
    st.header("💡 מחשבון סכום ביטוח חיים מומלץ")

    licol1, licol2, licol3 = st.columns(3)
    age = licol1.number_input("גיל המבוטח", min_value=18, max_value=80, value=35, key="li_age")
    income = licol2.number_input("הכנסה חודשית (₪)", min_value=0, value=15000, step=1000, key="li_inc")
    spouse_income = licol3.number_input("הכנסת בן/בת זוג (₪)", min_value=0, value=10000, step=1000, key="li_sp_inc")

    licol4, licol5 = st.columns(2)
    children = licol4.number_input("מספר ילדים סמוכים לשולחן", min_value=0, max_value=10, value=2, key="li_kids")
    mortgage = licol5.number_input("יתרת משכנתה והלוואות (₪)", min_value=0, value=800000, step=50000, key="li_mort")

    if st.button("חשב כיסוי נדרש", key="btn_li"):
        total_needed = calc_life_insurance(age, income, mortgage, children)
        st.success(f"הסכום המומלץ לביטוח חיים הוא כ- **₪{safe_format(total_needed):,.0f}**")
        st.caption("* חישוב זה הנו הערכה גסה ואינו מחליף ייעוץ פנסיוני מקצועי.")

# --- TAB 3: משכנתה ---
with tabs[2]:
    st.header("🏠 מחשבון החזר משכנתה משוער")

    mcol1, mcol2, mcol3 = st.columns(3)
    principal = mcol1.number_input("סכום ההלוואה (₪)", min_value=100000, value=1000000, step=50000, key="mort_prin")
    rate = mcol2.number_input("ריבית שנתית ממוצעת (%)", min_value=0.1, max_value=15.0, value=3.5, step=0.1,
                              key="mort_rate")
    m_years = mcol3.number_input("תקופת הלוואה (בשנים)", min_value=5, max_value=30, value=25, key="mort_yrs")

    monthly_payment = calc_mortgage(principal, rate, m_years)

    st.metric("💳 החזר חודשי צפוי", f"₪{safe_format(monthly_payment):,.0f}")

    if conn:
        df_clients = get_leads_data(conn)
        if not df_clients.empty and 'id' in df_clients.columns and 'name' in df_clients.columns:
            st.divider()
            st.subheader("שמירת הנתונים לתיק לקוח")
            target_calc_lead = st.selectbox("בחר לקוח:", df_clients['id'].tolist(),
                                            format_func=lambda x: df_clients[df_clients['id'] == x]['name'].values[0],
                                            key="mort_lead")

            if st.button("📄 שמור לתיק והפק PDF", type="secondary", key="btn_mort_save"):
                client_name = df_clients[df_clients['id'] == target_calc_lead]['name'].values[0]
                details = f"חישוב משכנתה: סכום ₪{principal:,.0f} | ריבית {rate}% | {m_years} שנים | החזר: ₪{monthly_payment:,.0f}"

                try:
                    add_interaction(conn, target_calc_lead, "סימולציה", details)
                    pdf_output = generate_branded_calc_pdf({"name": client_name}, "סיכום משכנתה", details)


                    class MockFile:
                        def __init__(self, content, name):
                            self.content, self.name, self.type = content, name, "application/pdf"

                        def getvalue(self): return self.content

                        def read(self): return self.content


                    save_file(conn, target_calc_lead, MockFile(pdf_output.getvalue(), f"Mortgage_{date.today()}.pdf"))
                    st.success(f"נשמר בהצלחה בתיק של {client_name}!")
                except Exception as e:
                    st.error(f"שגיאה בשמירה: {e}")

# --- TAB 4: עמלות ---
with tabs[3]:
    st.header("💰 מחשבון עמלות סוכן")

    ccol1, ccol2, ccol3 = st.columns(3)
    company = ccol1.selectbox("חברת ביטוח", list(LOCAL_COMMISSION_RATES.keys()), key="comm_comp")

    products = list(LOCAL_COMMISSION_RATES.get(company, {"פנסיה": 0}).keys())
    product = ccol2.selectbox("סוג מוצר", products, key="comm_prod")

    prem = ccol3.number_input("פרמיה/הפקדה חודשית (₪)", min_value=0, value=1000, step=100, key="comm_prem")

    # חישוב עמלה עצמאי ללא תלות במנוע הראשי
    rate_val = LOCAL_COMMISSION_RATES.get(company, {}).get(product, 10)
    comm = prem * (rate_val / 100) * 12

    st.metric("🎯 עמלה שנתית צפויה", f"₪{safe_format(comm):,.0f}")

if conn:
    conn.close()