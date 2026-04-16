import mysql.connector
from config.database import get_db_connection

try:
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("SELECT username FROM users LIMIT 1")
    user = cur.fetchall()
    print(f"User from DB: {user}")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'cur' in locals(): cur.close()
    if 'db' in locals() and db: db.close()
