import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, datetime

from engines import (
    init_db, get_leads_data, add_interaction, save_file,
    DataIngestionLayer, FinanceEngine, FinConfig, generate_branded_calc_pdf,
    setup_page_styling
)

# --- Page Configuration & Styling ---
st.set_page_config(layout="wide", page_title="Open Finance")
theme = setup_page_styling()

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("💰 Open Finance Israel 2025")
st.caption("מנוע פיננסי מתקדם: הר הביטוח, מיסוי 2025, דמי ניהול ותיקון 190")

tabs = st.tabs(["🚀 טעינת HAR", "🧠 מס 2025", "📉 דמי ניהול", "👴 תיקון 190", "💡 ביטוח חיים", "🏠 משכנתה"])

# Tab 1: HAR
with tabs[0]:
    st.header("📂 ניתוח תיק מהר הביטוח")
    st.info("העלה קובץ HAR או Excel מהר הביטוח לניתוח מקיף")

    uploaded = st.file_uploader("גרור קובץ", type=['har', 'json', 'xlsx'])
    if uploaded:
        with st.spinner('מעבד...'):
            if uploaded.name.endswith('.xlsx'):
                result = DataIngestionLayer.parse_excel_har_alternative(uploaded)
            else:
                result = DataIngestionLayer.parse_har_file(uploaded)

            if isinstance(result, pd.DataFrame) and not result.empty:
                st.success(f"✅ זוהו {len(result)} רשומות!")
                st.session_state['holdings'] = result
                st.dataframe(result, use_container_width=True)

                type_col = 'PolicyType' if 'PolicyType' in result.columns else 'type'
                if type_col in result.columns:
                    type_counts = result[type_col].value_counts()
                    fig = px.pie(values=type_counts.values, names=type_counts.index, title="התפלגות סוגי פוליסות", template=theme['plot'])
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(str(result))

# Tab 2: Tax
with tabs[1]:
    st.header("💼 מחשבון שכר נטו 2025")
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        gross = st.number_input("שכר ברוטו חודשי (₪)", 5000, 100000, 20000, 500)
    with tcol2:
        points = st.number_input("נקודות זיכוי", 0.0, 10.0, 2.25, 0.25)

    net = FinanceEngine.calculate_net_salary_2025(gross, points)
    st.divider()
    rcol1, rcol2, rcol3 = st.columns(3)
    rcol1.metric("💵 שכר ברוטו", f"₪{gross:,.0f}")
    rcol2.metric("✅ שכר נטו", f"₪{net:,.2f}")
    rcol3.metric("📊 מס אפקטיבי", f"{100 - (net / gross * 100):.1f}%")

# Tab 3: Fees
with tabs[2]:
    st.header("📉 אובדן עושר מדמי ניהול")
    fcol1, fcol2, fcol3 = st.columns(3)
    curr_balance = fcol1.number_input("צבירה נוכחית (₪)", 0, 10000000, 100000, 10000)
    monthly_dep = fcol2.number_input("הפקדה חודשית (₪)", 0, 50000, 2000, 100)
    years = fcol3.slider("שנים לתחזית", 5, 40, 20)
    fcol4, fcol5 = st.columns(2)
    fee_accum = fcol4.number_input("דמי ניהול מצבירה (%)", 0.0, 3.0, 0.7, 0.1) / 100
    fee_deposit = fcol5.number_input("דמי ניהול מהפקדה (%)", 0.0, 6.0, 2.0, 0.1) / 100

    if st.button("🔮 הצג תחזית", type="primary"):
        projection = FinanceEngine.project_fee_impact(curr_balance, monthly_dep, years, 0.05, fee_deposit, fee_accum)
        
        chart_data = pd.DataFrame({
            'תרחיש': ['דמי ניהול נוכחיים', 'דמי ניהול אופטימליים'],
            'צבירה': [projection['current_projected'], projection['optimal_projected']]
        })
        fig = px.bar(chart_data, x='תרחיש', y='צבירה', title=f"השוואת צבירה ב-{years} שנים", color='תרחיש', template=theme['plot'])
        st.plotly_chart(fig, use_container_width=True)

        res1, res2, res3 = st.columns(3)
        res1.metric("צבירה נוכחית", f"₪{projection['current_projected']:,.0f}")
        res2.metric("צבירה אופטימלית", f"₪{projection['optimal_projected']:,.0f}")
        res3.metric("💸 הפסד צפוי", f"₪{projection['lost_wealth']:,.0f}", delta=f"-{projection['lost_wealth']:,.0f}", delta_color="inverse")


# Tab 4: Tikun 190
with tabs[3]:
    st.header("👴 בדיקת זכאות לתיקון 190")
    t190col1, t190col2 = st.columns(2)
    age_190 = t190col1.number_input("גיל הלקוח", 50, 90, 67, 1)
    allowance_190 = t190col2.number_input("קצבה חודשית (ברוטו) (₪)", 0, 30000, 5000, 100)
    is_eligible = age_190 >= 60 and allowance_190 >= FinConfig.TIKUN_190_MIN_ALLOWANCE
    if is_eligible:
        st.success("✅ הלקוח זכאי לתיקון 190!")
    else:
        st.warning("❌ הלקוח אינו עומד בתנאי הסף")

# Tab 5: Life Insurance
with tabs[4]:
    st.header("💡 מחשבון ביטוח חיים")
    licol1, licol2 = st.columns(2)
    li_age = licol1.number_input("גיל", 20, 70, 35)
    li_income = licol1.number_input("הכנסה חודשית (₪)", 5000, 100000, 15000, 1000)
    li_mortgage = licol2.number_input("יתרת משכנתה (₪)", 0, 5000000, 800000, 50000)
    li_children = licol2.number_input("מספר ילדים", 0, 10, 2)
    if st.button("חשב כיסוי מומלץ", type="primary"):
        needed = FinanceEngine.calculate_life_insurance_needed(li_age, li_income, li_mortgage, li_children)
        st.metric("🛡️ כיסוי מומלץ", f"₪{needed:,.0f}")

# Tab 6: Mortgage
with tabs[5]:
    st.header("🏠 מחשבון משכנתה")
    mcol1, mcol2, mcol3 = st.columns(3)
    principal = mcol1.number_input("סכום הלוואה (₪)", 100000, 5000000, 1000000, 50000)
    rate = mcol2.number_input("ריבית שנתית (%)", 1.0, 10.0, 3.5, 0.1)
    m_years = mcol3.number_input("תקופה (שנים)", 5, 30, 25, 1)
    monthly_payment = FinanceEngine.calculate_mortgage_payment(principal, rate, m_years)
    st.metric("💳 החזר חודשי", f"₪{monthly_payment:,.0f}")
    
    df_clients = get_leads_data(conn)
    if not df_clients.empty:
        target_calc_lead = st.selectbox("בחר לקוח לשמירת החישוב:", df_clients['id'].tolist(), format_func=lambda x: df_clients[df_clients['id'] == x]['name'].values[0], key="calc_save_lead_select")
        if st.button("📄 שמור כהערה וכקובץ PDF", type="primary"):
            calc_details = f"סימולציית משכנתה - {datetime.now().strftime('%d/%m/%Y')}\nסכום: ₪{principal:,.0f}\nריבית: {rate}%\nהחזר: ₪{monthly_payment:,.0f}"
            add_interaction(conn, target_calc_lead, "סימולציה", calc_details)
            client_name = df_clients[df_clients['id'] == target_calc_lead]['name'].values[0]
            pdf_output = generate_branded_calc_pdf(client_name, "סיכום סימולציה", calc_details)
            class MockFile:
                def __init__(self, content, name):
                    self.content, self.name, self.type = content, name, "application/pdf"
                def getvalue(self): return self.content
            save_file(conn, target_calc_lead, MockFile(pdf_output.getvalue(), f"Calc_{date.today()}.pdf"))
            st.success(f"✅ נשמר בתיק של {client_name}!")
    else:
        st.warning("אין לקוחות במערכת.")
