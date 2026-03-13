import streamlit as st
import base64

from engines import init_db, get_leads_data, setup_page_styling

# --- Page Configuration & Styling (RULE 1) ---
st.set_page_config(layout="wide", page_title="פורטל לקוחות")
theme = setup_page_styling()

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("🔗 מחולל לינק ללקוח")
df = get_leads_data(conn)
if not df.empty:
    selected_lead = st.selectbox("בחר לקוח:", df['id'].tolist(), format_func=lambda x: df[df['id']==x]['name'].values[0])
    if selected_lead:
        token = base64.b64encode(str(selected_lead).encode()).decode()
        # Replace with your actual Streamlit Cloud URL
        link = f"https://your-app.streamlit.app/?portal_token={token}" 
        st.code(link)
        st.info("שלח את הלינק הזה ללקוח בוואטסאפ")
else:
    st.warning("אין לקוחות במערכת.")
