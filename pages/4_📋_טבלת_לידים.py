import streamlit as st
import pandas as pd
from datetime import datetime
import time
import math

# --- 1. הגדרת העמוד ---
st.set_page_config(layout="wide", page_title="טבלת לידים", page_icon="📋")

# --- כפיית יישור למרכז לטבלאות ספציפית בדף הזה ---
st.markdown("""
<style>
    /* מכריח את כל תאי הטבלה והכותרות להיות ממורכזים לחלוטין */
    [data-testid="stDataFrame"] div[role="gridcell"], 
    [data-testid="stDataEditor"] div[role="gridcell"],
    [data-testid="stDataFrame"] div[role="columnheader"],
    [data-testid="stDataEditor"] div[role="columnheader"] {
        display: flex !important;
        justify-content: center !important;
        text-align: center !important;
    }

    /* מוודא שטקסט באנגלית ומספרים לא יקפצו הצידה */
    [data-testid="stDataFrame"] p, 
    [data-testid="stDataEditor"] p {
        text-align: center !important;
        width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. אבטחה וניהול זיכרון ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. טעינה מאובטחת של המנוע ---
try:
    from engines import (
        init_db, get_leads_data, setup_page_styling,
        add_interaction, AISalesCoach, AIEngine, get_interactions
    )

    theme = setup_page_styling()
except ImportError:
    st.error("שגיאה בטעינת קובצי המערכת (engines.py).")
    st.stop()

st.title("📋 טבלת לידים - ניהול ועריכה")

# חיבור למסד ושליפת נתונים
conn = init_db()
df = get_leads_data(conn)

if df.empty:
    st.info("📭 אין לידים להצגה.")
else:
    # --- אזור סינונים ---
    with st.expander("🔍 סינון וחיפוש"):
        col1, col2, col3, col4 = st.columns(4)
        search_term = col1.text_input("חיפוש חופשי:")
        status_list = ["הכל"] + df['status'].unique().tolist() if 'status' in df.columns else ["הכל"]
        selected_status = col2.selectbox("סטטוס", status_list)
        source_list = ["הכל"] + df['source'].unique().tolist() if 'source' in df.columns else ["הכל"]
        selected_source = col3.selectbox("מקור", source_list)
        min_comm = col4.number_input("עמלה מינימלית", min_value=0, value=0)

    # החלת סינונים
    filtered_df = df.copy()
    if search_term:
        mask = filtered_df.apply(lambda row: search_term.lower() in str(row.to_dict()).lower(), axis=1)
        filtered_df = filtered_df[mask]
    if selected_status != "הכל":
        filtered_df = filtered_df[filtered_df['status'] == selected_status]
    if selected_source != "הכל":
        filtered_df = filtered_df[filtered_df['source'] == selected_source]

    # ==========================================
    # --- מנגנון דפדוף (5 תוצאות) ---
    # ==========================================
    PAGE_SIZE = 5
    if 'leads_page_index' not in st.session_state: st.session_state.leads_page_index = 0
    total_pages = math.ceil(len(filtered_df) / PAGE_SIZE) if not filtered_df.empty else 1
    if st.session_state.leads_page_index >= total_pages: st.session_state.leads_page_index = 0

    pg_col1, pg_col2, pg_col3 = st.columns([1, 4, 1])
    if pg_col1.button("⬅️ הקודם", disabled=st.session_state.leads_page_index <= 0):
        st.session_state.leads_page_index -= 1
        st.rerun()
    pg_col2.markdown(
        f"<p style='text-align: center;'>עמוד {st.session_state.leads_page_index + 1} מתוך {total_pages}</p>",
        unsafe_allow_html=True)
    if pg_col3.button("הבא ➡️", disabled=st.session_state.leads_page_index >= total_pages - 1):
        st.session_state.leads_page_index += 1
        st.rerun()

    start_idx = st.session_state.leads_page_index * PAGE_SIZE
    paged_df = filtered_df.iloc[start_idx:start_idx + PAGE_SIZE].copy()

    # --- הכנת נתונים לתצוגה ---
    cols_to_hide = ['policies_json', 'notes', 'created_at', 'updated_at', 'health_score', 'engagement_level',
                    'issue_date', 'expiry_date']
    display_df = paged_df.drop(columns=[c for c in cols_to_hide if c in paged_df.columns])

    # המרת תאריכים וציונים
    if 'callback_date' in display_df.columns:
        display_df['callback_date'] = pd.to_datetime(display_df['callback_date'], errors='coerce')
    if 'lead_score' in display_df.columns:
        display_df['lead_score'] = pd.to_numeric(display_df['lead_score'], errors='coerce').fillna(0)

    # ==========================================
    # --- חישוב רוחב עמודות דינמי מדויק ותרגום ---
    # ==========================================
    heb_names = {
        "id": "מזהה",
        "name": "שם",
        "phone": "טלפון",
        "email": "אימייל",
        "status": "סטטוס",
        "source": "מקור",
        "callback_date": "תאריך חזרה",
        "estimated_commission": "עמלה משוערת",
        "lead_score": "ציון",
        "birth_date": "תאריך לידה",
        "marital_status": "סטטוס משפחתי",
        "children": "ילדים",
        "id_number": "ת.ז"
    }

    column_config = {}
    for col in display_df.columns:
        heb_label = heb_names.get(col, col)

        # מחשב את אורך הטקסט הכי ארוך בעמודה הנוכחית - עטיפה ב-int() כדי לפתור את שגיאת ה-JSON
        max_len = int(max(
            display_df[col].astype(str).map(len).max() if not display_df.empty else 0,
            len(heb_label)
        ))

        # חישוב פיקסלים: המרה מפורשת ל-int של פייתון
        calc_width = int(min(max(max_len * 10 + 30, 80), 400))

        # הגדרות מיוחדות לפי סוג עמודה
        if col == "lead_score":
            column_config[col] = st.column_config.ProgressColumn(heb_label, min_value=0, max_value=100, format="%d",
                                                                 width=calc_width)
        elif col == "callback_date":
            column_config[col] = st.column_config.DateColumn(heb_label, format="DD/MM/YYYY", width=calc_width)
        else:
            column_config[col] = st.column_config.Column(heb_label, width=calc_width)

    # תצוגת הטבלה
    st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        disabled=True
    )

    st.divider()

    # ==========================================
    # --- אזור עבודה חכם (Smart Workspace) - כל השדות ---
    # ==========================================
    st.subheader("⚙️ אזור עבודה חכם - כרטיס לקוח מלא")

    lead_dict = {row['id']: f"{row.get('name', 'ללא שם')} (ID: {row['id']})" for idx, row in filtered_df.iterrows()}

    if lead_dict:
        selected_lead_id = st.selectbox("בחר ליד לעריכה מלאה:", list(lead_dict.keys()),
                                        format_func=lambda x: lead_dict[x])
        lead_row = df[df['id'] == selected_lead_id].iloc[0]

        tabs = st.tabs(["✏️ עריכת כל פרטי הליד", "🧠 תובנות AI"])

        with tabs[0]:
            with st.form(key=f"full_edit_{selected_lead_id}"):

                def safe_str(val):
                    return str(val) if pd.notna(val) else ""


                st.markdown("#### 👤 פרטי לקוח וסטטוס")
                c1, c2, c3, c4 = st.columns(4)
                new_name = c1.text_input("שם מלא", value=safe_str(lead_row.get('name')))
                new_phone = c2.text_input("טלפון", value=safe_str(lead_row.get('phone')))
                new_email = c3.text_input("אימייל", value=safe_str(lead_row.get('email')))

                status_opts = ["חדש", "בטיפול", "לא עונה", "נמכר", "לא רלוונטי", "פגישה תואמה"]
                curr_status = lead_row.get('status', 'חדש')
                new_status = c4.selectbox("סטטוס", status_opts,
                                          index=status_opts.index(curr_status) if curr_status in status_opts else 0)

                st.markdown("#### 🪪 פרטי זיהוי ודמוגרפיה")
                d1, d2, d3, d4 = st.columns(4)
                new_id = d1.text_input("ת.ז", value=safe_str(lead_row.get('id_number')))

                try:
                    b_val = datetime.strptime(str(lead_row.get('birth_date')), '%Y-%m-%d').date() if pd.notna(
                        lead_row.get('birth_date')) and lead_row.get('birth_date') else None
                except:
                    b_val = None
                new_birth = d2.date_input("תאריך לידה", value=b_val)

                marital_opts = ["", "רווק/ה", "נשוי/ה", "גרוש/ה", "אלמן/ה"]
                curr_marital = safe_str(lead_row.get('marital_status'))
                new_marital = d3.selectbox("מצב משפחתי", marital_opts, index=marital_opts.index(
                    curr_marital) if curr_marital in marital_opts else 0)

                kids_val = lead_row.get('children', 0)
                new_kids = d4.number_input("ילדים", min_value=0,
                                           value=int(kids_val) if pd.notna(kids_val) and str(kids_val).isdigit() else 0)

                st.markdown("#### 🗓️ מקור, פיננסי וחזרה")
                f1, f2, f3 = st.columns(3)
                source_opts = ["פייסבוק", "גוגל", "חבר מביא חבר", "וואטסאפ", "אחר"]
                curr_source = safe_str(lead_row.get('source'))
                new_src = f1.selectbox("מקור", source_opts,
                                       index=source_opts.index(curr_source) if curr_source in source_opts else 4)

                try:
                    cb_val = datetime.strptime(str(lead_row.get('callback_date')), '%Y-%m-%d').date() if pd.notna(
                        lead_row.get('callback_date')) and lead_row.get('callback_date') else datetime.now().date()
                except:
                    cb_val = datetime.now().date()
                new_cb = f2.date_input("תאריך חזרה", value=cb_val)

                comm_val = lead_row.get('estimated_commission', 0.0)
                new_comm = f3.number_input("עמלה (₪)", value=float(comm_val) if pd.notna(comm_val) else 0.0)

                new_notes = st.text_area("הערות:", value=safe_str(lead_row.get('notes')))

                if st.form_submit_button("💾 שמור את כל השינויים", type="primary", use_container_width=True):
                    try:
                        conn.execute("""
                            UPDATE leads SET name=?, phone=?, email=?, status=?, id_number=?, birth_date=?, 
                            marital_status=?, children=?, source=?, callback_date=?, estimated_commission=?, notes=?, updated_at=CURRENT_TIMESTAMP 
                            WHERE id=?
                        """, (
                            new_name, new_phone, new_email, new_status, new_id,
                            str(new_birth) if new_birth else None, new_marital, new_kids, new_src,
                            str(new_cb) if new_cb else None, new_comm, new_notes, selected_lead_id
                        ))
                        conn.commit()
                        add_interaction(conn, selected_lead_id, "עדכון מקיף", "כל השדות עודכנו")
                        st.success("נשמר בהצלחה!")
                        time.sleep(0.5)
                        st.rerun()
                    except Exception as e:
                        st.error(f"שגיאה בעדכון מסד הנתונים: {e}")

        with tabs[1]:
            st.info(f"ניתוח AI עבור {lead_row.get('name')}")
            try:
                ai_analysis = AISalesCoach.analyze_sales_notes(safe_str(lead_row.get('notes')))
                if ai_analysis and 'tips' in ai_analysis and ai_analysis['tips']:
                    st.write(ai_analysis['tips'][0])
                else:
                    st.write("אין תובנות מיוחדות כרגע מבוססות על ההערות הקיימות.")
            except Exception:
                st.write("שגיאה בטעינת המאמן החכם.")

if conn:
    conn.close()