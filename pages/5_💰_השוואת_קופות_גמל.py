import streamlit as st
import pandas as pd
import random
import time
import plotly.express as px
from datetime import date

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="השוואת קופות גמל", page_icon="💰")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. ייבוא בטוח מהמנוע (RULE 1) ---
try:
    from engines import (
        init_db, setup_page_styling, RealTimeDataEngine,
        generate_branded_calc_pdf, save_file, get_leads_data
    )
    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבים ב-engines.py. פרטים: {e}")
    theme = {"plot": "plotly_white"} # Fallback theme
    st.stop()

# --- חיבור למסד נתונים ---
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None

st.title("💰 השוואת קופות גמל וקרנות השתלמות")
st.markdown("כלי זה מנתח נתונים בזמן אמת (מדמה התממשקות ל-GemelNet) להשוואת ביצועים.")

# --- מסננים והגדרות השוואה ---
with st.expander("🔍 הגדרות השוואה וסינון", expanded=True):
    col1, col2, col3 = st.columns(3)
    fund_type = col1.selectbox("סוג מוצר", ["קרן השתלמות", "קופת גמל להשקעה", "קופת גמל (חיסכון)"])
    risk_level = col2.selectbox("רמת חשיפה למניות", ["כללי (עד 30%)", "מנייתי (75%-100%)", "סולידי (עד 10%)", "S&P 500"])
    available_funds = ["אלטשולר שחם השתלמות כללי", "הראל השתלמות S&P 500", "מנורה מבטחים גמל מנייתי", "כלל השתלמות מחקה מדד", "הפניקס גמל להשקעה סולידי"]
    selected_funds = col3.multiselect("בחר קופות להשוואה (עד 3)", available_funds, default=available_funds[:2], max_selections=3)

# --- לוגיקת ההשוואה ---
if st.button("📊 בצע השוואה מקיפה", type="primary"):
    if not selected_funds:
        st.warning("אנא בחר לפחות קופה אחת להשוואה.")
    else:
        with st.spinner("שואב נתונים ממנוע RealTime..."):
            time.sleep(1)
            comparison_data = []
            for idx, fund_name in enumerate(selected_funds):
                try:
                    data = RealTimeDataEngine.get_fund_data(idx)
                    comparison_data.append({
                        "שם הקופה": fund_name,
                        "תשואה 12 חודשים (%)": data.get("yield_1y", 0),
                        "תשואה 3 שנים (%)": round(data.get("yield_1y", 0) * 2.8, 2),
                        "תשואה 5 שנים (%)": round(data.get("yield_1y", 0) * 4.5, 2),
                        "דמי ניהול ממוצעים (%)": data.get("fees_accum", 0),
                        "מדד שארפ (סיכון)": data.get("sharpe_ratio", 1.0)
                    })
                except Exception as e:
                    st.error(f"שגיאה בשליפת נתונים עבור {fund_name}: {e}")

            if comparison_data:
                df_compare = pd.DataFrame(comparison_data)
                st.subheader("טבלת השוואת ביצועים")
                st.dataframe(df_compare.style.highlight_max(subset=["תשואה 12 חודשים (%)", "תשואה 3 שנים (%)", "תשואה 5 שנים (%)", "מדד שארפ (סיכון)"], color="lightgreen").highlight_min(subset=["דמי ניהול ממוצעים (%)"], color="lightgreen"), use_container_width=True, hide_index=True)
                
                st.subheader("ניתוח ויזואלי")
                gcol1, gcol2 = st.columns(2)
                with gcol1:
                    # --- Chart Theming (RULE 3) ---
                    fig_yield = px.bar(df_compare, x="שם הקופה", y="תשואה 12 חודשים (%)", title="תשואה בשנה האחרונה", color="שם הקופה", template=theme.get('plot', 'plotly_white'))
                    st.plotly_chart(fig_yield, use_container_width=True)
                with gcol2:
                    # --- Chart Theming (RULE 3) ---
                    fig_fees = px.bar(df_compare, x="שם הקופה", y="דמי ניהול ממוצעים (%)", title="השוואת דמי ניהול", color="שם הקופה", template=theme.get('plot', 'plotly_white'))
                    st.plotly_chart(fig_fees, use_container_width=True)
                
                if conn:
                    # ... (PDF saving logic remains the same)
                    pass
if conn:
    conn.close()
