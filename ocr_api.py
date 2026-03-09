import os
import sqlite3
from flask import Flask, request, jsonify

app = Flask(__name__)

# נתיב דינמי לקובץ בסיס הנתונים
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'leads_pro_ultimate.db')


def upgrade_db():
    """מכין את בסיס הנתונים: מוסיף עמודות חסרות ויוצר את טבלת המשימות"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 1. מוודא שעמודת issue_date קיימת בטבלת הלידים
        cursor.execute("PRAGMA table_info(leads)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'issue_date' not in columns:
            cursor.execute("ALTER TABLE leads ADD COLUMN issue_date TEXT")

        # 2. יוצר את טבלת המשימות (Tasks) עבור סעיף 7
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER,
                task_description TEXT,
                due_date TEXT,
                is_completed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (lead_id) REFERENCES leads (id)
            )
        ''')

        conn.commit()
        conn.close()
        print("DEBUG: Database upgrade completed successfully.")
    except Exception as e:
        print(f"DEBUG: Error during DB upgrade: {e}")


@app.route('/api/update_lead', methods=['POST'])
def update_lead():
    try:
        data = request.json
        full_name = data.get('full_name', '').strip()
        id_number = data.get('id_number', '').strip()
        issue_date = data.get('issue_date', '').strip()
        expiry_date = data.get('expiry_date', '').strip()

        if not full_name:
            return jsonify({"status": "error", "message": "Missing full_name"}), 400

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # חיפוש גמיש - האם הליד כבר קיים במערכת?
        cursor.execute('SELECT id FROM leads WHERE name LIKE ?', (f"%{full_name}%",))
        result = cursor.fetchone()

        if result:
            # אם הליד נמצא -> מעדכנים את הפרטים שלו
            lead_id = result[0]
            cursor.execute('''
                UPDATE leads 
                SET id_number = ?, issue_date = ?, expiry_date = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (id_number, issue_date, expiry_date, lead_id))
            action = "updated"
        else:
            # אם הליד לא נמצא -> יוצרים ליד חדש אוטומטית
            cursor.execute('''
                INSERT INTO leads (name, id_number, issue_date, expiry_date, status, source, created_at, updated_at) 
                VALUES (?, ?, ?, ?, 'חדש', 'OCR_Automation', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (full_name, id_number, issue_date, expiry_date))
            action = "created"

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "action": action, "name": full_name}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    upgrade_db()  # מריץ את שדרוג ה-DB לפני העלייה
    app.run(host='0.0.0.0', port=5000)