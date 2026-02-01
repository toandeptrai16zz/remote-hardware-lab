"""
Decorator functions for route protection and validation
"""
import time
from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from config import SECURITY_CONFIG

def require_auth(role=None):
    """Decorator to require authentication and optionally a specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            is_api_request = request.is_json or request.path.startswith('/api/')

            if 'username' not in session:
                if is_api_request:
                    return jsonify(success=False, error='Phiên hết hạn. Vui lòng đăng nhập lại.'), 401
                flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
                return redirect(url_for('auth.login_page'))

            if 'last_activity' in session and time.time() - session['last_activity'] > SECURITY_CONFIG['SESSION_TIMEOUT']:
                session.clear()
                if is_api_request:
                    return jsonify(success=False, error='Phiên hết hạn. Vui lòng đăng nhập lại.'), 401
                flash('Phiên đăng nhập đã hết hạn', 'warning')
                return redirect(url_for('auth.login_page'))

            session['last_activity'] = time.time()

            if role and session.get('role') != role:
                if is_api_request:
                    return jsonify(success=False, error='Bạn không có quyền thực hiện hành động này.'), 403
                flash('Bạn không có quyền truy cập trang này.', 'error')
                return redirect(url_for('index'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_rate_limit(f):
    """Decorator for rate limiting (placeholder for future implementation)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Basic rate limiting logic can be added here
        return f(*args, **kwargs)
    return decorated_function

def require_internal_secret(f):
    """Decorator to validate internal API secret for hardware events"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from config import INTERNAL_API_SECRET
        from services.logger import log_action
        
        if request.headers.get('X-Internal-Secret') != INTERNAL_API_SECRET:
            log_action('internal_api', 'Unauthorized hardware event', success=False, 
                      details={'ip': request.remote_addr, 'reason': 'Invalid secret key'})
            return jsonify(success=False, error="Unauthorized - Invalid Secret Key"), 403
        return f(*args, **kwargs)
    return decorated_function
