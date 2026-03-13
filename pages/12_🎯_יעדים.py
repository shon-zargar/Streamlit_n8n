import streamlit as st
import pandas as pd
import plotly.express as px

# --- 1. הגדרת עמוד ---
st.set_page_config(layout="wide", page_title="ניהול יעדים", page_icon="🎯")

# --- 2. הגנת Session State ---
if 'auth_status' not in st.session_state:
    st.switch_page("app.py")

# --- 3. ייבוא בטוח מהמנוע ---
try:
    from engines import init_db, get_goals, setup_page_styling

    theme = setup_page_styling()
except ImportError as e:
    st.error(f"שגיאת טעינה: חסרים רכיבים בקובץ engines.py. פרטים: {e}")
    st.stop()

# --- 4. ממשק המשתמש ---
st.title("🎯 ניהול יעדים ומדדי ביצוע (KPIs)")
st.markdown("מעקב אחר התקדמות היעדים של הסוכנות והסוכנים בזמן אמת.")

# חיבור למסד הנתונים
try:
    conn = init_db()
except Exception as e:
    st.error(f"שגיאת חיבור ל-DB: {e}")
    conn = None

if not conn:
    st.stop()

# --- 5. משיכת נתונים בטוחה ---
with st.spinner("שואב נתוני יעדים..."):
    try:
        df_goals = get_goals(conn)
    except Exception as e:
        st.error(f"שגיאה במשיכת היעדים מהמסד: {e}")
        df_goals = pd.DataFrame()

# --- 6. תצוגת נתונים מוגנת ---
if df_goals.empty:
    st.info("📭 אין יעדים פעילים במערכת כרגע. ברגע שיוגדרו משימות שהן 'יעד', הן יופיעו כאן.")
else:
    # וידוא שעמודות החובה קיימות כדי למנוע KeyErrors
    required_cols = ['title', 'target', 'current', 'deadline']
    for col in required_cols:
        if col not in df_goals.columns:
            if col in ['target', 'current']:
                df_goals[col] = 0.0
            else:
                df_goals[col] = "לא מוגדר"

    st.subheader("📊 סקירת יעדים פעילים")

    # תצוגה ברשת (Grid) של 3 כרטיסיות בשורה
    cols = st.columns(3)
    for index, row in df_goals.iterrows():
        with cols[index % 3].container(border=True):
            st.markdown(f"<h5 style='color: #0d6efd;'>{row['title']}</h5>", unsafe_allow_html=True)

            # שליפה בטוחה של מספרים ומניעת חלוקה באפס
            target = float(row.get('target', 0))
            current = float(row.get('current', 0))

            # הגנה: אם היעד הוא 0 או פחות, נגדיר אותו ל-1 רק לצורך חישוב האחוזים (למנוע קריסה)
            safe_target = target if target > 0 else 1.0

            progress = min(current / safe_target, 1.0)
            progress_pct = int(progress * 100)

            # צבע הבר משתנה בהתאם להתקדמות (אופציונלי ויזואלית בסטרימליט)
            st.progress(progress, text=f"הושלם: {progress_pct}%")

            st.caption(f"**נוכחי:** {current:,.0f} | **יעד:** {target:,.0f}")

            # אם יש תאריך יעד תקין
            if pd.notna(row['deadline']) and str(row['deadline']).strip() != "לא מוגדר":
                st.caption(f"📅 תאריך יעד: {row['deadline']}")

    st.divider()

    # --- 7. גרף מגמות מוגן ---
    st.subheader("📈 ניתוח מגמות")
    try:
        # נסנן רק שורות שיש להן ערכים מספריים לצורך הגרף
        chart_df = df_goals[['title', 'target', 'current']].copy()

        # המרת עמודות לערכים מספריים (כדי ש-Plotly לא יקרוס על מחרוזות)
        chart_df['target'] = pd.to_numeric(chart_df['target'], errors='coerce').fillna(0)
        chart_df['current'] = pd.to_numeric(chart_df['current'], errors='coerce').fillna(0)

        fig = px.bar(
            chart_df,
            x='title',
            y=['current', 'target'],
            barmode='group',
            labels={'value': 'כמות / סכום', 'variable': 'מדד', 'title': 'שם היעד'},
            title="השוואת ביצועים מול יעדים",
            template=theme.get('plot', 'plotly')
        )
        # שינוי שמות המקרא לעברית
        newnames = {'current': 'ביצוע נוכחי', 'target': 'יעד'}
        fig.for_each_trace(lambda t: t.update(name=newnames.get(t.name, t.name),
                                              legendgroup=newnames.get(t.name, t.name)))

        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.warning(f"⚠️ לא ניתן לייצר גרף עם הנתונים הנוכחיים (ייתכן וחסרים ערכים מספריים). פרטים: {e}")

if conn:
    conn.close()