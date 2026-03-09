import sqlite3
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# הגדרות ביטחון - שים לב לעדכן את ה-ID שלך!
TOKEN = "xxxxxxx"
ADMIN_IDS = [xxxxxx]  # שון, תחליף ל-ID האמיתי שלך


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text(f"❌ גישה חסומה (ID: {update.effective_user.id})")
        return
    await update.message.reply_text(
        "💎 שלום שון! בוט ה-CRM הפרטי שלך מחובר למערכת.\n\nפקודות זמינות:\n/today - לידים לטיפול היום\n/summary - סיכום מצב כללי")


async def leads_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return

    conn = sqlite3.connect('leads_pro_ultimate.db')
    cursor = conn.cursor()
    today = datetime.datetime.now().strftime('%Y-%m-%d')

    cursor.execute("SELECT name, phone, status FROM leads WHERE callback_date <= ? AND status != 'נמכר'", (today,))
    leads = cursor.fetchall()

    if not leads:
        await update.message.reply_text("✅ אין משימות דחופות להיום. יום רגוע!")
    else:
        text = "🚨 *לידים לטיפול דחוף להיום:*\n\n"
        for l in leads:
            text += f"• *{l[0]}* - {l[1]} ({l[2]})\n"
        await update.message.reply_text(text, parse_mode='Markdown')
    conn.close()


async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    conn = sqlite3.connect('leads_pro_ultimate.db')
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) FROM leads GROUP BY status")
    stats = cursor.fetchall()

    text = "📊 *סיכום סטטוסים בתיק:*\n\n"
    for s in stats:
        text += f"• {s[0]}: {s[1]}\n"
    await update.message.reply_text(text, parse_mode='Markdown')
    conn.close()


if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", leads_today))
    app.add_handler(CommandHandler("summary", summary))
    print("🚀 הבוט הפרטי של שון רץ...")
    app.run_polling()
