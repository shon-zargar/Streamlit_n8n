import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import math
import json
import io

from engines import (
    init_db, get_leads_data, FinanceEngine, generate_hebrew_pdf,
    COMMISSION_RATES, setup_page_styling, N8nIntegration,
    AIEngine, AISalesCoach, get_smart_age_insights
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
    search_text = fcol1.text_input("חיפוש חופשי", placeholder="שם, טלפון, ת.ז...")
    filter_status = fcol2.multiselect("סטטוס", df['status'].unique())
    filter_source = fcol3.multiselect("מקור", df['source'].unique())
    min_comm = fcol4.number_input("עמלה מינימלית", 0, int(df['estimated_commission'].max() if not df.empty else 0), 0)

filtered = df.copy()
if search_text:
    filtered = filtered[
        filtered['name'].str.contains(search_text, case=False, na=False) |
        filtered['phone'].str.contains(search_text, case=False, na=False) |
        filtered['id_number'].str.contains(search_text, case=False, na=False)
        ]
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

# הפרדה מלאה של עמודות התאריכים בתצוגה
display_cols = ['name', 'phone', 'id_number', 'issue_date', 'expiry_date', 'status', 'source', 'estimated_commission']
display_df = filtered.iloc[start_idx:end_idx][display_cols].copy()
display_df.columns = ['שם', 'טלפון', 'ת.ז', 'ת. הנפקה', 'ת. תוקף', 'סטטוס', 'מקור', 'עמלה']

st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)

# --- Detailed Edit & AI Coach ---
st.divider()
st.subheader("⚙️ אזור עבודה חכם - כרטיס לקוח")

lead_to_edit_id = st.selectbox("בחר ליד לעבודה שוטפת:", filtered['id'].tolist(), format_func=lambda
    x: f"{filtered[filtered['id'] == x]['name'].values[0]} (ID: {x})") if not filtered.empty else None

if lead_to_edit_id:
    # שליפת נתוני הליד כ-Series וכ-Dict (עבור ה-AI)
    lead_row_series = filtered[filtered['id'] == lead_to_edit_id].iloc[0]
    lead_row_dict = lead_row_series.to_dict()

    # --- יצירת לשוניות (Tabs) ---
    tab_edit, tab_ai = st.tabs(["✏️ עריכת פרטים וסטטוס", "🧠 תובנות AI (Sales Coach)"])

    # ----------------------------------------
    # TAB 1: עריכת פרטים (הקוד המקורי שלך)
    # ----------------------------------------
    with tab_edit:
        # --- עדכון סטטוס מהיר ---
        col_status1, col_status2 = st.columns([1, 3])
        with col_status1:
            current_status_idx = STATUS_OPTIONS.index(lead_row_series['status']) if lead_row_series[
                                                                                        'status'] in STATUS_OPTIONS else 0
            new_quick_status = st.selectbox("עדכון סטטוס מהיר:", STATUS_OPTIONS, index=current_status_idx,
                                            key="quick_status_change")

            if new_quick_status != lead_row_series['status']:
                conn.execute("UPDATE leads SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                             (new_quick_status, lead_to_edit_id))
                conn.commit()

                N8nIntegration.notify_status_change({
                    "lead_id": int(lead_to_edit_id),
                    "name": lead_row_series['name'],
                    "old_status": lead_row_series['status'],
                    "new_status": new_quick_status
                })
                st.success(f"הסטטוס עודכן בהצלחה ל-{new_quick_status}!")
                time.sleep(1)
                st.rerun()

        # --- טופס עריכה מפורט ---
        with st.form("detailed_edit_form"):
            st.info("פרטים אישיים")
            ecol1, ecol2, ecol3 = st.columns(3)
            e_name = ecol1.text_input("שם", lead_row_series['name'])
            e_phone = ecol2.text_input("טלפון", lead_row_series['phone'])
            e_source = ecol3.selectbox("מקור", SOURCE_OPTIONS,
                                       index=SOURCE_OPTIONS.index(lead_row_series['source']) if lead_row_series[
                                                                                                    'source'] in SOURCE_OPTIONS else 0)

            # הפרדת שדות ת"ז, הנפקה ותוקף בטופס (3 עמודות)
            ecol_id1, ecol_id2, ecol_id3 = st.columns(3)
            e_id_number = ecol_id1.text_input("מספר תעודת זהות", lead_row_series['id_number'] if pd.notna(
                lead_row_series.get('id_number')) else "")
            e_issue_date = ecol_id2.text_input("תאריך הנפקה", lead_row_series['issue_date'] if pd.notna(
                lead_row_series.get('issue_date')) else "")
            e_expiry_date = ecol_id3.text_input("תאריך תוקף", lead_row_series['expiry_date'] if pd.notna(
                lead_row_series.get('expiry_date')) else "")

            ecol4, ecol5, ecol6 = st.columns(3)
            e_email = ecol4.text_input("אימייל", lead_row_series['email'] if lead_row_series['email'] else "")

            try:
                b_val = datetime.strptime(lead_row_series['birth_date'], '%Y-%m-%d').date() if lead_row_series[
                    'birth_date'] else None
            except:
                b_val = None
            e_birth = ecol5.date_input("תאריך לידה", b_val, min_value=date(1920, 1, 1), max_value=datetime.now().date())

            ms_opts = ["רווק", "נשוי", "גרוש", "אלמן"]
            e_marital = ecol6.selectbox("סטטוס משפחתי", ms_opts,
                                        index=ms_opts.index(lead_row_series['marital_status']) if lead_row_series[
                                                                                                      'marital_status'] in ms_opts else 0)

            e_children = st.number_input("מספר ילדים", 0, 15,
                                         int(lead_row_series['children']) if lead_row_series['children'] else 0)

            st.info("תיק ביטוחי")
            try:
                policies_df = pd.DataFrame(json.loads(lead_row_series['policies_json']))
            except:
                policies_df = pd.DataFrame([{"type": "בחר...", "company": "בחר...", "prem": 0}])

            policy_config = {
                "type": st.column_config.SelectboxColumn("מוצר", options=["רכב", "דירה", "בריאות", "חיים", "פנסיוני",
                                                                          "משכנתה"]),
                "company": st.column_config.SelectboxColumn("חברה", options=list(COMMISSION_RATES.keys())),
                "prem": st.column_config.NumberColumn("פרמיה חודשית", format="₪%.0f")
            }
            e_policies = st.data_editor(policies_df, column_config=policy_config, num_rows="dynamic",
                                        use_container_width=True, key="policy_editor")

            st.info("תזמון והערות")
            ecol7, ecol8 = st.columns(2)
            try:
                c_val = datetime.strptime(lead_row_series['callback_date'], '%Y-%m-%d').date() if lead_row_series[
                    'callback_date'] else datetime.now().date()
            except:
                c_val = datetime.now().date()
            e_callback = ecol7.date_input("תאריך חזרה", c_val)

            try:
                r_val = datetime.strptime(lead_row_series['renewal_date'], '%Y-%m-%d').date() if lead_row_series[
                    'renewal_date'] else None
            except:
                r_val = None
            e_renewal = ecol8.date_input("תאריך חידוש", r_val)

            e_notes = st.text_area("הערות בתיק", lead_row_series['notes'] if lead_row_series['notes'] else "",
                                   height=100)

            if st.form_submit_button("💾 שמור שינויים", type="primary"):
                new_policies = [p for p in e_policies.to_dict('records') if p.get('type') != "בחר..."]
                total_prem = sum(p.get('prem', 0) for p in new_policies)
                total_comm = sum(
                    FinanceEngine.calculate_smart_commission(p['company'], p['type'], p.get('prem', 0)) for p in
                    new_policies)
                policies_json = json.dumps(new_policies, ensure_ascii=False)

                bd_str = e_birth.strftime('%Y-%m-%d') if e_birth else None
                ren_str = e_renewal.strftime('%Y-%m-%d') if e_renewal else None

                conn.execute("""
                    UPDATE leads SET 
                    name=?, phone=?, id_number=?, issue_date=?, expiry_date=?, email=?, birth_date=?, marital_status=?, children=?, 
                    source=?, policies_json=?, monthly_premium=?, estimated_commission=?, 
                    callback_date=?, renewal_date=?, notes=?, updated_at=CURRENT_TIMESTAMP 
                    WHERE id=?
                """, (e_name, e_phone, e_id_number, e_issue_date, e_expiry_date, e_email, bd_str, e_marital, e_children,
                      e_source,
                      policies_json, total_prem, total_comm, e_callback.strftime('%Y-%m-%d'), ren_str, e_notes,
                      lead_to_edit_id))
                conn.commit()

                st.success("✅ פרטי הליד עודכנו בהצלחה!")
                time.sleep(1)
                st.rerun()

        # Generate PDF Button
        if st.button("📄 הורד דוח PDF ללקוח", key="pdf_single"):
            pdf_buffer = generate_hebrew_pdf(lead_row_dict)
            st.download_button("📥 לחץ כאן להורדת ה-PDF", pdf_buffer, f"lead_report_{lead_to_edit_id}.pdf",
                               "application/pdf")

    # ----------------------------------------
    # TAB 2: יועץ ה-AI (השדרוג החדש)
    # ----------------------------------------
    with tab_ai:
        col_score, col_action, col_insights = st.columns(3)

        # 1. מדד חום הליד
        lead_score = AIEngine.calculate_lead_score(lead_row_dict, conn)
        with col_score:
            st.markdown("### 🎯 מדד חום (Lead Score)")
            if lead_score >= 80:
                st.success(f"**{lead_score}/100** - ליד רותח! 🔥")
            elif lead_score >= 50:
                st.warning(f"**{lead_score}/100** - ליד פושר 🟡")
            else:
                st.error(f"**{lead_score}/100** - ליד קר ❄️")
            st.caption("מחושב לפי זמן במערכת, כמות אינטראקציות ופוטנציאל עמלה.")

        # 2. פעולה מומלצת הבאה
        with col_action:
            st.markdown("### 📅 המלצה לפעולה")
            st.info(AIEngine.suggest_next_action(lead_row_dict))
            st.caption("מבוסס על תאריך החזרה המתוכנן שנקבע בתיק.")

        # 3. תובנות גיל
        age, age_insights = get_smart_age_insights(lead_row_dict.get('birth_date', ''))
        with col_insights:
            st.markdown("### 🎂 תובנות דמוגרפיות")
            if age:
                st.markdown(f"**גיל:** {age}")
                for insight in age_insights: st.markdown(f"- {insight}")
            else:
                st.write("נא להזין תאריך לידה בטאב העריכה כדי לקבל תובנות.")

        st.divider()
        col_cross, col_nlp = st.columns(2)

        # 4. זיהוי הזדמנויות למכירה צולבת
        with col_cross:
            st.markdown("### 💡 מנוע Cross-Sell")
            cross_opps = AIEngine.identify_cross_sell(lead_row_dict)
            if cross_opps:
                st.write("זיהינו פוטנציאל להרחבת התיק הביטוחי:")
                for opp in cross_opps: st.error(opp)  # אדום כדי לבלוט כחוסר
            else:
                st.success("✅ לא נמצאו פערים בולטים בתיק הביטוחי כרגע.")

        # 5. מנתח שיחות AI
        with col_nlp:
            st.markdown("### 🕵️‍♂️ Sales Coach")
            notes = lead_row_dict.get('notes', '')
            if notes:
                analysis = AISalesCoach.analyze_sales_notes(notes)
                st.markdown(f"**סנטימנט השיחה:** {analysis['sentiment']}")

                if analysis['tips']:
                    st.markdown("**טיפים לשיחה הבאה:**")
                    for tip in analysis['tips']: st.markdown(f"- {tip}")
                if analysis['tasks']:
                    st.markdown("**משימות שנגזרו מההערות:**")
                    for task in analysis['tasks']: st.markdown(f"- {task}")
            else:
                st.info("נא לכתוב הערות בטאב העריכה ולשמור כדי לקבל ניתוח שיחה אוטומטי.")

conn.close()