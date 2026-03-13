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

# --- 3. ייבוא בטוח ---
try:
    from engines import (
        init_db, get_leads_data, add_interaction, save_file,
        FinanceEngine, FinConfig, generate_branded_calc_pdf,
        setup_page_styling, safe_format
    )

    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבים ב-engines.py. {e}")
    st.stop()

# --- חיבור למסד נתונים ---
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None

st.title("🧮 מחשבוני ביטוח ופיננסים")
st.caption("כלי עזר לחישוב עמלות, השפעת דמי ניהול וביטוח חיים.")

tabs = st.tabs(["📉 הפסד דמי ניהול", "💡 ביטוח חיים", "🏠 משכנתה", "💰 עמלות"])

# --- TAB 1: דמי ניהול ---
with tabs[0]:
    st.header("📉 השפעת דמי ניהול על הצבירה")
    st.markdown("מחשבון זה מדגים ללקוח כמה כסף הוא מאבד בגלל דמי ניהול גבוהים.")

    col1, col2, col3 = st.columns(3)
    balance = col1.number_input("צבירה נוכחית (₪)", min_value=0, value=100000, step=10000)
    monthly = col2.number_input("הפקדה חודשית (₪)", min_value=0, value=2000, step=100)
    years = col3.slider("תקופת חישוב (בשנים)", min_value=1, max_value=40, value=20)

    col4, col5, col6 = st.columns(3)
    yield_rate = col4.number_input("תשואה שנתית משוערת (%)", min_value=0.0, max_value=15.0, value=5.0, step=0.5) / 100
    fee_current = col5.number_input("דמי ניהול נוכחיים מצבירה (%)", min_value=0.0, max_value=3.0, value=0.8,
                                    step=0.05) / 100
    fee_target = col6.number_input("דמי ניהול יעד מצבירה (%)", min_value=0.0, max_value=3.0, value=0.4, step=0.05) / 100

    if st.button("חשב השפעה", type="primary"):
        # חישוב בטוח תוך שימוש ב-try/except למקרה של בעיות במנוע
        try:
            # הערה: project_fee_impact במנוע לא תומך כרגע ב-yield_rate שונה, אז נעביר 0.05 (5%) כפי שהוגדר שם כברירת מחדל או שנעקוף
            # לשם אבטחה, נשתמש בחישוב מקומי פשוט שמקבל את כל הפרמטרים
            res = FinanceEngine.project_fee_impact(balance, monthly, years, yield_rate, fee_current, fee_target)
        except (AttributeError, TypeError):
            # Fallback לחישוב מקומי
            b_curr, b_targ = balance, balance
            for _ in range(int(years * 12)):
                b_curr = (b_curr + monthly) * (1 + (yield_rate - fee_current) / 12)
                b_targ = (b_targ + monthly) * (1 + (yield_rate - fee_target) / 12)
            diff = b_targ - b_curr
            res = {
                "projection_1": b_targ,  # האופטימלי (fee2) ב-engines נשמר ב-projection_2, כאן הפכתי
                "projection_2": b_curr,
                "savings": diff,
                "lost_wealth": abs(diff)
            }
            # התאמה לפלט של ה-Engine המקורי
            res = {
                "projection_1": b_targ,
                "projection_2": b_curr,
                "lost_wealth": abs(diff)
            }

        st.divider()
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("צבירה בתנאים נוכחיים", f"₪{safe_format(res.get('projection_2', 0)):,.0f}")
        res_col2.metric("צבירה בתנאי יעד", f"₪{safe_format(res.get('projection_1', 0)):,.0f}")
        res_col3.metric("💸 הפסד צפוי", f"₪{safe_format(res.get('lost_wealth', 0)):,.0f}",
                        delta=f"-₪{safe_format(res.get('lost_wealth', 0)):,.0f}", delta_color="inverse")

# --- TAB 2: ביטוח חיים ---
with tabs[1]:
    st.header("💡 מחשבון סכום ביטוח חיים מומלץ")

    licol1, licol2, licol3 = st.columns(3)
    age = licol1.number_input("גיל המבוטח", min_value=18, max_value=80, value=35)
    income = licol2.number_input("הכנסה חודשית (₪)", min_value=0, value=15000, step=1000)
    spouse_income = licol3.number_input("הכנסת בן/בת זוג (₪)", min_value=0, value=10000, step=1000)

    licol4, licol5 = st.columns(2)
    children = licol4.number_input("מספר ילדים סמוכים לשולחן", min_value=0, max_value=10, value=2)
    mortgage = licol5.number_input("יתרת משכנתה והלוואות (₪)", min_value=0, value=800000, step=50000)

    if st.button("חשב כיסוי נדרש"):
        # חישוב אצבע סטנדרטי (כ-70% מההכנסה עד גיל 65 + חובות)
        years_to_pension = max(5, 65 - age)
        income_replacement = income * 12 * years_to_pension * 0.7
        child_support = children * 150000  # הוצאה משוערת לילד

        total_needed = income_replacement + mortgage + child_support

        st.success(f"הסכום המומלץ לביטוח חיים הוא כ- **₪{safe_format(total_needed):,.0f}**")
        st.caption("* חישוב זה הנו הערכה גסה ואינו מחליף ייעוץ פנסיוני מקצועי.")

# --- TAB 3: משכנתה ---
with tabs[2]:
    st.header("🏠 מחשבון החזר משכנתה משוער")

    mcol1, mcol2, mcol3 = st.columns(3)
    principal = mcol1.number_input("סכום ההלוואה (₪)", min_value=100000, value=1000000, step=50000)
    rate = mcol2.number_input("ריבית שנתית ממוצעת (%)", min_value=0.1, max_value=15.0, value=3.5, step=0.1)
    m_years = mcol3.number_input("תקופת הלוואה (בשנים)", min_value=5, max_value=30, value=25)

    # נוסחת שפיצר קלאסית
    r_monthly = (rate / 100) / 12
    n_months = int(m_years * 12)

    if r_monthly > 0:
        monthly_payment = principal * (r_monthly * (1 + r_monthly) ** n_months) / ((1 + r_monthly) ** n_months - 1)
    else:
        monthly_payment = principal / n_months

    st.metric("💳 החזר חודשי צפוי", f"₪{safe_format(monthly_payment):,.0f}")

    # שמירת חישוב לליד
    if conn:
        df_clients = get_leads_data(conn)
        if not df_clients.empty and 'id' in df_clients.columns and 'name' in df_clients.columns:
            st.divider()
            st.subheader("שמירת הנתונים לתיק לקוח")
            target_calc_lead = st.selectbox("בחר לקוח:", df_clients['id'].tolist(),
                                            format_func=lambda x: df_clients[df_clients['id'] == x]['name'].values[0])

            if st.button("📄 שמור לתיק והפק PDF", type="secondary"):
                client_name = df_clients[df_clients['id'] == target_calc_lead]['name'].values[0]
                details = f"חישוב משכנתה: סכום ₪{principal:,.0f} | ריבית {rate}% | {m_years} שנים | החזר: ₪{monthly_payment:,.0f}"

                try:
                    # הוספת אינטראקציה
                    add_interaction(conn, target_calc_lead, "סימולציה", details)

                    # יצירת מסמך דמה ושמירתו
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
    company = ccol1.selectbox("חברת ביטוח", list(getattr(FinConfig, 'COMMISSION_RATES', {"כללי": {}}).keys()))

    # שליפת מוצרים של החברה (או ברירת מחדל אם ריק)
    products = list(getattr(FinConfig, 'COMMISSION_RATES', {}).get(company, {"פנסיה": 0}).keys())
    product = ccol2.selectbox("סוג מוצר", products)

    prem = ccol3.number_input("פרמיה/הפקדה חודשית (₪)", min_value=0, value=1000, step=100)

    try:
        comm = FinanceEngine.calculate_smart_commission(company, product, prem)
    except AttributeError:
        # חישוב גיבוי
        comm = prem * 0.1 * 12  # 10% עמלה שנתית

    st.metric("🎯 עמלה שנתית צפויה", f"₪{safe_format(comm):,.0f}")

if conn:
    conn.close()