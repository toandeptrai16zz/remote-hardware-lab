"""
Các hàm Decorator để bảo vệ và xác thực các route
"""
import time
from functools import wraps
from flask import session, redirect, url_for, flash, request, jsonify
from config import SECURITY_CONFIG

def require_auth(role=None):
    """Decorator yêu cầu xác thực và tùy chọn yêu cầu một vai trò (role) cụ thể"""
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

def require_rate_limit(max_requests=10, window_seconds=60):
    """Decorator để giới hạn tần suất yêu cầu (rate limiting) - chặn các cuộc tấn công brute-force.
    Mặc định: 10 yêu cầu/phút trên mỗi IP.
    """
    from collections import defaultdict
    _rate_store = defaultdict(list)
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr or 'unknown'
            now = time.time()
            
            # Dọn dẹp các bản ghi yêu cầu cũ nằm ngoài cửa sổ thời gian
            _rate_store[ip] = [t for t in _rate_store[ip] if now - t < window_seconds]
            
            if len(_rate_store[ip]) >= max_requests:
                return jsonify(success=False, error=f'Quá nhiều yêu cầu. Vui lòng thử lại sau {window_seconds} giây.'), 429
            
            _rate_store[ip].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_internal_secret(f):
    """Decorator để xác thực mã bí mật (secret key) cho các sự kiện phần cứng từ API nội bộ"""
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
