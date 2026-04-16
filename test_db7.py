import os
from config.database import get_db_connection

try:
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM hardware_devices")
    print(cur.fetchall())
except Exception as e:
    print(f"Error: {e}")
