"""
Dịch vụ Logger để theo dõi hành động của người dùng
"""
import json
import logging
from flask import request, has_request_context
from config import get_db_connection

logger = logging.getLogger(__name__)

def log_action(username, action, success=True, details=None):
    """Ghi lại hành động của người dùng vào cơ sở dữ liệu"""
    try:
        db = get_db_connection()
        if not db: 
            return
        cur = db.cursor()
        
        # Kiểm tra xem chúng ta có đang trong ngữ cảnh request (request context) hay không
        if has_request_context():
            ip_address = request.remote_addr
            user_agent = request.user_agent.string if request.user_agent else "Unknown"
        else:
            # Đang chạy trong tiến trình nền (background task)
            ip_address = "System/Background"
            user_agent = "Server Worker"

        cur.execute(
            "INSERT INTO logs (username, action, ip_address, user_agent, success, details) VALUES (%s, %s, %s, %s, %s, %s)",
            (username, action, ip_address, user_agent, success, json.dumps(details) if details else None)
        )
        db.commit()
        cur.close()
        db.close()
    except Exception as e:
        # Sử dụng print thay vì logger để tránh lỗi đệ quy (vòng lặp vô hạn)
        print(f"LOG ACTION ERROR: {e}")
