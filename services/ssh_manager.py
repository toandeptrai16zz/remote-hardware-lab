"""
SSH connection management service
"""
import time
import paramiko
import logging
from utils import make_safe_name
from config import get_db_connection

logger = logging.getLogger(__name__)

def get_ssh_client(username_raw):
    """Get SSH client connection for a user's container"""
    # Get port using original username from DB
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT ssh_port FROM users WHERE username=%s", (username_raw,))
    user_data = cur.fetchone()
    cur.close()
    db.close()

    ssh_port = user_data.get("ssh_port") if user_data else None
    
    if not ssh_port:
        logger.error(f"DB search failed for port with username: '{username_raw}'")
        raise Exception("Không tìm thấy thông tin Port trong Database")

    # Connect SSH using safe username
    safe_username = make_safe_name(username_raw)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    for i in range(30):
        try:
            client.connect(
                '127.0.0.1', 
                port=int(ssh_port), 
                username=safe_username, 
                password='password123', 
                timeout=5
            ) 
            return client
        except Exception:
            time.sleep(1)
    
    raise Exception(f"KHONG THE KET NOI SSH TOI PORT {ssh_port} SAU 5 GIAY")
