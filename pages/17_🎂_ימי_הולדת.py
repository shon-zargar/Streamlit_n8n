import streamlit as st
import pandas as pd
from datetime import datetime
import time

# ייבוא פונקציות המנוע המעודכנות
from engines import (
    init_db, get_leads_data, generate_ai_blessing,
    generate_whatsapp_link, add_interaction, setup_page_styling
)

# --- Page Configuration & Styling ---
st.set_page_config(layout="wide", page_title="ימי הולדת")
# שימוש בסטיילינג הגלובלי במקום CSS ידני
theme = setup_page_styling()

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("🎂 מרכז ימי הולדת ואוטומציה")
st.markdown("כאן תוכל לראות מי חוגג היום ולשלוח לו ברכה אישית מה-AI בלחיצת כפתור.")

df = get_leads_data(conn)
today = datetime.now()

if not df.empty:
    # טיפול בתאריכי לידה
    df['birth_dt'] = pd.to_datetime(df['birth_date'], errors='coerce')
    birthdays_today = df[(df['birth_dt'].dt.month == today.month) & (df['birth_dt'].dt.day == today.day)]

    if birthdays_today.empty:
        st.info("🎈 אין ימי הולדת היום! יום עבודה רגיל בחולון.")
    else:
        # חגיגה ויזואלית!
        st.balloons()
        st.success(f"🎉 מזל טוב! יש {len(birthdays_today)} לקוחות שחוגגים היום.")

        # יצירת כרטיסי עבודה לכל חוגג
        for idx, row in birthdays_today.iterrows():
            with st.expander(f"🎁 {row['name']} - {row['phone']}", expanded=True):
                col1, col2 = st.columns([2, 1])

                with col1:
                    default_msg = generate_ai_blessing(row['name'])
                    final_blessing = st.text_area("✏️ ערוך/אשר את הברכה:", value=default_msg, key=f"text_{row['id']}",
                                                  height=100)

                with col2:
                    st.write("🚀 **פעולות מהירות:**")
                    wa_link = generate_whatsapp_link(row['phone'], final_blessing)
                    st.link_button("💬 שלח WhatsApp", wa_link, use_container_width=True)

                    if st.button("📝 סמן כנשלח ושמור", key=f"save_note_{row['id']}", use_container_width=True):
                        if add_interaction(conn, row['id'], "יום הולדת", f"נשלחה ברכה: {final_blessing}"):
                            st.toast(f"האינטראקציה עם {row['name']} נשמרה!", icon='✅')
                            time.sleep(1)
                            st.rerun()
else:
    st.warning("המערכת ריקה. תתחיל להכניס לידים כדי שנוכל לחגוג!")

conn.close()