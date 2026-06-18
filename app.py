"""
Hệ thống Quản lý IoT Lab - by Chương
Tệp tin khởi chạy chính - by Chương
"""
import eventlet
eventlet.monkey_patch()

import os
import secrets
import logging
from datetime import timedelta
from flask import Flask, session, redirect, url_for
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from prometheus_client import make_wsgi_app
from flask_socketio import SocketIO
from dotenv import load_dotenv
from utils.metrics import init_metrics

# Tải các biến môi trường - by Chương
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
load_dotenv(env_path)

# Khởi tạo DB - by Chương
from config import init_db

# Import các Blueprints điều hướng - by Chương
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.user import user_bp
from routes.flash import flash_bp

# Import trình xử lý Socket.IO - by Chương
from sockets import (
    register_realtime_handlers,
    register_terminal_handlers,
    register_serial_handlers,
    register_upload_status_handlers
)

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

# ================== KHỞI TẠO ỨNG DỤNG FLASK - by Chương ==================
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(24))

# ================== [BẢO MẬT] CẤU HÌNH SESSION & COOKIE ==================
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=4)
app.config['SESSION_COOKIE_HTTPONLY'] = True      # Chặn JavaScript truy cập Cookie (Chống XSS)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'     # Ngăn chặn tấn công CSRF
app.config['SESSION_COOKIE_SECURE'] = False        # Đặt thành True nếu triển khai trên HTTPS

# Tích hợp endpoint /metrics phục vụ cho hệ thống giám sát Prometheus/Grafana
init_metrics(app)
app.wsgi_app = DispatcherMiddleware(app.wsgi_app, {
    '/metrics': make_wsgi_app()
})

# Khởi chạy SocketIO với chế độ eventlet - by Chương
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# ================== ĐĂNG KÝ CÁC BLUEPRINTS - by Chương ==================
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
app.register_blueprint(flash_bp)

# ================== ĐĂNG KÝ CÁC TRÌNH XỬ LÝ SOCKET.IO - by Chương ==================
register_realtime_handlers(socketio)
register_terminal_handlers(socketio)
register_serial_handlers(socketio)
register_upload_status_handlers(socketio)

# ================== ĐỊNH TUYẾN TRANG CHỦ - by Chương ==================
@app.route("/")
def index():
    """Trang chủ điều hướng - chuyển hướng dựa trên vai trò của người dùng"""
    if "username" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        return redirect(url_for("user.user_redirect"))
    return redirect(url_for("auth.login_page"))

# ================== CÁC TRÌNH XỬ LÝ LỖI - by Chương ==================
@app.errorhandler(404)
def not_found(e):
    """Xử lý lỗi 404 - Không tìm thấy trang"""
    return "Không tìm thấy trang yêu cầu (404)", 404

@app.errorhandler(500)
def internal_error(e):
    """Xử lý lỗi 500 - Lỗi máy chủ nội bộ"""
    logger.error(f"Lỗi hệ thống: {e}")
    return "Lỗi máy chủ nội bộ (500)", 500

# ================== DỌN DẸP KHI THOÁT - by Chương ==================
def cleanup_on_exit(signum=None, frame=None):
    """Xử lý dọn dẹp để tắt ứng dụng một cách an toàn"""
    logger.info("🛑 Đang tắt ứng dụng...")
    logger.info("✅ Đã tắt ứng dụng hoàn tất")

# ================== KHỞI CHẠY CHÍNH - by Chương ==================

def print_banner():
    logger.info("=" * 60)
    logger.info("🚀 Hệ thống Quản lý IoT Lab - EPU Tech (Virtual Platform)")
    logger.info("=" * 60)

def main():
    """Điểm vào chính để khởi động ứng dụng"""
    print_banner()
    try:
        # Khởi tạo cơ sở dữ liệu
        init_db()
        from services.docker_manager import start_container_gc
        start_container_gc()
        # Vô hiệu hóa tính năng theo dõi USB vì đã chuyển sang kiến trúc Virtual AI
        logger.info("Các dịch vụ chạy nền theo dõi USB đã được vô hiệu hóa.")
        
        logger.info("✅ Khởi tạo ứng dụng thành công")
        logger.info("🌐 Server đang chạy tại địa chỉ http://[::]:5000")
        logger.info("=" * 60)
        
        # Chạy với SocketIO (Bật use_reloader=True để tự động cập nhật code mới)
        socketio.run(app, host="::", port=5000, debug=True, use_reloader=True)
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Nhận tín hiệu dừng từ bàn phím")
        cleanup_on_exit()
    except Exception as e:
        logger.error(f"❌ Lỗi nghiêm trọng: {e}")
        cleanup_on_exit()

if __name__ == "__main__":
    main()
