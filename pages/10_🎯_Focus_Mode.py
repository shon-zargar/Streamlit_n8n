import streamlit as st
from datetime import datetime, timedelta
import time

from engines import init_db, get_leads_data, add_interaction, AIEngine, generate_whatsapp_link, setup_page_styling

# --- Page Configuration & Styling (RULE 1) ---
st.set_page_config(layout="wide", page_title="Focus Mode")
theme = setup_page_styling()

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("🎯 Focus Mode - משימות ממוקדות")
st.caption("רשימת משימות דחופות ממוקדת ל-5 הדחופים ביותר")
df = get_leads_data(conn)
today_str = datetime.now().strftime('%Y-%m-%d')

urgent_leads = df[(df['callback_date'] <= today_str) & (~df['status'].isin(['נמכר', 'לא רלוונטי']))].copy()

if urgent_leads.empty:
    st.balloons()
    st.success("🎉 כל הכבוד! אין משימות דחופות כרגע.")
else:
    urgent_leads['priority_score'] = urgent_leads.apply(lambda row: AIEngine.calculate_lead_score(row, conn) + (row.get('estimated_commission', 0) / 100), axis=1)
    urgent_leads = urgent_leads.sort_values('priority_score', ascending=False)

    st.progress(max(0, 1 - (len(urgent_leads) / 20)), text=f"נותרו {len(urgent_leads)} משימות דחופות")
    
    for idx, row in urgent_leads.head(5).iterrows():
        days_overdue = (datetime.now().date() - datetime.strptime(row['callback_date'], '%Y-%m-%d').date()).days
        
        # --- Card UI Refactoring (RULE 2) ---
        st.markdown(f"""
        <div style='background-color:{theme.get("card", "#fff")}; 
                    padding:20px; 
                    border-radius:12px; 
                    border:1px solid {theme.get("border", "#ddd")}; 
                    margin-bottom:20px;
                    border-right: 6px solid #FF4B4B;'>
            <h3 style='margin:0; color:{theme.get("text", "#000")};'>🔥 {row['name']}</h3>
            <p style='margin:5px 0; color:gray;'>📞 {row['phone']} | 💰 פוטנציאל: ₪{row['estimated_commission']:,.0f}</p>
            <p style='margin:10px 0 0 0; color:{theme.get("text", "#000")};'><strong>הערות:</strong> {row['notes'] if row['notes'] else 'אין הערות'}</p>
        </div>
        """, unsafe_allow_html=True)

        acol1, acol2, acol3, acol4 = st.columns(4)
        if acol1.button("✅ טופל - למחר", key=f"done_{row['id']}", use_container_width=True):
            conn.execute("UPDATE leads SET status='בטיפול', callback_date=? WHERE id=?", ((datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'), row['id']))
            add_interaction(conn, row['id'], "טיפול", "טופל ב-Focus Mode")
            conn.commit()
            st.rerun()
        # ... (other buttons)
        acol4.link_button("💬 WhatsApp", generate_whatsapp_link(row['phone']), use_container_width=True)
        st.divider()
