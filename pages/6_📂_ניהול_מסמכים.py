import streamlit as st
import time

from engines import init_db, get_leads_data, get_files, save_file, delete_file, setup_page_styling

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="ניהול מסמכים")

# --- Global Styling ---
theme = setup_page_styling()

# --- Database Connection ---
conn = init_db()

# --- Main Page ---
st.title("📂 ניהול מסמכים וארכיון")

df = get_leads_data(conn)

if df.empty:
    st.warning("אין לקוחות במערכת")
else:
    # Select lead
    lead_id = st.selectbox(
        "בחר לקוח:",
        df['id'].tolist(),
        format_func=lambda x: df[df['id'] == x]['name'].values[0]
    )

    current_lead = df[df['id'] == lead_id].iloc[0]

    st.info(f"**לקוח נבחר:** {current_lead['name']} | {current_lead['phone']}")

    # Upload files
    st.divider()
    st.subheader("📤 העלאת קבצים")

    with st.form("upload_files"):
        uploaded_files = st.file_uploader("בחר קבצים להעלאה", accept_multiple_files=True)
        if st.form_submit_button("💾 שמור קבצים", type="primary") and uploaded_files:
            for f in uploaded_files:
                save_file(conn, lead_id, f)
            st.success(f"✅ {len(uploaded_files)} קבצים נשמרו בהצלחה!")
            time.sleep(0.5)
            st.rerun()

    # Display files
    st.divider()
    st.subheader("📁 תיק מסמכים")

    files = get_files(conn, lead_id)

    if files.empty:
        st.info("אין קבצים בתיק זה")
    else:
        st.caption(f"סה'כ {len(files)} קבצים בתיק")

        for _, file_row in files.iterrows():
            col1, col2, col3, col4 = st.columns([1, 4, 3, 2])

            col1.text(file_row['id'])
            col2.text(file_row['filename'])
            col3.text(file_row['upload_date'][:16])

            with col4:
                try:
                    blob = conn.execute("SELECT file_data FROM files WHERE id=?", (file_row['id'],)).fetchone()[0]
                    st.download_button("📥 הורד", blob, file_row['filename'], key=f"dl_doc_{file_row['id']}")

                    if st.button("🗑️ מחק", key=f"del_doc_{file_row['id']}"):
                        delete_file(conn, file_row['id'])
                        st.success("הקובץ נמחק!")
                        time.sleep(0.5)
                        st.rerun()
                except Exception as e:
                    st.error(f"שגיאה בגישה לקובץ: {e}")

            # Preview for images
            if file_row['filename'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                with st.expander("🖼️ תצוגה מקדימה"):
                    try:
                        blob = conn.execute("SELECT file_data FROM files WHERE id=?", (file_row['id'],)).fetchone()[0]
                        st.image(blob, caption=file_row['filename'], use_container_width=True)
                    except:
                        st.error("לא ניתן להציג את התמונה")