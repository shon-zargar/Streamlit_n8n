import streamlit as st
import plotly.express as px

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="שוק ההון", page_icon="📈")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. ייבוא בטוח מהמנוע (RULE 1) ---
try:
    from engines import get_boi_rates, get_dynamic_stock_data, setup_page_styling
    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: {e}")
    theme = {'plot': 'plotly_white'} # Fallback
    st.stop()

# --- 4. ממשק המשתמש ---
st.title("📈 שוק ההון - נתונים בזמן אמת")

POPULAR_TICKERS = {
    "S&P 500": "^GSPC", "נאסדק": "^IXIC", "תל אביב 35": "TA35.TA",
    "ביטקוין": "BTC-USD", "אפל": "AAPL", "טסלה": "TSLA", "הפניקס": "PHOE1.TA"
}

selected_names = st.multiselect("📋 בחר מניות להצגה:", list(POPULAR_TICKERS.keys()), default=["S&P 500", "טסלה"])
custom_ticker = st.text_input("🔍 חפש סימול מניה חופשי (למשל: GOOG):")

tickers_to_fetch = {name: POPULAR_TICKERS[name] for name in selected_names}
if custom_ticker:
    tickers_to_fetch[f"חיפוש: {custom_ticker.upper()}"] = custom_ticker.upper()

with st.spinner("שואב נתוני אמת..."):
    boi_data = get_boi_rates()
    market_df = get_dynamic_stock_data(tickers_to_fetch)

all_metrics = boi_data + (market_df.to_dict('records') if not market_df.empty else [])

cols = st.columns(4)
for i, row in enumerate(all_metrics):
    with cols[i % 4]:
        delta_color = "normal" if row.get('שינוי', 0) >= 0 else "inverse"
        st.metric(
            label=row.get('מדד', 'N/A'), 
            value=f"{row.get('שער', 0):,.2f}", 
            delta=f"{row.get('שינוי', 0):+.2f}%", 
            delta_color=delta_color
        )

if not market_df.empty:
    st.divider()
    st.subheader("📊 השוואת ביצועים")
    # --- Chart Theming (RULE 3) ---
    fig = px.bar(
        market_df, 
        x='מדד', 
        y='שינוי', 
        color='שינוי', 
        color_continuous_scale='RdYlGn', 
        template=theme.get('plot', 'plotly_white')
    )
    st.plotly_chart(fig, use_container_width=True)
