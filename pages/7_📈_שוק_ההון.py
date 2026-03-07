import streamlit as st
import plotly.express as px

from engines import get_boi_rates, get_dynamic_stock_data

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="שוק ההון")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="market_dark_mode")
if dark_mode:
    TEXT_COLOR, PLOT_THEME = "#ffffff", "plotly_dark"
else:
    TEXT_COLOR, PLOT_THEME = "#000000", "plotly_white"

st.markdown(f"""
<style>
    .stApp, .main, .stMarkdown, p, h1, h2, h3, h4, h5, h6, span, label {{
        direction: rtl;
        text-align: right;
        font-family: 'Heebo', sans-serif;
        color: {TEXT_COLOR} !important;
    }}
    section[data-testid="stSidebar"] {{
        direction: rtl;
        text-align: right;
    }}
</style>
""", unsafe_allow_html=True)


# --- Main Page ---
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
        delta_color = "normal" if row['שינוי'] >= 0 else "inverse"
        st.metric(label=row['מדד'], value=f"{row['שער']:,.2f}", delta=f"{row['שינוי']:+.2f}%", delta_color=delta_color)

if not market_df.empty:
    st.divider()
    st.subheader("📊 השוואת ביצועים")
    fig = px.bar(market_df, x='מדד', y='שינוי', color='שינוי', color_continuous_scale='RdYlGn', template=PLOT_THEME)
    st.plotly_chart(fig, use_container_width=True)
