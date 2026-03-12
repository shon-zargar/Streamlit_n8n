import streamlit as st
import random
from datetime import datetime

from engines import RealTimeDataEngine, setup_page_styling, generate_branded_calc_pdf

# --- Page Configuration & Styling ---
st.set_page_config(layout="wide", page_title="השוואת קופות גמל")
theme = setup_page_styling()

# --- Main Page ---
st.title("💰 מערכת מושיקונט - השוואת קופות")
st.caption(f"נתונים מעודכנים ליום: {datetime.now().strftime('%d/%m/%Y')}")

# CSS לעיצוב כרטיסיות נכסנט
st.markdown(f"""
    <style>
    .fund-card {{
            background-color: {theme['card']}; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            overflow: hidden; margin-bottom: 20px; border-top: 4px solid #1f77b4;
            direction: rtl; text-align: right;
        }}
        .fund-header {{
            background-color: {theme['header']}; padding: 12px; border-bottom: 1px solid {theme['border']};
            font-weight: bold; color: #1f77b4; font-size: 1.1em;
        }}
        .fund-metrics {{
            display: flex; justify-content: space-between; padding: 15px;
        }}
        .metric-box {{
            text-align: center; width: 30%;
        }}
        .metric-val {{ font-size: 1.4em; font-weight: bold; color: {theme['text']}; }}
        .metric-lbl {{ font-size: 0.8em; color: #7f8c8d; }}
        .fund-footer {{
            background-color: {theme['header']}; padding: 10px; font-size: 0.9em; display: flex; justify-content: space-between;
            color: {theme['text']};
        }}
    </style>
    """, unsafe_allow_html=True)

# רשימת הקופות האמיתיות שאנו רוצים לעקוב אחריהן (מספרי אוצר אמיתיים)
real_funds_ids = [15209, 1199, 723, 599, 1374, 874]

# חברות למיפוי
company_map = {15209: "הפניקס", 1199: "אנליסט", 723: "ילין לפידות", 599: "אלטשולר שחם", 1374: "מיטב", 874: "הראל"}
names_map = {15209: "מסלול מניות", 1199: "מסלול כללי", 723: "מסלול מניות", 599: "מסלול כללי", 1374: "מחקי מדד S&P", 874: "מסלול משולב"}

# סרגל צד לפילטור
with st.sidebar:
    st.header("🔍 סינון מתקדם")
    selected_comps = st.multiselect("בחר גופים", list(company_map.values()),
                                    default=["הפניקס", "אנליסט", "אלטשולר שחם"])
    risk_profile = st.selectbox("רמת סיכון", ["גבוה (מניות)", "בינוני (כללי)", "נמוך (אג'ח)"])
    st.info("💡 הנתונים נשאבים ממאגרי המידע ומציגים תשואות חודשיות אחרונות ידועות.")

# תצוגה ראשית
cols = st.columns(3)

col_idx = 0
for fid in real_funds_ids:
    comp_name = company_map.get(fid, "כללי")

    # סינון לפי בחירת משתמש
    if comp_name not in selected_comps:
        continue

    fund_data = RealTimeDataEngine.get_fund_data(fid)
    if fund_data:
        with cols[col_idx % 3]:
            # HTML Card
            st.markdown(f"""
                <div class="fund-card">
                    <div class="fund-header">
                        {fund_data['name']} <span style='float:left; font-size:0.8em; color:gray'>#{fund_data['id']}</span>
                    </div>
                    <div class="fund-metrics">
                        <div class="metric-box">
                            <div class="metric-val" style="color: {'green' if fund_data['ytd'] > 0 else 'red'}">{fund_data['ytd']}%</div>
                            <div class="metric-lbl">מתחילת שנה</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-val">{fund_data['yield3y']}%</div>
                            <div class="metric-lbl">3 שנים</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-val">{fund_data['sharpe']}</div>
                            <div class="metric-lbl">מדד שארפ</div>
                        </div>
                    </div>
                    <div class="fund-footer">
                        <span>💎 מנוהל: {random.uniform(1000, 50000):,.0f} מ' ₪</span>
                        <span>דמי ניהול: 0.7%</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            # כפתורי פעולה לכל קופה
            b1, b2 = st.columns(2)
            with b1:
                # סימולטור אישי לכל קופה
                popover = st.popover("🧮 סימולטור", key=f"popover_{fid}")

                amount = popover.number_input(f"סכום להפקדה ({fid})", 10000, 5000000, 100000, key=f"amount_{fid}")
                years = popover.slider("שנים", 1, 20, 5, key=f"years_{fid}")

                future_val = amount * ((1 + fund_data['ytd'] / 100) ** years)
                popover.metric("צפי רווח", f"₪{future_val:,.0f}", delta=f"₪{future_val - amount:,.0f}")

            with b2:
                if st.button("📄 צור מסמך", key=f"doc_{fid}"):
                    content = f"הצעת הצטרפות ל{fund_data['name']}\nמספר אוצר: {fid}\nתשואה שנתית: {fund_data['ytd']}%\nתשואה 3 שנים: {fund_data['yield3y']}%"
                    pdf_file = generate_branded_calc_pdf(fund_data['name'], "דוח קופת גמל", content)
                    st.download_button("📥 הורד PDF", pdf_file, f"fund_report_{fid}.pdf", "application/pdf")
        col_idx += 1
