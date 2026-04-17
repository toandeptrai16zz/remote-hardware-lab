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
from utils.metrics import init_metrics, FLASH_QUEUE_DEPTH, USB_DEVICE_STATUS, ACTIVE_CONTAINERS

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

# Import trình xử lý Socket.IO - by Chương
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

# ================== KHỞI TẠO ỨNG DỤNG FLASK - by Chương ==================
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(24))

# ================== [BẢO MẬT] CẤU HÌNH SESSION & COOKIE ==================
from datetime import timedelta
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

# ================== ĐĂNG KÝ CÁC TRÌNH XỬ LÝ SOCKET.IO - by Chương ==================
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
@app.route("/api/flash", methods=["POST"])
def flash_test_real_api():
    """
    [NCKH] API Flash đồng bộ dành riêng cho kiểm thử tải 300 SV - by Chương
    Tích hợp Smart Routing thật sự từ services/arduino
    """
    from flask import request
    import time, random
    from services.arduino import get_user_assigned_device, FLASH_QUEUE_DEPTH, USB_DEVICE_STATUS
    from utils.metrics import ACTIVE_CONTAINERS

    data = request.json or {}
    board_type = data.get('board_type', 'ESP32')
    
    # 1. Gọi Smart Routing thực tế (Giả lập username để lấy quyền thiết bị)
    assigned = get_user_assigned_device("ha quang chuong", reserve=True)
    if not assigned:
        return {"success": False, "error": "No available hardware ports"}, 503
    
    port = assigned['port']
    
    try:
        # 2. Cập nhật Metrics rực rỡ lên Grafana
        ACTIVE_CONTAINERS.inc()
        USB_DEVICE_STATUS.labels(port=port).set(2) # In Use
        # Lưu ý: FLASH_QUEUE_DEPTH đã được tăng bên trong get_user_assigned_device(reserve=True)
        
        # 3. Giả lập thời gian nạp code vật lý thực tế
        delay = random.uniform(3.8, 4.3)
        time.sleep(delay)
        
        return {"success": True, "port": port, "delay": delay}
    finally:
        # 4. Giải phóng hàng đợi và trả trạng thái về Available
        from services.arduino import queue_counts
        queue_counts[port] = max(0, queue_counts[port] - 1)
        FLASH_QUEUE_DEPTH.labels(port=port).set(queue_counts[port])
        
        if queue_counts[port] == 0:
            USB_DEVICE_STATUS.labels(port=port).set(1) # Available
        
        ACTIVE_CONTAINERS.dec()

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
background_services = None

def cleanup_on_exit(signum=None, frame=None):
    """Xử lý dọn dẹp để tắt ứng dụng một cách an toàn"""
    logger.info("🛑 Đang tắt ứng dụng...")

    # Dừng các dịch vụ chạy nền (Logic này hiện đã được vô hiệu hóa)
    # if 'background_services' in globals() and background_services:
    #     stop_background_services()

    logger.info("✅ Đã tắt ứng dụng hoàn tất")


# Đăng ký các trình xử lý tín hiệu để tắt ứng dụng an toàn
# signal.signal(signal.SIGINT, cleanup_on_exit) # Đã gỡ bỏ vì import signal không còn dùng
# signal.signal(signal.SIGTERM, cleanup_on_exit) # Đã gỡ bỏ vì import signal không còn dùng

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
        # Vô hiệu hóa tính năng theo dõi USB vì đã chuyển sang kiến trúc Virtual AI
        logger.info("🔧 Các dịch vụ chạy nền theo dõi USB đã được vô hiệu hóa.")
        background_services = None
        
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
