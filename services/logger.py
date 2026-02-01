"""
Logger service for tracking user actions
"""
import json
import logging
from flask import request, has_request_context
from config import get_db_connection

logger = logging.getLogger(__name__)

def log_action(username, action, success=True, details=None):
    """Log user action to database"""
    try:
        db = get_db_connection()
        if not db: 
            return
        cur = db.cursor()
        
        # Check if we're in a request context
        if has_request_context():
            ip_address = request.remote_addr
            user_agent = request.user_agent.string if request.user_agent else "Unknown"
        else:
            # Running in background task
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
        # Use print instead of logger to avoid recursion
        print(f"LOG ACTION ERROR: {e}")
