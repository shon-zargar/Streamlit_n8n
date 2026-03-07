import streamlit as st
import random
from datetime import datetime

from engines import RealTimeDataEngine, setup_page_styling

# --- Page Configuration & Styling ---
st.set_page_config(layout="wide", page_title="השוואת קופות גמל")
theme = setup_page_styling()

# --- Main Page ---
st.title("💰 מערכת מושיקונט - השוואת קופות")
st.caption(f"נתונים מעודכנים ליום: {datetime.now().strftime('%d/%m/%Y')}")

# --- Fund Data ---
real_funds_ids = [15209, 1199, 723, 599, 1374, 874]
company_map = {15209: "הפניקס", 1199: "אנליסט", 723: "ילין לפידות", 599: "אלטשולר שחם", 1374: "מיטב", 874: "הראל"}
names_map = {15209: "מסלול מניות", 1199: "מסלול כללי", 723: "מסלול מניות", 599: "מסלול כללי", 1374: "מחקי מדד S&P", 874: "מסלול משולב"}

# --- Sidebar Filters ---
selected_comps = st.sidebar.multiselect("בחר גופים", list(company_map.values()), default=["הפניקס", "אנליסט", "אלטשולר שחם"])

# --- Display Funds ---
cols = st.columns(3)
col_idx = 0
for fid in real_funds_ids:
    comp_name = company_map.get(fid, "כללי")
    if comp_name not in selected_comps:
        continue

    fund_data = RealTimeDataEngine.get_fund_data(fid)
    if fund_data:
        with cols[col_idx % 3]:
            st.markdown(f"""
                <div style='background-color:{theme['card']}; border:1px solid {theme['border']}; border-radius: 8px; padding: 15px; margin-bottom: 20px;'>
                    <h5 style='color:{theme['text']};'>{fund_data['name']}</h5>
                    <div style='display: flex; justify-content: space-around; text-align: center;'>
                        <div><p style='font-size: 1.2em; color: {'green' if fund_data['ytd'] > 0 else 'red'};'>{fund_data['ytd']:.2f}%</p><small>מתחילת שנה</small></div>
                        <div><p style='font-size: 1.2em;'>{fund_data['yield3y']:.2f}%</p><small>3 שנים</small></div>
                        <div><p style='font-size: 1.2em;'>{fund_data['sharpe']:.2f}</p><small>מדד שארפ</small></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            popover = st.popover("🧮 סימולטור")
            amount = popover.number_input(f"סכום להפקדה ({fid})", 10000, 5000000, 100000, key=f"amount_{fid}")
            years = popover.slider("שנים", 1, 20, 5, key=f"years_{fid}")
            future_val = amount * ((1 + fund_data['ytd'] / 100) ** years)
            popover.metric("צפי רווח", f"₪{future_val:,.0f}", delta=f"₪{future_val - amount:,.0f}")
        col_idx += 1
