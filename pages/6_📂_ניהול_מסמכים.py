import time

import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="ניהול מסמכים", page_icon="📂")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. ייבוא בטוח מהמנוע ---
try:
    from engines import (
        init_db, get_leads_data, get_files,
        save_file, delete_file, setup_page_styling
    )

    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבים ב-engines.py. פרטים: {e}")
    st.stop()

# --- חיבור למסד נתונים ---
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None

st.title("📂 ניהול מסמכים מרכזי")
st.markdown("ניהול קבצים מצורפים, מסמכי זיהוי, והצעות מחיר עבור לקוחות.")

if not conn:
    st.stop()

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
        # יצירת מילון לשליפה מהירה של שמות
        lead_dict = dict(zip(df_leads['id'], df_leads['name']))
        selected_lead_id = st.selectbox("בחר לקוח:", list(lead_dict.keys()),
                                        format_func=lambda x: f"{lead_dict[x]} (ID: {x})")

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
        # המרת תאריך לפורמט קריא אם העמודה קיימת
        if 'upload_date' in files_df.columns:
            files_df['תאריך העלאה'] = pd.to_datetime(files_df['upload_date']).dt.strftime('%d/%m/%Y %H:%M')

        # תצוגה מותאמת
        for index, file_row in files_df.iterrows():
            with st.container(border=True):
                f_col1, f_col2, f_col3 = st.columns([3, 1, 1])

                # שם הקובץ ואייקון
                file_ext = str(file_row['filename']).split('.')[-1].lower() if pd.notna(file_row['filename']) else ""
                icon = "📄"
                if file_ext in ['pdf']:
                    icon = "📕"
                elif file_ext in ['png', 'jpg', 'jpeg']:
                    icon = "🖼️"
                elif file_ext in ['xlsx', 'xls']:
                    icon = "📊"

                f_col1.markdown(f"**{icon} {file_row['filename']}**")

                if 'תאריך העלאה' in file_row:
                    f_col1.caption(f"הועלה ב: {file_row['תאריך העלאה']}")

                # כפתורי פעולות
                with f_col2:
                    # שימוש ב-file_data רק אם הוגדר
                    file_data = file_row.get('file_data')
                    if pd.notna(file_data) and file_data is not None:
                        # מזהה סוג קובץ סטנדרטי להורדה
                        mime_type = "application/octet-stream"
                        if file_ext == 'pdf':
                            mime_type = "application/pdf"
                        elif file_ext in ['png', 'jpg', 'jpeg']:
                            mime_type = f"image/{file_ext}"

                        st.download_button(
                            label="⬇️ הורד",
                            data=file_data,
                            file_name=file_row['filename'],
                            mime=mime_type,
                            key=f"dl_{file_row['id']}",
                            use_container_width=True
                        )
                    else:
                        st.button("❌ לא זמין", key=f"dl_err_{file_row.get('id', index)}", disabled=True)

                with f_col3:
                    if st.button("🗑️ מחיקה", key=f"del_{file_row['id']}", type="secondary", use_container_width=True):
                        try:
                            if delete_file(conn, file_row['id']):
                                st.toast(f"הקובץ {file_row['filename']} נמחק בהצלחה!")
                                st.rerun()
                            else:
                                st.error("שגיאה במחיקת הקובץ.")
                        except Exception as e:
                            st.error(f"תקלה: {e}")

# --- העלאת קובץ חדש ---
with col_upload:
    st.subheader("📤 העלאת מסמך חדש")
    with st.container(border=True):
        uploaded_file = st.file_uploader("בחר קובץ (PDF, תמונות, אקסל)",
                                         type=['pdf', 'png', 'jpg', 'jpeg', 'xlsx', 'xls'])

        if uploaded_file:
            st.success(f"נבחר: {uploaded_file.name}")

            if st.button("💾 שמור בתיק לקוח", type="primary", use_container_width=True):
                with st.spinner("שומר..."):
                    try:
                        if save_file(conn, selected_lead_id, uploaded_file):
                            st.success("הקובץ נשמר בהצלחה!")
                            time.sleep(1)  # לתת למשתמש לראות את ההודעה
                            st.rerun()
                        else:
                            st.error("השמירה נכשלה במסד הנתונים.")
                    except Exception as e:
                        st.error(f"שגיאה בשמירת הקובץ: {e}")

if conn:
    conn.close()