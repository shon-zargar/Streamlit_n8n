import streamlit as st
from datetime import datetime, timedelta
import time

from engines import init_db, get_leads_data, add_interaction, AIEngine, generate_whatsapp_link

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Focus Mode")

# --- Global Styling ---
dark_mode = st.sidebar.toggle("🌙 מצב לילה", value=False, key="focus_dark_mode")
if dark_mode:
    TEXT_COLOR = "#ffffff"
else:
    TEXT_COLOR = "#000000"

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


# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("🎯 Focus Mode - משימות ממוקדות")
df = get_leads_data(conn)
today_str = datetime.now().strftime('%Y-%m-%d')

urgent_leads = df[(df['callback_date'] <= today_str) & (~df['status'].isin(['נמכר', 'לא רלוונטי']))].copy()

if urgent_leads.empty:
    st.balloons()
    st.success("🎉 כל הכבוד! אין משימות דחופות כרגע.")
else:
    urgent_leads['priority_score'] = urgent_leads.apply(lambda row: AIEngine.calculate_lead_score(row, conn) + (row['estimated_commission'] / 100), axis=1)
    urgent_leads = urgent_leads.sort_values('priority_score', ascending=False)

    st.progress(max(0, 1 - (len(urgent_leads) / 20)), text=f"נותרו {len(urgent_leads)} משימות דחופות")
    
    for idx, row in urgent_leads.head(5).iterrows():
        st.markdown(f"### {row['name']}")
        acol1, acol2, acol3, acol4 = st.columns(4)
        if acol1.button("✅ טופל - למחר", key=f"done_{row['id']}"):
            conn.execute("UPDATE leads SET status='בטיפול', callback_date=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", ((datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'), row['id']))
            add_interaction(conn, row['id'], "טיפול", "טופל ב-Focus Mode")
            conn.commit()
            st.rerun()
        if acol2.button("❌ לא ענה - עוד יומיים", key=f"noans_{row['id']}"):
            conn.execute("UPDATE leads SET status='לא עונה', callback_date=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", ((datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'), row['id']))
            conn.commit()
            st.rerun()
        if acol3.button("🎉 נסגר!", key=f"closed_{row['id']}"):
            conn.execute("UPDATE leads SET status='נמכר', updated_at=CURRENT_TIMESTAMP WHERE id=?", (row['id'],))
            conn.commit()
            st.rerun()
        acol4.link_button("💬 WhatsApp", generate_whatsapp_link(row['phone']))
        st.divider()
