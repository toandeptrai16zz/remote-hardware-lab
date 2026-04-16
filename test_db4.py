import os
from config.database import get_db_connection

try:
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    username = "toan ha"
    query = """
        SELECT hd.port, hd.status
        FROM hardware_devices hd
        JOIN device_assignments da ON hd.id = da.device_id
        JOIN users u ON da.user_id = u.id
        WHERE u.username = %s
    """
    cur.execute(query, (username,))
    print("Ports for", username, ":", [(row['port'], row['status']) for row in cur.fetchall()])
    
except Exception as e:
    print(f"Error: {e}")
