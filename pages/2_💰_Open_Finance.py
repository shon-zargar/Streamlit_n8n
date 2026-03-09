import streamlit as st
import pandas as pd

# ייבוא מהמנוע המתוקן שלנו
from engines import (
    init_db, DataIngestionLayer, FinanceEngine, FinConfig,
    generate_branded_calc_pdf, setup_page_styling
)

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Open Finance 2026")
theme = setup_page_styling()

# --- Database ---
conn = init_db()

# --- Main Page ---
st.title("💰 Open Finance Israel")
st.markdown("מרכז מחשבונים פיננסיים וסימולציות ללקוחות.")

# יצירת הטאבים
tabs = st.tabs(["🚀 טעינת HAR", "🧠 מס 2025", "📉 דמי ניהול", "👴 תיקון 190", "💡 ביטוח חיים", "🏠 משכנתה"])

# ----------------------------------------
# TAB 1: טעינת HAR
# ----------------------------------------
with tabs[0]:
    st.subheader("טעינת נתוני מסלקה פנסיונית (HAR)")
    uploaded_har = st.file_uploader("העלה קובץ מסלקה (JSON/HAR)", type=['json', 'har'])
    if uploaded_har:
        if st.button("🔄 נתח קובץ"):
            with st.spinner("מנתח נתונים..."):
                result = DataIngestionLayer.process_har_file(uploaded_har)
                if "error" in result:
                    st.error(f"שגיאה בקריאת הקובץ: {result['error']}")
                else:
                    st.success(f"הקובץ נותח בהצלחה! זוהו {result.get('count', 0)} פוליסות.")

# ----------------------------------------
# TAB 2: מס 2025/2026
# ----------------------------------------
with tabs[1]:
    st.subheader("סימולטור מדרגות מס")
    income = st.number_input("הכנסה חודשית ברוטו (₪):", min_value=0, value=15000, step=1000)
    st.info("כאן תיכנס הלוגיקה המלאה של מדרגות המס ונקודות הזיכוי. כרגע מחובר כ-Placeholder להדגמת ה-UI.")
    if st.button("🧮 חשב מס משוער"):
        estimated_tax = income * 0.15  # חישוב דמה
        st.metric(label="מס משוער", value=f"₪{estimated_tax:,.0f}")

# ----------------------------------------
# TAB 3: דמי ניהול
# ----------------------------------------
with tabs[2]:
    st.subheader("מחשבון חיסכון בדמי ניהול")
    col1, col2, col3 = st.columns(3)
    balance = col1.number_input("צבירה נוכחית (₪):", min_value=0, value=500000, step=50000)
    current_fee = col2.number_input("דמי ניהול מצבירה קיימים (%):", min_value=0.0, value=1.05, step=0.05)
    offered_fee = col3.number_input("דמי ניהול מוצעים (%):", min_value=0.0, value=0.5, step=0.05)

    if st.button("📉 הצג פוטנציאל חיסכון"):
        savings = FinanceEngine.calc_management_fees(balance, current_fee, offered_fee)
        scol1, scol2 = st.columns(2)
        scol1.metric("חיסכון שנתי", f"₪{savings['yearly_save']:,.0f}")
        scol2.metric("חיסכון מצטבר ל-10 שנים", f"₪{savings['10_year_save']:,.0f}")

# ----------------------------------------
# TAB 4: תיקון 190
# ----------------------------------------
with tabs[3]:
    st.subheader("בדיקת זכאות וכדאיות - תיקון 190")
    col_age, col_dep = st.columns(2)
    age = col_age.number_input("גיל הלקוח:", min_value=20, max_value=120, value=65)
    deposit = col_dep.number_input("סכום הפקדה מיועד (₪):", min_value=0, value=300000, step=10000)

    if st.button("🔍 בדוק זכאות"):
        result = FinanceEngine.calc_amendment_190(deposit, age)
        if result['eligible']:
            st.success("✅ הלקוח עומד בתנאי הגיל לתיקון 190!")
            st.metric("הטבת מס רווחי הון משוערת", f"₪{result['benefit']:,.0f}")

            # כפתור הפקת PDF
            if st.button("📄 הפק דוח ללקוח"):
                pdf_file = generate_branded_calc_pdf("לקוח פוטנציאלי", result)
                st.download_button("📥 הורד PDF", pdf_file, "190_report.pdf", "application/pdf")
        else:
            st.error(f"❌ הלקוח מתחת לגיל {FinConfig.AMENDMENT_190_AGE} ולא זכאי כרגע להטבות תיקון 190 בסיום.")

# ----------------------------------------
# TAB 5: ביטוח חיים
# ----------------------------------------
with tabs[4]:
    st.subheader("מחשבון ריסק - ביטוח חיים")
    st.info("כאן נכנס מחשבון השוואת פרמיות ריסק (לפי גיל, עישון ומין).")

# ----------------------------------------
# TAB 6: משכנתה
# ----------------------------------------
with tabs[5]:
    st.subheader("מחשבון משכנתה וביטוח מבנה")
    mortgage_amount = st.number_input("סכום משכנתה:", min_value=0, value=1000000)
    st.info("כאן יוצג לוח סילוקין ועלויות ביטוח חיים/מבנה למשכנתה.")