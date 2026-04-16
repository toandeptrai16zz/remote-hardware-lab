import os
from config.database import get_db_connection

try:
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("UPDATE hardware_devices SET type = 'generic' WHERE port = '/dev/ttyUSB0'")
    db.commit()
    print("Updated hardware_devices to generic")
except Exception as e:
    print(f"Error: {e}")
