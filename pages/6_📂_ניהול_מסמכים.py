import streamlit as st
import pandas as pd
import time
import os

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="ניהול מסמכים", page_icon="📂")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. ייבוא בטוח מהמנוע (RULE 1) ---
try:
    from engines import (
        init_db, get_leads_data, get_files,
        save_file, delete_file, setup_page_styling
    )
    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבים ב-engines.py. פרטים: {e}")
    theme = {"card": "#f0f2f6", "border": "#ddd"} # Fallback
    st.stop()

# --- חיבור למסד נתונים ---
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None
    st.stop()

st.title("📂 ניהול מסמכים מרכזי")
st.markdown("ניהול קבצים מצורפים, מסמכי זיהוי, והצעות מחיר עבור לקוחות.")

# --- שליפת נתוני לקוחות ---
try:
    df_leads = get_leads_data(conn)
except Exception:
    df_leads = pd.DataFrame()

if df_leads.empty or 'id' not in df_leads.columns or 'name' not in df_leads.columns:
    st.warning("אין לקוחות במערכת עדיין. לא ניתן לנהל מסמכים ללא לקוחות.")
    st.stop()

# --- בחירת לקוח ---
with st.container(border=True):
    col1, col2 = st.columns([3, 1])
    with col1:
        lead_dict = dict(zip(df_leads['id'], df_leads['name']))
        selected_lead_id = st.selectbox("בחר לקוח:", list(lead_dict.keys()),
                                        format_func=lambda x: f"{lead_dict.get(x, 'לא ידוע')} (ID: {x})")
    with col2:
        st.write("")
        st.write("")
        if st.button("🔄 רענן מסמכים"):
            st.rerun()

st.divider()

col_files, col_upload = st.columns([2, 1])

# --- תצוגת קבצים קיימים ---
with col_files:
    st.subheader(f"📄 המסמכים של {lead_dict.get(selected_lead_id, '')}")

    try:
        files_df = get_files(conn, selected_lead_id)
    except Exception as e:
        st.error(f"שגיאה בשליפת קבצים: {e}")
        files_df = pd.DataFrame()

    if files_df.empty:
        st.info("לא נמצאו מסמכים משויכים ללקוח זה.")
    else:
        for index, file_row in files_df.iterrows():
            # --- Card UI Refactoring (RULE 2) ---
            with st.container(border=True):
                f_col1, f_col2, f_col3 = st.columns([3, 1, 1])
                
                file_ext = str(file_row.get('filename', '')).split('.')[-1].lower()
                icon = "📄"
                if file_ext == 'pdf': icon = "📕"
                elif file_ext in ['png', 'jpg', 'jpeg']: icon = "🖼️"

                f_col1.markdown(f"**{icon} {file_row.get('filename', 'קובץ ללא שם')}**")
                if 'upload_date' in file_row:
                    f_col1.caption(f"הועלה ב: {pd.to_datetime(file_row['upload_date']).strftime('%d/%m/%Y %H:%M')}")

                with f_col2:
                    blob_query = conn.execute("SELECT file_data FROM files WHERE id=?", (file_row['id'],)).fetchone()
                    if blob_query and blob_query[0]:
                        st.download_button("⬇️ הורד", blob_query[0], file_row['filename'], key=f"dl_{file_row['id']}", use_container_width=True)
                    else:
                        st.button("❌ לא זמין", disabled=True, key=f"dl_err_{file_row['id']}", use_container_width=True)

                with f_col3:
                    if st.button("🗑️ מחיקה", key=f"del_{file_row['id']}", type="secondary", use_container_width=True):
                        if delete_file(conn, file_row['id']):
                            st.toast(f"הקובץ {file_row['filename']} נמחק!")
                            st.rerun()
                        else:
                            st.error("שגיאה במחיקה.")

# --- העלאת קובץ חדש ---
with col_upload:
    st.subheader("📤 העלאת מסמך חדש")
    with st.container(border=True):
        uploaded_file = st.file_uploader("בחר קובץ", type=['pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'xls'])
        if uploaded_file:
            st.success(f"נבחר: {uploaded_file.name}")
            if st.button("💾 שמור בתיק לקוח", type="primary", use_container_width=True):
                with st.spinner("שומר..."):
                    if save_file(conn, selected_lead_id, uploaded_file):
                        st.success("הקובץ נשמר בהצלחה!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("השמירה נכשלה.")

if conn:
    conn.close()
