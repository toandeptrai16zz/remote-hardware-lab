"""
Hệ thống Quản lý IoT Lab - by Chương
Tệp tin khởi chạy chính - by Chương
"""
import eventlet
eventlet.monkey_patch()

import os
import secrets
import logging
import warnings
from urllib3.exceptions import InsecureRequestWarning
from flask import Flask, session, redirect, url_for
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app
from flask_socketio import SocketIO
from dotenv import load_dotenv

# Tải các biến môi trường - by Chương
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(env_path)

# Import các cấu hình - by Chương
from config import init_db

# Gọi các module điều hướng - by Chương
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.user import user_bp

# Gọi xử lý Socket - by Chương
from sockets import (
    register_terminal_handlers,
    register_serial_handlers,
    register_upload_status_handlers
)

# Mute request warnings - by Chương
# (đã xử lý bên trên) - by Chương

# Lấy đường dẫn JWT - by Chương

# Lấy JWT path
jwt_manager_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'venv', 'lib', 'python3.12', 'site-packages', 'flask_jwt_extended', 'jwt_manager.py')


# ================== CÀI ĐẶT LOGGING - by Chương ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ================== KHỞI TẠO APP - by Chương ==================
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(24))

# ================== [SECURITY HARDENING] SESSION & COOKIE ==================
from datetime import timedelta
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=4)
app.config['SESSION_COOKIE_HTTPONLY'] = True      # Chặn JS đọc Cookie (Anti-XSS)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'     # Chặn CSRF qua cross-site request
app.config['SESSION_COOKIE_SECURE'] = False        # True nếu dùng HTTPS

# Cọc endpoint /metrics phục vụ cho hệ thống giám sát Monitoring Kubernetes
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

# Khởi chạy SocketIO - by Chương
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ================== ĐĂNG KÝ BLUEPRINTS - by Chương ==================
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)

# ================== ĐĂNG KÝ SOCKET.IO HANDLERS - by Chương ==================
register_terminal_handlers(socketio)
register_serial_handlers(socketio)
register_upload_status_handlers(socketio)

# ================== ĐIỀU HƯỚNG CHÍNH - by Chương ==================
@app.route("/")
def index():
    """Main index route - redirect based on user role"""
    if "username" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        else:
            return redirect(url_for("user.user_redirect"))
    return redirect(url_for("auth.login_page"))

# ================== XỬ LÝ LỖI - by Chương ==================
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return "Page not found", 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal error: {e}")
    return "Internal server error", 500

# ================== DỊCH VỤ NGẦM - by Chương ==================
background_services = None

def cleanup_on_exit(signum=None, frame=None):
    """Cleanup handler for graceful shutdown"""
    logger.info("🛑 Shutting down application...")

    # Stop background services (Disabled logic)
    # if 'background_services' in globals() and background_services:
    #     stop_background_services()

    logger.info("✅ Application shutdown complete")


# Register signal handlers for graceful shutdown
# signal.signal(signal.SIGINT, cleanup_on_exit) # Removed as signal import is gone
# signal.signal(signal.SIGTERM, cleanup_on_exit) # Removed as signal import is gone

# ================== THỰC THI CHÍNH - by Chương ==================

def print_banner():
    logger.info("=" * 60)
    logger.info("🚀 EPU Tech IoT Lab Management System")
    logger.info("=" * 60)

def main():
    """Main entry point for starting the application"""
    print_banner()
    try:
        # Initialize database
        init_db()
        # Removed USB watcher for Virtual Assessment architecture
        logger.info("🔧 Background services tracking USB disabled for Virtual AI assessment.")
        background_services = None
        
        logger.info("✅ Application initialization complete")
        logger.info("🌐 Server running on http://[::]:5000")
        logger.info("=" * 60)
        
        # Run with SocketIO
        socketio.run(app, host="::", port=5000, debug=True, use_reloader=False)
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Received keyboard interrupt")
        cleanup_on_exit()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        cleanup_on_exit()

if __name__ == "__main__":
    main()
