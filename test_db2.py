import os
from config.database import get_db_connection

try:
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    print("Users:", [u['username'] for u in users])
    
    cur.execute("SELECT * FROM device_assignments")
    da = cur.fetchall()
    print("Assign:", da)
    
    username = users[0]['username']
    query = """
        SELECT hd.port
        FROM hardware_devices hd
        JOIN device_assignments da ON hd.id = da.device_id
        JOIN users u ON da.user_id = u.id
        WHERE u.username = %s AND hd.status != 'disconnected'
    """
    cur.execute(query, (username,))
    print("Ports for", username, ":", [row['port'] for row in cur.fetchall()])
    
except Exception as e:
    print(f"Error: {e}")
