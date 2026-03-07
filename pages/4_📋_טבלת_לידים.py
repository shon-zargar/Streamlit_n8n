import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import math
import json
import io

from engines import (
    init_db, get_leads_data, calculate_smart_commission, generate_hebrew_pdf,
    COMMISSION_RATES, setup_page_styling, N8nIntegration
)

# --- Page Configuration & Styling ---
st.set_page_config(layout="wide", page_title="טבלת לידים")
theme = setup_page_styling()

# --- Constants & DB ---
ITEMS_PER_PAGE = 10
SOURCE_OPTIONS = ["פייסבוק", "גוגל", "חבר מביא חבר", "אינסטגרם", "טיקטוק", "רכישת לידים", "LinkedIn", "אתר אינטרנט",
                  "אחר"]
STATUS_OPTIONS = ["חדש", "בטיפול", "לא עונה", "נמכר", "לא רלוונטי", "פגישה תואמה"]
conn = init_db()

# --- Main Page ---
st.title("📋 טבלת לידים - ניהול ועריכה")

df = get_leads_data(conn)

if df.empty:
    st.info("אין לידים במערכת")
    st.stop()

# --- Filters ---
with st.expander("🔍 סינון וחיפוש", expanded=True):
    fcol1, fcol2, fcol3, fcol4 = st.columns(4)
    search_text = fcol1.text_input("חיפוש חופשי", placeholder="שם, טלפון...")
    filter_status = fcol2.multiselect("סטטוס", df['status'].unique())
    filter_source = fcol3.multiselect("מקור", df['source'].unique())
    min_comm = fcol4.number_input("עמלה מינימלית", 0, int(df['estimated_commission'].max() if not df.empty else 0), 0)

filtered = df.copy()
if search_text:
    filtered = filtered[
        filtered['name'].str.contains(search_text, case=False, na=False) | filtered['phone'].str.contains(search_text,
                                                                                                          case=False,
                                                                                                          na=False)]
if filter_status:
    filtered = filtered[filtered['status'].isin(filter_status)]
if filter_source:
    filtered = filtered[filtered['source'].isin(filter_source)]
if min_comm > 0:
    filtered = filtered[filtered['estimated_commission'] >= min_comm]

st.caption(f"מציג {len(filtered)} מתוך {len(df)} לידים")

# --- Pagination & Display Table ---
if 'table_page' not in st.session_state:
    st.session_state.table_page = 0

total_pages = math.ceil(len(filtered) / ITEMS_PER_PAGE)
if st.session_state.table_page >= total_pages and total_pages > 0:
    st.session_state.table_page = 0

pcol1, pcol2, pcol3 = st.columns([1, 8, 1])
if pcol1.button("⬅️", key="tprev"):
    st.session_state.table_page = max(0, st.session_state.table_page - 1)
    st.rerun()
pcol2.markdown(f"<div style='text-align:center;'>עמוד {st.session_state.table_page + 1}/{max(1, total_pages)}</div>",
               unsafe_allow_html=True)
if pcol3.button("➡️", key="tnext"):
    st.session_state.table_page = min(total_pages - 1, st.session_state.table_page + 1)
    st.rerun()

start_idx = st.session_state.table_page * ITEMS_PER_PAGE
end_idx = start_idx + ITEMS_PER_PAGE

display_cols = ['name', 'phone', 'status', 'source', 'estimated_commission', 'callback_date', 'lead_score']
display_df = filtered.iloc[start_idx:end_idx][display_cols].copy()
display_df.columns = ['שם', 'טלפון', 'סטטוס', 'מקור', 'עמלה', 'תאריך חזרה', 'Score']

st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

# --- Detailed Edit Form ---
st.divider()
st.subheader("✏️ עריכת ליד ושינוי סטטוס")

lead_to_edit_id = st.selectbox("בחר ליד לעריכה:", filtered['id'].tolist(), format_func=lambda
    x: f"{filtered[filtered['id'] == x]['name'].values[0]} (ID: {x})") if not filtered.empty else None

if lead_to_edit_id:
    lead_row = filtered[filtered['id'] == lead_to_edit_id].iloc[0]

    # --- עדכון סטטוס מהיר ---
    col_status1, col_status2 = st.columns([1, 3])
    with col_status1:
        current_status_idx = STATUS_OPTIONS.index(lead_row['status']) if lead_row['status'] in STATUS_OPTIONS else 0
        new_quick_status = st.selectbox("עדכון סטטוס מהיר:", STATUS_OPTIONS, index=current_status_idx,
                                        key="quick_status_change")

        if new_quick_status != lead_row['status']:
            conn.execute("UPDATE leads SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                         (new_quick_status, lead_to_edit_id))
            conn.commit()

            # שליחת התראה ל-n8n על שינוי סטטוס
            N8nIntegration.notify_status_change({
                "lead_id": int(lead_to_edit_id),
                "name": lead_row['name'],
                "old_status": lead_row['status'],
                "new_status": new_quick_status
            })
            st.success(f"הסטטוס עודכן בהצלחה ל-{new_quick_status}!")
            time.sleep(1)
            st.rerun()

    # --- טופס עריכה מפורט למטה ---
    with st.form("detailed_edit_form"):
        st.info("פרטים אישיים")
        ecol1, ecol2, ecol3 = st.columns(3)
        e_name = ecol1.text_input("שם", lead_row['name'])
        e_phone = ecol2.text_input("טלפון", lead_row['phone'])
        e_source = ecol3.selectbox("מקור", SOURCE_OPTIONS, index=SOURCE_OPTIONS.index(lead_row['source']) if lead_row[
                                                                                                                 'source'] in SOURCE_OPTIONS else 0)

        ecol4, ecol5, ecol6 = st.columns(3)
        e_email = ecol4.text_input("אימייל", lead_row['email'] if lead_row['email'] else "")

        try:
            b_val = datetime.strptime(lead_row['birth_date'], '%Y-%m-%d').date() if lead_row['birth_date'] else None
        except:
            b_val = None
        e_birth = ecol5.date_input("תאריך לידה", b_val, min_value=date(1920, 1, 1), max_value=datetime.now().date())

        ms_opts = ["רווק", "נשוי", "גרוש", "אלמן"]
        e_marital = ecol6.selectbox("סטטוס משפחתי", ms_opts,
                                    index=ms_opts.index(lead_row['marital_status']) if lead_row[
                                                                                           'marital_status'] in ms_opts else 0)

        e_children = st.number_input("מספר ילדים", 0, 15, int(lead_row['children']) if lead_row['children'] else 0)

        st.info("תיק ביטוחי")
        try:
            policies_df = pd.DataFrame(json.loads(lead_row['policies_json']))
        except:
            policies_df = pd.DataFrame([{"type": "בחר...", "company": "בחר...", "prem": 0}])

        policy_config = {
            "type": st.column_config.SelectboxColumn("מוצר",
                                                     options=["רכב", "דירה", "בריאות", "חיים", "פנסיוני", "משכנתה"]),
            "company": st.column_config.SelectboxColumn("חברה", options=list(COMMISSION_RATES.keys())),
            "prem": st.column_config.NumberColumn("פרמיה חודשית", format="₪%.0f")
        }
        e_policies = st.data_editor(policies_df, column_config=policy_config, num_rows="dynamic",
                                    use_container_width=True, key="policy_editor")

        st.info("תזמון והערות")
        ecol7, ecol8 = st.columns(2)
        try:
            c_val = datetime.strptime(lead_row['callback_date'], '%Y-%m-%d').date() if lead_row[
                'callback_date'] else datetime.now().date()
        except:
            c_val = datetime.now().date()
        e_callback = ecol7.date_input("תאריך חזרה", c_val)

        try:
            r_val = datetime.strptime(lead_row['renewal_date'], '%Y-%m-%d').date() if lead_row['renewal_date'] else None
        except:
            r_val = None
        e_renewal = ecol8.date_input("תאריך חידוש", r_val)

        e_notes = st.text_area("הערות בתיק", lead_row['notes'] if lead_row['notes'] else "", height=100)

        if st.form_submit_button("💾 עדכן את כל הפרטים המלאים", type="primary"):
            new_policies = [p for p in e_policies.to_dict('records') if p.get('type') != "בחר..."]
            total_prem = sum(p.get('prem', 0) for p in new_policies)
            total_comm = sum(
                calculate_smart_commission(p['company'], p['type'], p.get('prem', 0)) for p in new_policies)
            policies_json = json.dumps(new_policies, ensure_ascii=False)

            bd_str = e_birth.strftime('%Y-%m-%d') if e_birth else None
            ren_str = e_renewal.strftime('%Y-%m-%d') if e_renewal else None

            conn.execute("""
                UPDATE leads SET 
                name=?, phone=?, email=?, birth_date=?, marital_status=?, children=?, 
                source=?, policies_json=?, monthly_premium=?, estimated_commission=?, 
                callback_date=?, renewal_date=?, notes=?, updated_at=CURRENT_TIMESTAMP 
                WHERE id=?
            """, (e_name, e_phone, e_email, bd_str, e_marital, e_children, e_source,
                  policies_json, total_prem, total_comm, e_callback.strftime('%Y-%m-%d'), ren_str, e_notes,
                  lead_to_edit_id))
            conn.commit()

            st.success("✅ פרטי הליד עודכנו בהצלחה!")
            time.sleep(1)
            st.rerun()

    # Generate PDF Button
    if st.button("📄 הורד דוח PDF ללקוח", key="pdf_single"):
        pdf_buffer = generate_hebrew_pdf(lead_row)
        st.download_button(
            "📥 לחץ כאן להורדת ה-PDF",
            pdf_buffer,
            f"lead_report_{lead_to_edit_id}.pdf",
            "application/pdf"
        )