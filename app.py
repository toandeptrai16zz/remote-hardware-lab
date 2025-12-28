# ================== IMPORTS ==================
import os
import docker
import secrets
import time
import requests
import random
import socket
import subprocess
import logging
import stat
import shutil
import base64
import re
import json
import smtplib
import glob
import threading
from math import ceil
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from functools import wraps
from collections import defaultdict
from werkzeug.utils import secure_filename
import string
import serial
import sys
import shlex
import serial.tools.list_ports 
from collections import defaultdict
from flask import has_request_context
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, emit
import mysql.connector
import paramiko
from werkzeug.security import generate_password_hash, check_password_hash

# List of default Arduino libraries to pre-install for all users.
# You can add or remove library names here. Use the name that you would
# use with "arduino-cli lib install".
DEFAULT_ARDUINO_LIBRARIES = [
    "Adafruit NeoPixel", "DHT sensor library", "Adafruit Unified Sensor", "PubSubClient", "ArduinoJson"
]

# ================== APP SETUP ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler('app.log'), logging.StreamHandler()]
)
app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app, cors_allowed_origins="*")

# ================== CONFIGURATIONS ==================
SECURITY_CONFIG = {
    'MAX_LOGIN_ATTEMPTS': 5, 'LOCKOUT_DURATION': 300, 'OTP_EXPIRY': 300,
    'SESSION_TIMEOUT': 1800, 'CSRF_EXPIRY': 3600, 'PASSWORD_MIN_LENGTH': 8,
    'USERNAME_MIN_LENGTH': 3, 'RATE_LIMIT_PER_MINUTE': 60,
}
EMAIL_CONFIG = {
    'SMTP_SERVER': 'smtp.gmail.com', 'SMTP_PORT': 587,
    'SMTP_USERNAME': 'haquangchuong28@gmail.com',
    'SMTP_PASSWORD': 'ctuo nyxx clvg xxtc',
    'FROM_EMAIL': 'EPU TECH'
}

# ================== IN-MEMORY STORAGE ==================
login_attempts = defaultdict(lambda: {'count': 0, 'locked_until': None})
otp_storage = {}
csrf_tokens = {}
rate_limiter = defaultdict(lambda: {'requests': [], 'blocked_until': None})

device_locks = defaultdict(threading.Lock)
user_sids = {} # Lưu session ID của user cho Socket.IO

# ================== SECURITY UTILITIES ==================
def generate_csrf_token():
    token = secrets.token_urlsafe(32)
    csrf_tokens[token] = {'created_at': time.time(), 'user_ip': request.remote_addr if request else None}
    expired = [t for t, data in list(csrf_tokens.items()) if time.time() - data['created_at'] > SECURITY_CONFIG['CSRF_EXPIRY']]
    for t in expired: del csrf_tokens[t]
    return token

def validate_csrf_token(token):
    if not token or token not in csrf_tokens: return False
    if time.time() - csrf_tokens[token]['created_at'] > SECURITY_CONFIG['CSRF_EXPIRY']:
        del csrf_tokens[token]
        return False
    return True

def generate_captcha():
    chars = string.digits + string.ascii_lowercase + string.ascii_uppercase
    captcha = ''.join(random.choices(chars, k=6))
    token = base64.b64encode(f"{captcha}:{time.time()}".encode()).decode()
    return captcha, token

def validate_captcha(user_input, token):
    try:
        decoded = base64.b64decode(token.encode()).decode()
        captcha, timestamp = decoded.split(':', 1)
        if time.time() - float(timestamp) > 300: return False
        return user_input.upper() == captcha.upper()
    except: return False

def generate_otp(): return ''.join(random.choices('0123456789', k=6))

def send_otp_email(email, otp, username):
    try:
        msg = MIMEMultipart()
        msg['From'], msg['To'], msg['Subject'] = EMAIL_CONFIG['FROM_EMAIL'], email, "EPU Tech - Mã xác thực"
        body = f"Xin chào {username},\n\nMã xác thực của bạn là: {otp}\n\nMã này có hiệu lực trong 5 phút."
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        server = smtplib.SMTP(EMAIL_CONFIG['SMTP_SERVER'], EMAIL_CONFIG['SMTP_PORT'])
        server.starttls()
        server.login(EMAIL_CONFIG['SMTP_USERNAME'], EMAIL_CONFIG['SMTP_PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        app.logger.error(f"EMAIL SEND ERROR: {e}")
        return False

def validate_password_strength(password):
    if len(password) < SECURITY_CONFIG['PASSWORD_MIN_LENGTH']: return False, "Mật khẩu phải dài ít nhất 8 ký tự"
    if not re.search("[a-z]", password): return False, "Mật khẩu phải chứa chữ thường"
    if not re.search("[A-Z]", password): return False, "Mật khẩu phải chứa chữ HOA"
    if not re.search("[0-9]", password): return False, "Mật khẩu phải chứa số"
    return True, ""

# ================== DECORATORS ==================
def require_auth(role=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            is_api_request = request.is_json or request.path.startswith('/api/')

            if 'username' not in session:
                if is_api_request:
                    return jsonify(success=False, error='Phiên hết hạn. Vui lòng đăng nhập lại.'), 401
                flash('Vui lòng đăng nhập để tiếp tục.', 'warning')
                return redirect(url_for('login_page'))

            if 'last_activity' in session and time.time() - session['last_activity'] > SECURITY_CONFIG['SESSION_TIMEOUT']:
                session.clear()
                if is_api_request:
                    return jsonify(success=False, error='Phiên hết hạn. Vui lòng đăng nhập lại.'), 401
                flash('Phiên đăng nhập đã hết hạn', 'warning')
                return redirect(url_for('login_page'))

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
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Basic rate limiting logic can be added here
        return f(*args, **kwargs)
    return decorated_function

# ================== DATABASE & DOCKER HELPERS ==================
def get_db_connection():
    try:
        db_user = os.getenv('DB_USER', 'chuongdev_admin')
        db_password = os.getenv('DB_PASSWORD', 'Chuong2004@')
        db_database = os.getenv('DB_DATABASE', 'flask_app')
        db_host = os.getenv('DB_HOST', 'localhost')

        return mysql.connector.connect(
            host=db_host, 
            user=db_user, 
            password=db_password, 
            database=db_database, 
            autocommit=True
        )
    except Exception as e:
        app.logger.error(f"DATABASE CONNECTION ERROR: {e}")
        return None

def init_db():
    db = get_db_connection()
    if not db: return
    cur = db.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) NOT NULL UNIQUE, password VARCHAR(255) NOT NULL, email VARCHAR(255) NULL UNIQUE, role ENUM('admin','user') NOT NULL DEFAULT 'user', status ENUM('pending','active','blocked') NOT NULL DEFAULT 'pending', ssh_port INT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, last_login TIMESTAMP NULL);")
    cur.execute("CREATE TABLE IF NOT EXISTS hardware_devices (id INT AUTO_INCREMENT PRIMARY KEY, tag_name VARCHAR(100) NOT NULL UNIQUE, type VARCHAR(100) NOT NULL, port VARCHAR(100) NOT NULL UNIQUE, status ENUM('available', 'in_use', 'maintenance') NOT NULL DEFAULT 'available', in_use_by VARCHAR(50) NULL, FOREIGN KEY (in_use_by) REFERENCES users(username) ON DELETE SET NULL);")
    cur.execute("CREATE TABLE IF NOT EXISTS logs (id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(50) NOT NULL, action VARCHAR(255) NOT NULL, timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, ip_address VARCHAR(45) NULL, user_agent TEXT NULL, success BOOLEAN DEFAULT TRUE, details JSON NULL);")
    cur.execute("CREATE TABLE IF NOT EXISTS device_assignments (id INT AUTO_INCREMENT PRIMARY KEY, user_id INT NOT NULL, device_id INT NOT NULL, assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, expires_at TIMESTAMP NULL, FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE, FOREIGN KEY (device_id) REFERENCES hardware_devices(id) ON DELETE CASCADE, UNIQUE KEY (user_id, device_id));")
    cur.execute("SELECT id FROM users WHERE username='admin'")
    if not cur.fetchone():
        hashed_password = generate_password_hash('admin123@')
        cur.execute("INSERT INTO users (username, password, email, role, status) VALUES (%s, %s, %s, %s, %s)", ('admin', hashed_password, 'admin@eputech.com', 'admin', 'active'))
        app.logger.info("Created default admin user")
    db.commit()
    cur.close()
    db.close()

def log_action(username, action, success=True, details=None):
    try:
        db = get_db_connection()
        if not db: return
        cur = db.cursor()
        
        # --- FIX LỖI CONTEXT: Kiểm tra xem có đang trong request HTTP không ---
        if has_request_context():
            ip_address = request.remote_addr
            user_agent = request.user_agent.string if request.user_agent else "Unknown"
        else:
            # Nếu đang chạy ngầm (background task), dùng giá trị mặc định
            ip_address = "System/Background"
            user_agent = "Server Worker"
        # ---------------------------------------------------------------------

        cur.execute("INSERT INTO logs (username, action, ip_address, user_agent, success, details) VALUES (%s, %s, %s, %s, %s, %s)",
                    (username, action, ip_address, user_agent, success, json.dumps(details) if details else None))
        db.commit()
        cur.close()
        db.close()
    except Exception as e:
        # In lỗi ra màn hình console thay vì dùng app.logger để tránh đệ quy lỗi
        print(f"LOG ACTION ERROR: {e}")

#Ham Xu ly sai du ten docker va SSH
def make_safe_name(input_string):
    if not input_string:
        return ""
    return re.sub(r'[^a-zA-Z0-9_-]', '_', input_string)
# === Ham Check duong dan path an toan chong hack
def is_safe_path(basedir, path):
    # Resolve đường dẫn tuyệt đối
    # Loại bỏ dấu / ở đầu input để os.path.join hoạt động đúng
    if path.startswith('/'): path = path.lstrip('/')
    target = os.path.abspath(os.path.join(basedir, path))
    return target.startswith(os.path.abspath(basedir))

def find_free_port(start=2200, end=2299):
    for _ in range(100):
        port = random.randint(start, end)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return None

def docker_status(cname):
    try:
        r = subprocess.run(["docker", "inspect", "-f", "{{.State.Status}}", cname], capture_output=True, text=True, check=False, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""

# --- KET THUC HAM ---
def _perform_upload_worker(username, sid, sketch_path, board_fqbn, port):
    """
    Hàm xử lý nạp code với chế độ Streaming Log (Real-time).
    """
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    full_path = os.path.normpath(f"/home/{safe_username}/{sketch_path}")
    
    # 1. Thông báo đã vào hàng đợi
    socketio.emit('upload_status', {
        'status': 'queued', 
        'message': f'Yêu cầu nạp code vào {port} đã được tiếp nhận.'
    }, namespace='/upload_status', room=sid)

    try:
        # --- GIAI ĐOẠN 1: BIÊN DỊCH (Vẫn dùng run để gom log gọn) ---
        socketio.emit('upload_status', {
            'status': 'compiling', 
            'message': f'Đang biên dịch chương trình...'
        }, namespace='/upload_status', room=sid)

        app.logger.info(f"User {safe_username} compiling {sketch_path}...")
        
        compile_cmd = ["docker", "exec", cname, "arduino-cli", "compile", "--fqbn", board_fqbn, full_path]
        compile_res = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=180)

        if compile_res.returncode != 0:
            raise Exception("Biên dịch thất bại:\n" + compile_res.stdout + "\n" + compile_res.stderr)
        
        # --- GIAI ĐOẠN 2: NẠP CODE (STREAMING LOG) ---
        socketio.emit('upload_status', {
            'status': 'uploading', 
            'message': f'Biên dịch xong. Đang kết nối cổng {port}...'
        }, namespace='/upload_status', room=sid)

        app.logger.info(f"User {safe_username} waiting for lock on {port}...")
        
        with device_locks[port]:
            app.logger.info(f"User {safe_username} acquired lock. Starting upload stream.")
            
            upload_cmd = ["docker", "exec", cname, "arduino-cli", "upload", "-p", port, "--fqbn", board_fqbn, full_path]
            
            # Dùng Popen thay vì run để đọc log từng dòng (Real-time)
            process = subprocess.Popen(
                upload_cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, # Gom lỗi vào chung output để hiển thị
                text=True,
                bufsize=1 # Line buffered
            )

            # Vòng lặp đọc log và gửi về client ngay lập tức
            for line in iter(process.stdout.readline, ''):
                if line:
                    # Gửi từng dòng log về web (trạng thái vẫn là uploading)
                    socketio.emit('upload_status', {
                        'status': 'uploading', 
                        'message': 'Đang nạp code...', # Frontend có thể hiển thị hoặc không
                        'output': line # Dòng log hiện tại (ví dụ: Writing at 0x000...)
                    }, namespace='/upload_status', room=sid)
            
            process.stdout.close()
            return_code = process.wait()

            if return_code != 0:
                raise Exception("Quá trình nạp bị lỗi (Exit code khác 0).")

            # --- GIAI ĐOẠN 3: HOÀN TẤT ---
            # Chỉ khi vòng lặp trên chạy xong hết mới gửi Success
            log_action(username, f"Upload success: {sketch_path}", success=True)
            
            socketio.emit('upload_status', {
                'status': 'success', 
                'message': '✓ Nạp chương trình thành công!',
                'output': '\nDone.\n'
            }, namespace='/upload_status', room=sid)
            
            app.logger.info(f"User {safe_username} upload finished.")

    except Exception as e:
        error_msg = str(e)
        app.logger.error(f"Upload process failed: {error_msg}")
        log_action(username, f"Upload failed: {sketch_path}", success=False, details={"error": error_msg})
        socketio.emit('upload_status', {
            'status': 'error', 
            'message': '✗ Quá trình thất bại!',
            'output': f"\nLỗi chi tiết:\n{error_msg}\n"
        }, namespace='/upload_status', room=sid)
    
    finally:
        app.logger.info(f"Lock released for {port}.")
# --- KET THUC HAM ^^ ---
# SỬA FUNCTION ensure_user_container
#Cap nhat ham ensure_user de khong can set up cac board khi cac user duoc tao 
def ensure_user_container(username):
    # 1. Chuẩn hóa tên User & Cấu hình
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    image = "my-dev-env:v2"
    
    # 2. Database logic: Lấy hoặc tạo Port mới
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT ssh_port FROM users WHERE username=%s", (username,))
    user_data = cur.fetchone()
    ssh_port = user_data.get("ssh_port") if user_data else None
    
    if not ssh_port:
        ssh_port = find_free_port()
        cur.execute("UPDATE users SET ssh_port=%s WHERE username=%s", (ssh_port, username))
        db.commit()
    cur.close()
    db.close()

    # 3. Chuẩn bị thư mục trên Host
    host_user_dir = f"/home/toan/QUAN_LY_USER/{safe_username}"
    os.makedirs(host_user_dir, exist_ok=True)
    os.chmod(host_user_dir, 0o777)

    # ==================================================================
    # [FINAL SCRIPT] COMMIT 3th by CHUONG
    # ==================================================================
    setup_script_path = os.path.join(host_user_dir, "setup_container.sh")
    
    script_content = f"""#!/bin/bash
USER="{safe_username}"

# --- A. CÀI SERIAL & PIP (CHẠY NGẦM KHÔNG CHẶN SSH) ---
(
    echo "[$(date)] Kiem tra va cai dat thu vien..." > /var/log/setup_pyserial.log
    # Kiểm tra xem đã có serial chưa, nếu chưa thì cài
    if ! python3 -c "import serial" &>/dev/null; then
        # Cố gắng dùng APT trước cho nhanh
        apt-get update -y &>/dev/null
        apt-get install -y python3-serial python3-pip &>/dev/null
        # Dùng PIP dự phòng
        pip3 install pyserial esptool --break-system-packages &>/dev/null || pip3 install pyserial esptool &>/dev/null
    fi
    echo "[$(date)] Da cai xong hoac da co thu vien." >> /var/log/setup_pyserial.log
) &

# --- B. TẠO USER & PASS ---
if ! id "$USER" &>/dev/null; then
    echo "Creating user $USER..."
    useradd -m -s /bin/bash "$USER"
    echo "$USER:password123" | chpasswd
    usermod -aG dialout "$USER" || true
    usermod -aG sudo "$USER" || true
fi

# --- C. FIX LỖI SFTP (GARBAGE PACKET) ---
# Ghi đè file cấu hình sạch sẽ
cat > /home/"$USER"/.bashrc << 'EOF_BASHRC'
# .bashrc for EPU Workspace
# Nếu không phải Terminal (ví dụ SFTP), thoát ngay để tránh rác
case $- in
    *i*) ;;
      *) return;;
esac

export PATH="/usr/local/bin:$PATH"
alias ll='ls -alF'
alias cls='clear'

# Hiện Welcome khi mở Terminal
clear
if [ -f ~/WELCOME.txt ]; then
    cat ~/WELCOME.txt
fi
EOF_BASHRC

# --- D. TẠO WELCOME ---
cat > /home/"$USER"/WELCOME.txt << EOF
================================================================
HE THONG THUC HANH IOT - EPU TECH
================================================================
[+] USER: $USER
[+] TRANG THAI: SAN SANG (Connected)
[+] MANG: Keep-Alive Enabled (Chong rot mang)

[!] Neu nap code loi 'No module named serial', 
    vui long doi 1 phut hoac go: pip3 install pyserial
================================================================
EOF
chown -R "$USER:$USER" /home/"$USER"

# --- E. CẤU HÌNH SSH CHỐNG DISCONNECT ---
mkdir -p /run/sshd
# Thêm cấu hình giữ kết nối cho mạng yếu/Ngrok
echo "ClientAliveInterval 30" >> /etc/ssh/sshd_config
echo "ClientAliveCountMax 100" >> /etc/ssh/sshd_config
echo "TCPKeepAlive yes" >> /etc/ssh/sshd_config

# --- F. KHỞI ĐỘNG SSH ---
echo "Starting SSH Daemon..."
exec /usr/sbin/sshd -D
"""
    # Ghi file script ra ổ cứng
    with open(setup_script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    os.chmod(setup_script_path, 0o777)

    # ==================================================================
    # KHỞI ĐỘNG CONTAINER
    # ==================================================================
    status = docker_status(cname)
    if status == 'running':
        subprocess.run(["docker", "exec", cname, "service", "ssh", "start"], check=False)
        return ssh_port
    
    # Nếu container lỗi hoặc đã tắt, xóa đi tạo lại để nhận script mới
    if status:
        subprocess.run(["docker", "rm", "-f", cname], check=False)

    app.logger.info(f"Starting container {cname} with final script...")
    
    docker_command = [
        "docker", "run", "-d", 
        "--name", cname, 
        "--restart", "unless-stopped",
        "--privileged",  
        "-p", f"{ssh_port}:22", 
        "-e", f"USERNAME={safe_username}", 
        "-v", f"{host_user_dir}:/home/{safe_username}",
        "-v", f"{setup_script_path}:/startup.sh",
        "-v", "/home/toan/flask-kerberos-demo/esp32_core:/root/.arduino15",
        "-v", "/dev:/dev",
        "--group-add", "dialout", 
        "--entrypoint", "/bin/bash",
        image,
        "/startup.sh"
    ]
    
    try:
        subprocess.run(docker_command, check=True, timeout=30)
        # Đợi 3s cho script kịp khởi động SSH
        time.sleep(3)
        
        # Dọn dẹp file script sau khi chạy xong
        if os.path.exists(setup_script_path):
             os.remove(setup_script_path)
             
    except Exception as e:
        app.logger.error(f"Error starting container: {e}")

    return ssh_port
# --- KET THUC HAM ^^ ---

# THÊM FUNCITON MOI

def setup_container_permissions(cname, username):
    """Setup quyền truy cập serial devices trong container"""
    try:
        # Thêm user vào group dialout trong container
        cmd = ["docker", "exec", cname, "usermod", "-a", "-G", "dialout", username]
        subprocess.run(cmd, check=True, timeout=10)
        
        # Set quyền cho /dev/tty* devices
        cmd = ["docker", "exec", cname, "sh", "-c", "chmod 666 /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true"]
        subprocess.run(cmd, check=True, timeout=10)
        
        app.logger.info(f"Setup permissions for container {cname}")
    except Exception as e:
        app.logger.error(f"Failed to setup permissions for {cname}: {e}")

# --- KET THUC HAM ---
@app.route('/user/<username>/serial-ports', methods=['GET'])
@require_auth('user')
def get_serial_ports_api(username):
    if session['username'] != username:
        return jsonify(error="Unauthorized"), 403
    
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"

    try:
        # BƯỚC 1: CẤP QUYỀN (Để chắc chắn Docker đọc được USB)
        subprocess.run(["docker", "exec", "--user", "root", cname, "sh", "-c", "chmod 666 /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true"], check=False, timeout=5)

        # BƯỚC 2: QUÉT CƠ BẢN BẰNG ARDUINO-CLI
        # (Lấy danh sách cổng trước, chưa cần tin tên thiết bị vội)
        scan_cmd = ["docker", "exec", cname, "arduino-cli", "board", "list", "--format", "json"]
        scan_result = subprocess.run(scan_cmd, capture_output=True, text=True, timeout=10)
        
        container_ports = []
        
        if scan_result.returncode == 0:
            try:
                data = json.loads(scan_result.stdout)
                # Xử lý cấu trúc JSON linh hoạt
                items_list = []
                if isinstance(data, list): items_list = data
                elif isinstance(data, dict) and "detected_ports" in data: items_list = data["detected_ports"]

                for item in items_list:
                    # Lấy thông tin cổng cơ bản
                    port_info = item.get('port', item)
                    if isinstance(port_info, dict) and port_info.get("protocol") == "serial":
                        port_address = port_info.get("address")
                        
                        # --- [SMART SCAN] BẮT ĐẦU THUẬT TOÁN ĐỌC CHIP ID ---
                        # Mặc định lấy tên từ Arduino CLI
                        boards = []
                        is_smart_detected = False
                        
                        # Chỉ chạy Smart Scan với các cổng USB (tránh ttyS0...)
                        if "USB" in port_address:
                            try:
                                # Chạy esptool để hỏi Chip ID (Timeout 2s để không bị treo)
                                # Lưu ý: Container cần có esptool (đã cài qua pip pyserial/esptool hoặc có sẵn trong core)
                                # Ta thử gọi python3 -m esptool vì nó ổn định hơn gọi thẳng lệnh
                                chip_cmd = ["docker", "exec", cname, "python3", "-m", "esptool", "--port", port_address, "chip_id"]
                                chip_res = subprocess.run(chip_cmd, capture_output=True, text=True, timeout=3)
                                output = chip_res.stdout

                                if "ESP32" in output:
                                    # PHÁT HIỆN ESP32 (Gán cứng là ESP32-CAM AI Thinker cho bác)
                                    boards = [{"name": "AI Thinker ESP32-CAM (Auto-Detected)", "fqbn": "esp32:esp32:esp32cam"}]
                                    is_smart_detected = True
                                elif "ESP8266" in output:
                                    # PHÁT HIỆN ESP8266
                                    boards = [{"name": "NodeMCU ESP8266 (Auto-Detected)", "fqbn": "esp8266:esp8266:nodemcuv2"}]
                                    is_smart_detected = True
                                
                            except Exception:
                                # Nếu Smart Scan lỗi (do cổng bận hoặc không phải ESP), bỏ qua
                                pass

                        # Nếu Smart Scan không ra gì, dùng lại logic cũ của Arduino CLI
                        if not is_smart_detected:
                            boards_data = item.get("boards", port_info.get("boards", []))
                            if isinstance(boards_data, list) and boards_data:
                                for b in boards_data:
                                    boards.append({"name": b.get("name", "Unknown"), "fqbn": b.get("fqbn", "")})
                            else:
                                # Fallback nếu CLI không nhận ra (Generic CH340)
                                if "USB" in port_address:
                                    boards = [
                                        {"name": "Generic ESP8266 (NodeMCU)", "fqbn": "esp8266:esp8266:nodemcuv2"},
                                        {"name": "Generic ESP32 Dev Module", "fqbn": "esp32:esp32:esp32"},
                                        {"name": "Arduino Uno", "fqbn": "arduino:avr:uno"}
                                    ]
                                else:
                                    boards = [{"name": "Serial Device", "fqbn": ""}]

                        container_ports.append({
                            "port": {"address": port_address, "label": port_address, "protocol": "serial"},
                            "matching_boards": boards
                        })

            except json.JSONDecodeError:
                app.logger.error(f"Error decoding json for {safe_username}")
            except Exception as e:
                app.logger.error(f"Error parsing port logic: {e}")

        # BƯỚC 3: FALLBACK (DÙNG LS NẾU ARDUINO-CLI TRẢ VỀ RỖNG)
        if not container_ports:
            fallback_cmd = ["docker", "exec", cname, "sh", "-c", "ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null"]
            fallback_res = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=5)
            if fallback_res.returncode == 0 and fallback_res.stdout.strip():
                for line in fallback_res.stdout.strip().split('\n'):
                    line = line.strip()
                    if line:
                        # Mặc định fallback cũng ưu tiên ESP32-CAM cho bác đỡ phải chọn
                        container_ports.append({
                            "port": {"address": line, "label": line, "protocol": "serial"},
                            "matching_boards": [
                                {"name": "AI Thinker ESP32-CAM (Default)", "fqbn": "esp32:esp32:esp32cam"},
                                {"name": "Generic ESP8266", "fqbn": "esp8266:esp8266:nodemcuv2"}
                            ]
                        })

        log_action(username, f"Smart Scan: Found {len(container_ports)} ports")
        return jsonify(success=True, ports=container_ports, message=f"Tìm thấy {len(container_ports)} cổng.")

    except Exception as e:
        app.logger.error(f"Serial ports API error for {safe_username}: {e}")
        return jsonify(success=False, error=str(e)), 500
# --- KET THUC HAM ^^ ---
# Ket thuc ham
    
platform_cache = {}
# ---SET UP MOI TRUONG THU VIEN CHO USERS ---
def setup_arduino_cli_for_user(cname, username):
    """Sets up arduino-cli with necessary board URLs and cores."""
    app.logger.info(f"Setting up Arduino CLI for container '{cname}'...")
    try:
        # A short delay to ensure the container's services are fully up.
        time.sleep(5)

        urls = [
            "http://arduino.esp8266.com/stable/package_esp8266com_index.json",
            "https://dl.espressif.com/dl/package_esp32_index.json"
        ]

        # 1. Set board manager URLs
        # The key and values must be separate arguments for arduino-cli
        config_cmd = ["docker", "exec", cname, "arduino-cli", "config", "set", "board_manager.additional_urls"] + urls
        subprocess.run(config_cmd, check=True, capture_output=True, text=True, timeout=60)
        app.logger.info(f"Set board manager URLs for '{cname}'.")

        # 2. Update index
        update_cmd = ["docker", "exec", cname, "arduino-cli", "core", "update-index"]
        subprocess.run(update_cmd, check=True, capture_output=True, text=True, timeout=120)
        app.logger.info(f"Updated core index for '{cname}'.")

        # 3. Install cores
        for core in ["esp8266:esp8266", "esp32:esp32"]:
            app.logger.info(f"Installing {core} core for '{cname}'...")
            install_cmd = ["docker", "exec", cname, "arduino-cli", "core", "install", core]
            subprocess.run(install_cmd, check=True, capture_output=True, text=True, timeout=300)
            app.logger.info(f"Installed {core} core for '{cname}'.")

        # 4. Install common libraries
        app.logger.info(f"Installing default libraries for '{cname}'...")
        for lib in DEFAULT_ARDUINO_LIBRARIES:
            app.logger.info(f"Installing library: {lib} for {cname}")
            lib_install_cmd = ["docker", "exec", cname, "arduino-cli", "lib", "install", lib]
            result = subprocess.run(lib_install_cmd, capture_output=True, text=True, timeout=180)
            if result.returncode != 0:
                # Log as warning because sometimes it returns non-zero for already installed dependencies
                app.logger.warning(f"Could not install library '{lib}' for '{cname}'. Output:\n{result.stdout}\n{result.stderr}")
            else:
                app.logger.info(f"Successfully installed or verified library '{lib}'.")

        log_action(username, "Arduino CLI setup complete")
    except Exception as e:
        error_output = e.stderr if hasattr(e, 'stderr') else str(e)
        app.logger.error(f"Failed to setup Arduino CLI for '{cname}': {error_output}")
        log_action(username, "Arduino CLI setup failed", success=False, details={"error": error_output})
def check_platform_installed(cname, platform_id):
    cache_key = f"{cname}_{platform_id}"
    
    # Check cache (valid 1 giờ)
    if cache_key in platform_cache:
        cached_time, cached_result = platform_cache[cache_key]
        if time.time() - cached_time < 3600:  # 1 giờ
            app.logger.info(f"Using cached result for {platform_id} in {cname}: {cached_result}")
            return cached_result
    
    app.logger.info(f"Checking for platform '{platform_id}' in container '{cname}'...")
    try:
        cmd = ["docker", "exec", cname, "arduino-cli", "core", "list"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            is_installed = platform_id in result.stdout
        else:
            # Command failed, assume installed để tránh loop
            is_installed = True
            
        platform_cache[cache_key] = (time.time(), is_installed)
        return is_installed
        
    except subprocess.TimeoutExpired:
        app.logger.warning(f"Timeout checking {platform_id} for {cname}, assuming installed")
        platform_cache[cache_key] = (time.time(), True)
        return True
        
    except Exception as e:
        app.logger.error(f"Error checking platform: {e}")
        platform_cache[cache_key] = (time.time(), True)
        return True

# HAM DIEU PHOI TOAN BO MOI TRUONG CHO USER
def ensure_user_container_and_setup(username):
    safe_username = make_safe_name(username) 
    cname = f"{safe_username}-dev"
    
    # 1. Đảm bảo Container ĐANG CHẠY (Gọi hàm con)
    ssh_port = ensure_user_container(username) 

    # 2. Kiểm tra/Cài đặt nền tảng Arduino
    if not check_platform_installed(cname, "esp8266:esp8266"):
        try:
            setup_arduino_cli_for_user(cname, safe_username)
        except Exception as e:
            app.logger.error(f"Setup Arduino failed: {e}")
    
    return ssh_port

# KET THUC HAM
def get_ssh_client(username_raw):
    # 1. Lấy Port bằng tên GỐC (ví dụ: "sinh vien")
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT ssh_port FROM users WHERE username=%s", (username_raw,))
    user_data = cur.fetchone()
    cur.close()
    db.close()

    ssh_port = user_data.get("ssh_port") if user_data else None
    
    if not ssh_port:
        app.logger.error(f"DB search failed for port with username: '{username_raw}'")
        raise Exception("Không tìm thấy thông tin Port trong Database")

    # 2. Kết nối SSH dùng SAFE name (ví dụ: "sinh_vien")
    safe_username = make_safe_name(username_raw)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for i in range(5):
        try:
            # client = paramiko.SSHClient()
            # client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect('127.0.0.1', port=int(ssh_port), username=safe_username, password='password123', timeout=5) 
            return client
        except Exception:
            time.sleep(1)
    raise Exception(f"KHONG THE KET NOI SSH TOI PORT {ssh_port} SAU 5 GIAY")
# KET THUC HAM


# ================== AUTHENTICATION ROUTES ==================
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("admin_dashboard" if session.get("role") == "admin" else "user_redirect"))
    return redirect(url_for("login_page"))

@app.route("/api/generate-csrf", methods=["GET"])
def generate_csrf_api():
    return jsonify({'csrf_token': generate_csrf_token()})

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def login_api():
    # --- DEBUG LOG (Để soi lỗi) ---
    print(f"--- LOGIN REQUEST ---", file=sys.stderr)
    print(f"Content-Type: {request.content_type}", file=sys.stderr)
    
    # 1. Xác định nguồn dữ liệu (JSON hay Form)
    data = {}
    if request.is_json:
        print("Data Source: JSON", file=sys.stderr)
        data = request.get_json()
    else:
        print("Data Source: FORM", file=sys.stderr)
        data = request.form

    # 2. Lấy dữ liệu (An toàn)
    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()
    captcha = data.get("captcha", "").strip()
    captcha_token = data.get("captcha_token", "")
    csrf_token = data.get("csrf_token", "")
    
    ip_address = request.remote_addr

    # --- DEBUG DỮ LIỆU THIẾU ---
    missing = []
    if not username: missing.append("username")
    if not password: missing.append("password")
    if not captcha: missing.append("captcha")
    if not captcha_token: missing.append("captcha_token")
    if not csrf_token: missing.append("csrf_token")
    
    if missing:
        print(f"❌ MISSING FIELDS: {missing}", file=sys.stderr)
        # Trả về lỗi chi tiết để Frontend biết thiếu gì (tạm thời)
        return jsonify({'success': False, 'message': f'Thiếu thông tin: {", ".join(missing)}'}), 400

    # 3. Validate Token (Logic cũ)
    if not validate_csrf_token(csrf_token):
        print("❌ Invalid CSRF Token", file=sys.stderr)
        return jsonify({'success': False, 'message': 'Token bảo mật không hợp lệ'}), 400
        
    if not validate_captcha(captcha, captcha_token):
        print(f"❌ Invalid Captcha. Input: {captcha}", file=sys.stderr)
        return jsonify({'success': False, 'message': 'Mã xác thực không đúng'}), 400

    # 4. Xử lý Database (Giữ nguyên logic cũ)
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone()

    if user and check_password_hash(user['password'], password):
        if user["status"] == "active":
            cur.execute("UPDATE users SET last_login=NOW() WHERE id=%s", (user['id'],))
            db.commit()
            if user.get('email'):
                otp = generate_otp()
                otp_storage[username] = {'otp': otp, 'expires_at': time.time() + SECURITY_CONFIG['OTP_EXPIRY'], 'ip': ip_address}
                send_otp_email(user['email'], otp, username)
                log_action(username, "Login: OTP sent")
                cur.close(), db.close()
                return jsonify({'success': True, 'requireOTP': True})
            else:
                session["username"], session["role"], session["last_activity"] = user["username"], user["role"], time.time()
                log_action(username, "Login: Success")
                cur.close(), db.close()
                return jsonify({'success': True, 'requireOTP': False, 'redirect': url_for('admin_dashboard' if user['role'] == 'admin' else 'user_redirect')})
        else:
            cur.close(), db.close()
            return jsonify({'success': False, 'message': 'Tài khoản đã bị khóa hoặc đang chờ xử lý.'}), 403
    else:
        cur.close(), db.close()
        log_action(username, "Login: Failed", False)
        return jsonify({'success': False, 'message': 'Sai tài khoản hoặc mật khẩu!'}), 401

@app.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    otp = request.json.get('otp')
    username = next((user for user, data in otp_storage.items() if data.get('ip') == request.remote_addr), None)
    if not username or username not in otp_storage: return jsonify({'success': False, 'error': 'Không tìm thấy phiên OTP'}), 400
    otp_data = otp_storage[username]
    if time.time() > otp_data['expires_at']:
        del otp_storage[username]
        return jsonify({'success': False, 'error': 'Mã OTP đã hết hạn'}), 400
    if otp == otp_data['otp']:
        db = get_db_connection()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE username=%s", (username,))
        user = cur.fetchone()
        cur.close()
        db.close()
        if user:
            session["username"], session["role"], session["last_activity"] = user["username"], user["role"], time.time()
            otp_storage.pop(username, None)
            log_action(username, "Login: OTP verified")
            return jsonify({'success': True, 'redirect': url_for('admin_dashboard' if user['role'] == 'admin' else 'user_redirect')})
    return jsonify({'success': False, 'error': 'Mã OTP không đúng'}), 400

# Cap nhat ham resend OTP
@app.route("/api/resend-otp", methods=["POST"])
def resend_otp_api():
    """API gửi lại mã OTP cho cả Đăng ký và Đăng nhập"""
    
    # TRƯỜNG HỢP 1: ĐANG ĐĂNG KÝ (Dữ liệu nằm trong Session)
    if 'registration_data' in session:
        try:
            reg_data = session['registration_data']
            new_otp = generate_otp()
            
            # Cập nhật OTP mới vào session
            reg_data['otp'] = new_otp
            reg_data['expires_at'] = time.time() + SECURITY_CONFIG['OTP_EXPIRY']
            session['registration_data'] = reg_data # Lưu lại thay đổi
            
            if send_otp_email(reg_data['email'], new_otp, reg_data['username']):
                return jsonify({'success': True, 'message': 'Đã gửi lại mã OTP vào email đăng ký.'})
            else:
                return jsonify({'success': False, 'message': 'Lỗi hệ thống gửi email.'}), 500
        except Exception as e:
            app.logger.error(f"Resend Register OTP Error: {e}")
            return jsonify({'success': False, 'message': 'Lỗi không xác định.'}), 500

    # TRƯỜNG HỢP 2: ĐANG ĐĂNG NHẬP (Dữ liệu nằm trong bộ nhớ RAM otp_storage)
    # Lấy username từ request hoặc tìm theo IP người dùng
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    
    # Nếu frontend không gửi username, thử mò lại trong otp_storage theo IP (fallback)
    if not username:
        username = next((u for u, d in otp_storage.items() if d.get('ip') == request.remote_addr), None)

    if username:
        try:
            # Lấy email từ Database vì otp_storage không lưu email
            db = get_db_connection()
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT email FROM users WHERE username=%s", (username,))
            user = cur.fetchone()
            cur.close()
            db.close()
            
            if user and user['email']:
                new_otp = generate_otp()
                # Cập nhật OTP mới vào bộ nhớ
                otp_storage[username] = {
                    'otp': new_otp, 
                    'expires_at': time.time() + SECURITY_CONFIG['OTP_EXPIRY'],
                    'ip': request.remote_addr
                }
                
                if send_otp_email(user['email'], new_otp, username):
                    log_action(username, "Resend Login OTP")
                    return jsonify({'success': True, 'message': 'Đã gửi lại mã OTP đăng nhập.'})
                else:
                    return jsonify({'success': False, 'message': 'Lỗi gửi email.'}), 500
            else:
                return jsonify({'success': False, 'message': 'Không tìm thấy email liên kết hoặc user không tồn tại.'}), 400
        except Exception as e:
            app.logger.error(f"Resend Login OTP Error: {e}")
            return jsonify({'success': False, 'message': 'Lỗi Database.'}), 500
            
    return jsonify({'success': False, 'message': 'Không tìm thấy phiên xác thực. Vui lòng thực hiện lại từ đầu.'}), 400

# Ket Thuc Ham ^^^^^^^^^^^^
@app.route("/logout")
def logout():
    log_action(session.get("username", "unknown"), "Logout: Success")
    session.clear()
    flash("Đã đăng xuất.", "info")
    return redirect(url_for("login_page"))

# ================== REGISTRATION WITH OTP ROUTES ==================
@app.route("/register", methods=["GET", "POST"])
def register():
    if "username" in session: return redirect(url_for("index"))
    if request.method == "POST":
        username, password, email = request.form["username"].strip().lower(), request.form["password"].strip(), request.form.get("email", "").strip()
        is_strong, message = validate_password_strength(password)
        if not is_strong:
            flash(message, "error")
            return redirect(url_for("register"))
        if not email:
            flash("Vui lòng nhập email để xác thực.", "error")
            return redirect(url_for("register"))

        db = get_db_connection()
        cur = db.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
        if cur.fetchone():
            flash("Username hoặc Email đã tồn tại!", "error")
            cur.close(), db.close()
            return redirect(url_for("register"))

        otp = generate_otp()
        session['registration_data'] = {
            'username': username, 'password': generate_password_hash(password), 'email': email,
            'otp': otp, 'expires_at': time.time() + SECURITY_CONFIG['OTP_EXPIRY']
        }
        send_otp_email(email, otp, username)
        log_action(username, f"Register: OTP sent to {email}")
        return redirect(url_for('verify_email'))
    return render_template("register.html")

@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    if 'registration_data' not in session: return redirect(url_for('register'))
    reg_data = session['registration_data']
    if time.time() > reg_data['expires_at']:
        session.pop('registration_data', None)
        flash("Mã OTP đã hết hạn. Vui lòng đăng ký lại.", "error")
        return redirect(url_for('register'))
    if request.method == 'POST' and request.form.get('otp', '') == reg_data['otp']:
        db = get_db_connection()
        cur = db.cursor()

        # === SỬA ĐỔI TẠI ĐÂY ===
        # Thay 'active' thành 'pending' để yêu cầu admin duyệt
        cur.execute("INSERT INTO users(username, password, email, status, role) VALUES(%s, %s, %s, 'pending', 'user')",
                    (reg_data['username'], reg_data['password'], reg_data['email']))
        # === KẾT THÚC SỬA ĐỔI ===

        db.commit()
        cur.close(), db.close()
        log_action(reg_data['username'], "Register success, pending approval")
        session.pop('registration_data', None)

        # Sửa lại thông báo cho người dùng
        flash("Xác thực và đăng ký thành công! Tài khoản của bạn đang chờ quản trị viên phê duyệt.", "success")
        return redirect(url_for('login_page'))

    elif request.method == 'POST':
        flash("Mã OTP không chính xác!", "error")
    return render_template('verify_email.html', email=reg_data['email'])

# ================== USER ROUTES & IDE APIS ==================
@app.route("/user")
@require_auth('user')
def user_redirect():
    return redirect(url_for('user_workspace', username=session['username']))

@app.route("/user/<username>/workspace")
@require_auth('user')
def user_workspace(username):
    if session["username"] != username: return redirect(url_for("index"))
    try:        
        ensure_user_container_and_setup(username)
    except Exception as e:
        app.logger.error(f"Container check failed for {username}: {e}")
        flash(f"Lỗi khởi tạo môi trường làm việc: {e}", "error")
    return render_template("user.html", username=username)

# --- CẤU HÌNH DANH SÁCH FILE CẦN ẨN TUYỆT ĐỐI ---
HIDDEN_SYSTEM_FILES = {
    "setup_container.sh",
    "startup.sh",
    ".bashrc",
    ".profile",
    ".bash_logout",
    ".local",
    ".cache",
    ".config",
    ".wget-hsts",
    ".sudo_as_admin_successful"
}

@app.route('/user/<username>/files', methods=['POST'])
@require_auth('user')
def list_files_api(username):
    # 1. Chuẩn hóa tên user
    safe_username = make_safe_name(username)
    
    # 2. Check quyền
    if session['username'] != username: 
        return jsonify(error="Unauthorized"), 403
    
    path = request.json.get("path", ".")
    
    # 3. Validate đường dẫn
    if '..' in path or path.startswith('/'): 
        return jsonify(error="Invalid path"), 400
    
    try:
        # 4. Kết nối SFTP
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        # 5. Xác định đường dẫn
        base_path = os.path.join("/home", safe_username, path)
        
        files = []
        try:
            dir_items = sftp.listdir_attr(base_path)
        except FileNotFoundError:
            return jsonify(error="Directory not found"), 404
            
        for attr in dir_items:
            filename = attr.filename
            
            # LOGIC CHẶN FILE HỆ THỐNG
            
            # 1. Chặn file ẩn của Linux (bắt đầu bằng dấu chấm)
            if filename.startswith('.'):
                continue
                
            # 2. Chặn các file nằm trong Danh sách đen (setup_container.sh...)
            if filename in HIDDEN_SYSTEM_FILES:
                continue

            files.append({
                'name': filename, 
                'is_dir': stat.S_ISDIR(attr.st_mode), 
                'size': attr.st_size, 
                'modified': attr.st_mtime
            })
        
        sftp.close()
        client.close()
        
        # Sắp xếp: Folder lên đầu
        files.sort(key=lambda x: (not x['is_dir'], x['name']))
        
        # Log (Optional - có thể bỏ qua nếu sợ rác log)
        # log_action(username, f"List files: {base_path}")
        
        return jsonify(files=files, path=path)

    except Exception as e:
        app.logger.error(f"ERROR List Files user '{safe_username}': {str(e)}")
        return jsonify(error=str(e)), 500
# KET THUC HAM

@app.route('/user/<username>/create-folder', methods=['POST'])
@require_auth('user')
def create_folder_api(username):
    # 1. Chuẩn hóa tên ( a b c -> a_b_c)upload_files_apiupload_files_api
    safe_username = make_safe_name(username)

    # 2. Check quyền (So sánh session với tên gốc)
    if session.get('username') != username: 
        return jsonify(success=False, error="Unauthorized"), 403

    data = request.get_json()
    folder_name = data.get("folder_name")
    path = data.get("path", ".")

    # 3. Validate input kỹ càng
    if not folder_name or not is_safe_path("/home", folder_name): # Chống tên folder chứa ký tự lạ
        return jsonify(success=False, error="Invalid folder name"), 400
    
    home_dir = f"/home/{safe_username}"
    if not is_safe_path(home_dir, path):
        return jsonify(success=False, error="Invalid path"), 400

    try:
        client = get_ssh_client(username) # Dùng tên an toàn
        sftp = client.open_sftp()
        
        full_path = os.path.join(home_dir, path, folder_name)
        sftp.mkdir(full_path)
        
        sftp.close(); client.close()
        log_action(username, f"Create folder: {full_path}")
        return jsonify(success=True)
    except Exception as e: 
        app.logger.error(f"Create Folder Error: {e}")
        return jsonify(success=False, error=str(e)), 500

# ==========================================
# 2. ĐỌC FILE (LOAD EDITOR)
# ==========================================
@app.route('/user/<username>/editor/load', methods=['POST'])
@require_auth('user')
def load_file_api(username):
    safe_username = make_safe_name(username)
    if session.get('username') != username: return jsonify(success=False, error="Unauthorized"), 403

    data = request.get_json()
    filename, path = data.get("filename"), data.get("path", ".")
    
    home_dir = f"/home/{safe_username}"
    # Check an toàn cho cả path và filename
    if not filename or not is_safe_path(home_dir, os.path.join(path, filename)):
        return jsonify(success=False, error="Invalid file path"), 400

    try:
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        filepath = os.path.join(home_dir, path, filename)
        
        with sftp.open(filepath, 'r') as f: 
            content = f.read().decode('utf-8', errors='ignore')
            
        sftp.close(); client.close()
        # Log mức debug thôi để đỡ rác database
        # log_action(username, f"Open file: {filepath}") 
        return jsonify(success=True, content=content)
    except Exception as e: 
        return jsonify(success=False, error=str(e)), 500

# ==========================================
# 3. LƯU FILE (SAVE)
# ==========================================
@app.route('/user/<username>/editor/save', methods=['POST'])
@require_auth('user')
def save_file_api(username):
    safe_username = make_safe_name(username) # FIX
    
    if session.get('username') != username: return jsonify(success=False, error="Unauthorized"), 403

    data = request.get_json()
    filename = data.get("filename")
    content = data.get("content", "")
    path = data.get("path", ".")

    home_dir = f"/home/{safe_username}"
    if not filename or not is_safe_path(home_dir, os.path.join(path, filename)):
        return jsonify(success=False, error="Invalid file path"), 400

    try:
        # FIX:  Dùng safe_username, code cũ dùng username -> Lỗi kết nối
        client = get_ssh_client(username) 
        sftp = client.open_sftp()
        
        filepath = os.path.join(home_dir, path, filename)
        
        with sftp.open(filepath, 'w') as f: 
            f.write(content)
            
        sftp.close(); client.close()
        log_action(username, f"Save file: {filename}")
        return jsonify(success=True)
    except Exception as e: 
        app.logger.error(f"Save Error: {e}")
        return jsonify(success=False, error=str(e)), 500

# ==========================================
# 4. ĐỔI TÊN (RENAME)
# ==========================================
@app.route('/user/<username>/rename-item', methods=['POST'])
@require_auth('user')
def rename_item_api(username):
    safe_username = make_safe_name(username)
    
    if session.get('username') != username: return jsonify(success=False, error="Unauthorized"), 403
    
    data = request.get_json()
    old_path = data.get("old_path")
    new_name = data.get("new_name")
    
    # Validate
    if not old_path or not new_name or '/' in new_name or '..' in new_name:
        return jsonify(success=False, error="Invalid parameters"), 400

    try:
        # FIX: Dùng safe_username
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        # Xây dựng đường dẫn tuyệt đối với safe_username
        # Code cũ dùng username -> Dẫn tới /home/a b c/... (Sai)
        base_dir_rel = os.path.dirname(old_path)
        old_full_path = os.path.join("/home", safe_username, old_path)
        new_full_path = os.path.join("/home", safe_username, base_dir_rel, new_name)
        
        sftp.rename(old_full_path, new_full_path)
        
        sftp.close(); client.close()
        log_action(username, f"Rename: {old_path} -> {new_name}")
        return jsonify(success=True)
    except Exception as e: 
        return jsonify(success=False, error=str(e)), 500

# ==========================================
# 5. XÓA FILE/FOLDER (DELETE)
# ==========================================
@app.route('/user/<username>/delete-item', methods=['POST'])
@require_auth('user')
def delete_item_api(username):
    safe_username = make_safe_name(username)
    if session.get('username') != username: return jsonify(success=False, error="Unauthorized"), 403
    
    path = request.json.get("path")
    home_dir = f"/home/{safe_username}"

    if not path or not is_safe_path(home_dir, path):
        return jsonify(success=False, error="Invalid path"), 400

    try:
        client = get_ssh_client(username)

        full_path = os.path.normpath(os.path.join(home_dir, path))
        
        # Double check: Không cho phép xóa thư mục gốc của user
        if full_path == home_dir:
             return jsonify(success=False, error="Cannot delete root home"), 403
             
        # FIX CÚ PHÁP: Thêm dấu cách sau -rf
        # shlex.quote giúp bọc đường dẫn: rm -rf '/home/a_b/file co dau cach'
        safe_command = f'rm -rf {shlex.quote(full_path)}'

        stdin, stdout, stderr = client.exec_command(safe_command)
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            log_action(username, f"Delete: {path}")
            return jsonify(success=True)
        else:
            err_msg = stderr.read().decode().strip()
            raise Exception(err_msg)
            
    except Exception as e: 
        app.logger.error(f"Delete Error: {e}")
        return jsonify(success=False, error=str(e)), 500

# ==========================================
# 6. UPLOAD FILE
# ==========================================
@app.route('/user/<username>/upload-files', methods=['POST'])
@require_auth('user')
def upload_files_api(username):
    safe_username = make_safe_name(username)
    if session.get('username') != username: return jsonify(success=False, error="Unauthorized"), 403
    
    path = request.form.get('path', '.')
    files = request.files.getlist('files')
    
    home_dir = f"/home/{safe_username}"
    if not files: return jsonify(success=False, error="No files provided"), 400
    if not is_safe_path(home_dir, path): return jsonify(success=False, error="Invalid path"), 400

    try:
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        count = 0
        for file in files:
            if file.filename:
                # FIX: Dùng secure_filename để loại bỏ ký tự lạ trong tên file upload
                safe_filename = secure_filename(file.filename)
                target_path = os.path.join(home_dir, path, safe_filename)
                
                # putfo upload file từ bộ nhớ lên server
                sftp.putfo(file, target_path)
                count += 1
                
        sftp.close(); client.close()
        log_action(username, f"Uploaded {count} files to {path}")
        return jsonify(success=True, message=f"Uploaded {count} files.")
    except Exception as e: 
        app.logger.error(f"Upload Error: {e}")
        return jsonify(success=False, error=str(e)), 500

@app.route('/user/<username>/compile', methods=['POST'])
@require_auth('user')
def compile_sketch_api(username):
    data = request.get_json()
    sketch_path = data.get("sketch_path")
    board_fqbn = data.get("board_fqbn")
    if not sketch_path or not board_fqbn:
        return jsonify(success=False, output="Thiếu thông tin sketch_path hoặc board", error_analysis=None), 400

    # --- FIX: Dùng tên an toàn ---
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    full_path = os.path.normpath(f"/home/{safe_username}/{sketch_path}")
    # -----------------------------

    try:
        cmd = ["docker", "exec", cname, "arduino-cli", "compile", "--fqbn", board_fqbn, "--verbose", full_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        output = result.stdout + "\n" + result.stderr

        success = result.returncode == 0
        log_action(username, f"{'Compile success' if success else 'Compile failed'}: {sketch_path}", success=success)
        
        error_analysis = memory_analysis = None
        if not success:
            error_analysis = analyze_compile_errors(output)
        else:
            memory_analysis = analyze_memory_usage(output)

        return jsonify(success=success, output=output, 
                       returncode=result.returncode, 
                       error_analysis=error_analysis,
                       memory_analysis=memory_analysis)
    except subprocess.TimeoutExpired:
        log_action(username, f"Compile timeout: {sketch_path}", success=False)
        return jsonify(success=False, output="Quá thời gian biên dịch", error_analysis=None), 500
    except Exception as e:
        log_action(username, f"Compile error: {sketch_path}", success=False, details={"error": str(e)})
        return jsonify(success=False, output=f"Lỗi hệ thống: {str(e)}", error_analysis=None), 500

def analyze_memory_usage(output):
    """Phân tích output để lấy thông tin sử dụng bộ nhớ."""
    ram_match = re.search(r"Variables and constants in RAM.*?used (\d+) / (\d+) bytes \((\d+)%\)", output)
    iram_match = re.search(r"Instruction RAM.*?used (\d+) / (\d+) bytes \((\d+)%\)", output)
    flash_match = re.search(r"Code in flash.*?used (\d+) / (\d+) bytes \((\d+)%\)", output)

    analysis = {}
    if ram_match:
        analysis['ram'] = {
            'used': int(ram_match.group(1)),
            'total': int(ram_match.group(2)),
            'percent': int(ram_match.group(3))
        }
    if flash_match:
        # Gộp IRAM và Flash vào làm một để đơn giản hóa cho người dùng
        iram_used = int(iram_match.group(1)) if iram_match else 0
        flash_used = int(flash_match.group(1))
        analysis['flash'] = {
            'used': flash_used + iram_used,
            'total': int(flash_match.group(2)),
            'percent': round(((flash_used + iram_used) / int(flash_match.group(2))) * 100)
        }
    return analysis

def analyze_compile_errors(output):
    """
    Phân tích output để tìm thông tin lỗi chi tiết
    """
    errors = []
    warnings = []
    
    lines = output.split('\n')
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Tìm lỗi compile (error)
        if 'error:' in line.lower():
            error_info = extract_error_info(line, lines, i)
            if error_info:
                errors.append(error_info)
        
        # Tìm cảnh báo (warning)  
        elif 'warning:' in line.lower():
            warning_info = extract_warning_info(line, lines, i)
            if warning_info:
                warnings.append(warning_info)
    
    return {
        'errors': errors,
        'warnings': warnings,
        'error_count': len(errors),
        'warning_count': len(warnings)
    }

def extract_error_info(error_line, all_lines, line_index):
    """
    Trích xuất thông tin chi tiết về lỗi
    """
    import re
    
    # Pattern để tìm file:line:column: error
    pattern = r'(.+?):(\d+):(\d+):\s*error:\s*(.+)'
    match = re.search(pattern, error_line)
    
    if match:
        file_path = match.group(1)
        line_number = int(match.group(2))
        column_number = int(match.group(3))
        error_message = match.group(4)
        
        # Tìm thêm context từ các dòng tiếp theo
        context = []
        for j in range(line_index + 1, min(line_index + 3, len(all_lines))):
            if all_lines[j].strip() and not all_lines[j].strip().startswith('/'):
                context.append(all_lines[j].strip())
        
        return {
            'type': 'error',
            'file': os.path.basename(file_path),
            'line': line_number,
            'column': column_number,
            'message': error_message,
            'context': context
        }
    
    # Fallback cho các format lỗi khác
    if 'error:' in error_line.lower():
        return {
            'type': 'error',
            'message': error_line.strip(),
            'raw': True
        }
    
    return None

def extract_warning_info(warning_line, all_lines, line_index):
    """
    Trích xuất thông tin chi tiết về warning
    """
    import re
    
    # Pattern để tìm file:line:column: warning
    pattern = r'(.+?):(\d+):(\d+):\s*warning:\s*(.+)'
    match = re.search(pattern, warning_line)
    
    if match:
        file_path = match.group(1)
        line_number = int(match.group(2))
        column_number = int(match.group(3))
        warning_message = match.group(4)
        
        return {
            'type': 'warning',
            'file': os.path.basename(file_path),
            'line': line_number,
            'column': column_number,
            'message': warning_message
        }
    
    # Fallback cho các format warning khác
    if 'warning:' in warning_line.lower():
        return {
            'type': 'warning',
            'message': warning_line.strip(),
            'raw': True
        }
    
    return None
# =================================================================

# ================== ARDUINO UPLOAD APIs ==================


#  upload_to_board_api
@app.route('/user/<username>/upload', methods=['POST'])
@require_auth('user')
def upload_to_board_api(username):
    data = request.get_json()
    if data is None:
        return jsonify(success=False, error="Yêu cầu không chứa dữ liệu JSON."), 400
        
    sid = data.get('sid')
    if not sid:
         return jsonify(success=False, error="Lỗi Frontend: Missing SID for status updates."), 400

    sketch_path = data.get("sketch_path")
    board_fqbn = data.get("board_fqbn")
    port = data.get("port")
    
    if not all([sketch_path, board_fqbn, port]):
        return jsonify(success=False, error="Thiếu thông tin sketch/board/port"), 400
    
    # === SỬA LỖI QUAN TRỌNG NHẤT: DÙNG CÔNG CỤ ĐÚNG CỦA SOCKETIO ===
    # Thay vì tạo threading.Thread, chúng ta dùng hàm có sẵn của socketio
    socketio.start_background_task(
        target=_perform_upload_worker, 
        username=username, 
        sid=sid, 
        sketch_path=sketch_path, 
        board_fqbn=board_fqbn, 
        port=port
    )
    # ==========================================================
    
    # Trả về ngay lập tức cho client biết yêu cầu đã được tiếp nhận
    return jsonify(success=True, message="Yêu cầu nạp code đã được đưa vào hàng đợi.")

# KET THUC HAM 



def analyze_upload_errors(output):
    """Phân tích lỗi upload để đưa ra gợi ý"""
    errors = {
        'connection_failed': False,
        'permission_denied': False,
        'board_not_found': False,
        'wrong_board': False,
        'port_busy': False,
        'bootloader_issue': False
    }
    
    output_lower = output.lower()
    
    # Phát hiện các loại lỗi phổ biến
    if 'permission denied' in output_lower or 'access denied' in output_lower:
        errors['permission_denied'] = True
    
    if 'no such file or directory' in output_lower and '/dev/' in output_lower:
        errors['board_not_found'] = True
    
    if 'device or resource busy' in output_lower:
        errors['port_busy'] = True
        
    if 'connection failed' in output_lower or 'upload failed' in output_lower:
        errors['connection_failed'] = True
        
    if 'wrong microcontroller' in output_lower or 'expected' in output_lower:
        errors['wrong_board'] = True
        
    if 'bootloader' in output_lower:
        errors['bootloader_issue'] = True
    
    return errors


def get_upload_error_suggestions(error_analysis):
    """Đưa ra gợi ý sửa lỗi dựa trên phân tích"""
    suggestions = []
    
    if error_analysis.get('permission_denied'):
        suggestions.append("🔧 Lỗi quyền truy cập: Thử chạy lại hoặc kiểm tra quyền truy cập cổng serial")
    
    if error_analysis.get('board_not_found'):
        suggestions.append("🔌 Không tìm thấy board: Kiểm tra kết nối USB và chọn đúng cổng")
    
    if error_analysis.get('port_busy'):
        suggestions.append("⚠️ Cổng đang bận: Đóng Serial Monitor hoặc các ứng dụng khác đang sử dụng cổng này")
    
    if error_analysis.get('connection_failed'):
        suggestions.append("📡 Kết nối thất bại: Thử nhấn nút Reset trên board và nạp lại")
    
    if error_analysis.get('wrong_board'):
        suggestions.append("🎯 Sai loại board: Kiểm tra lại board type (Arduino Uno, ESP32, etc.)")
    
    if error_analysis.get('bootloader_issue'):
        suggestions.append("💾 Lỗi bootloader: Board có thể cần được nạp bootloader lại")
    
    if not any(error_analysis.values()):
        suggestions.append("🔍 Thử các bước: 1) Kiểm tra kết nối 2) Chọn đúng cổng 3) Chọn đúng board type")
    
    return suggestions


# ================== CONTAINER MANAGEMENT HELPER ==================
def ensure_arduino_tools_in_container(username):
    """Đảm bảo container có đầy đủ tools cần thiết cho Arduino"""
    cname = f"{username}-dev"
    
    try:
        # Kiểm tra xem arduino-cli đã được cài đặt chưa
        check_cmd = [
            "docker", "exec", cname,
            "/usr/local/bin/arduino-cli", "version"
        ]
        
        result = subprocess.run(check_cmd, capture_output=True, timeout=10)
        
        if result.returncode != 0:
            app.logger.warning(f"Arduino CLI not found in container {cname}, installing...")
            # Có thể thêm logic cài đặt arduino-cli ở đây nếu cần
            return False
            
        return True
        
    except Exception as e:
        app.logger.error(f"Error checking Arduino tools in {cname}: {e}")
        return False
# ▲▲▲ KẾT THÚC ĐOẠN CODE API BIÊN DỊCH MỚI ▲▲▲
# ================== ADMIN ROUTES ==================
@app.route("/admin")
@require_auth('admin')
def admin_dashboard():
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT status, COUNT(*) as count FROM users GROUP BY status")
    stats = {row['status']: row['count'] for row in cur.fetchall()}
    cur.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 50")
    logs = cur.fetchall()
    cur.close(), db.close()
    return render_template("admin.html", 
                           total_users=sum(stats.values()),
                           active_users=stats.get('active', 0),
                           blocked_users=stats.get('blocked', 0),
                           pending_users=stats.get('pending', 0),
                           logs=logs)

@app.route("/admin/manage")
@require_auth('admin')
def admin_manage():
    db = get_db_connection()
    if not db:
        flash("Không thể kết nối đến database.", "error")
        return render_template("manage.html", users=[])

    cur = db.cursor(dictionary=True)
    
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str).strip()
    per_page = 15
    offset = (page - 1) * per_page

    base_query = "FROM users WHERE (username LIKE %s OR email LIKE %s)"
    search_term = f"%{search_query}%"
    
    # Get total count for pagination
    cur.execute(f"SELECT COUNT(id) as total {base_query}", (search_term, search_term))
    total_users = cur.fetchone()['total']
    total_pages = ceil(total_users / per_page) if total_users > 0 else 1

    # Get users for the current page
    query = f"SELECT id, username, email, role, status, created_at {base_query} ORDER BY created_at DESC LIMIT %s OFFSET %s"
    cur.execute(query, (search_term, search_term, per_page, offset))
    users = cur.fetchall()
    return render_template("manage.html", users=users, page=page, total_pages=total_pages, search_query=search_query)
    
@app.route("/admin/approve")
@require_auth('admin')
def admin_approve_page():
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, username, email, created_at FROM users WHERE status = 'pending' ORDER BY created_at DESC")
    users = cur.fetchall()
    cur.close(), db.close()
    return render_template("approve.html", users=users)

@app.route("/admin/api/logs")
@require_auth('admin')
def admin_api_logs():
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT username, action, ip_address, timestamp FROM logs ORDER BY timestamp DESC LIMIT 50")
    logs = cur.fetchall()
    cur.close(), db.close()
    for log in logs: log['timestamp'] = log['timestamp'].isoformat()
    return jsonify({'success': True, 'logs': logs})

@app.route("/admin/add_user", methods=["POST"])
@require_auth('admin')
def add_user():
    username, password, email, role = request.form.get("username", "").strip(), request.form.get("password", "").strip(), request.form.get("email", "").strip() or None, request.form.get("role", "user")
    is_strong, message = validate_password_strength(password)
    if not is_strong:
        flash(message, "error")
        return redirect(url_for("admin_manage"))
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("INSERT INTO users(username, password, email, role, status) VALUES(%s, %s, %s, %s, 'active')",
                (username, generate_password_hash(password), email, role))
    db.commit()
    cur.close(), db.close()
    flash(f"Đã thêm user '{username}' thành công!", "success")
    return redirect(url_for("admin_manage"))

# ▼▼▼ TÌM VÀ THAY THẾ TOÀN BỘ HÀM NÀY TRONG app.py ▼▼▼

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@require_auth('admin')
def delete_user(user_id):
    db = get_db_connection()
    if not db: return jsonify(success=False, error="Database connection error"), 500
    cur = db.cursor(dictionary=True)
    
    # 1. Lấy thông tin username gốc từ DB
    cur.execute("SELECT username FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    
    if user:
        username_raw = user['username']
        # --- BƯỚC QUAN TRỌNG: CHUẨN HÓA TÊN ---
        # Chuyển 'A B C' thành 'A_B_C' để khớp với tên folder và container đã tạo
        safe_username = make_safe_name(username_raw)
        cname = f"{safe_username}-dev"
        host_user_dir = f"/home/toan/QUAN_LY_USER/{safe_username}"
        # --------------------------------------

        app.logger.info(f"Admin action: Deleting user {username_raw} (Safe name: {safe_username})")

        # BƯỚC 1: Ép buộc xóa Docker container
        try:
            subprocess.run(["docker", "rm", "-f", cname], check=False, timeout=15)
            app.logger.info(f"Removed container: {cname}")
        except Exception as e:
            app.logger.error(f"Failed to remove container {cname}: {e}")
        
        # BƯỚC 2: Xóa thư mục dữ liệu trên máy chủ Ubuntu
        try:
            if os.path.exists(host_user_dir):
                # rmtree sẽ xóa sạch folder và file bên trong
                shutil.rmtree(host_user_dir)
                app.logger.info(f"Deleted directory: {host_user_dir}")
            else:
                app.logger.warning(f"Directory not found, skipping: {host_user_dir}")
        except Exception as e:
            app.logger.error(f"Failed to delete directory {host_user_dir}: {e}")

        # BƯỚC 3: Xóa user khỏi Database (Xóa sau cùng để đảm bảo có thông tin ở các bước trên)
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        db.commit()
        
        log_action(session["username"], f"Deleted user '{username_raw}' and folder '{safe_username}'")
        flash(f"Đã xóa hoàn toàn user '{username_raw}' và thư mục dữ liệu.", "success")
    else:
        flash("Người dùng không tồn tại!", "error")
        
    cur.close()
    db.close()
    return redirect(url_for("admin_manage"))

# --- KET THUC HAM ^^ ---

@app.route("/admin/change_user_status/<action>/<username>", methods=["POST"])
@require_auth('admin')
def change_user_status(action, username):
    db = get_db_connection()
    cur = db.cursor()
    actions = {
        "approve": ("active", f"Approved: {username}", f"Đã duyệt user {username}", "success"),
        "block": ("blocked", f"Blocked: {username}", f"Đã khóa user {username}", "warning"),
        "unblock": ("active", f"Unblocked: {username}", f"Đã mở khóa user {username}", "success"),
    }
    if action in actions:
        new_status, log_msg, flash_msg, flash_cat = actions[action]
        cur.execute("UPDATE users SET status=%s WHERE username=%s", (new_status, username))
        db.commit()
        log_action(session["username"], log_msg)
        flash(flash_msg, flash_cat)
    else:
        flash("Hành động không hợp lệ!", "error")
    cur.close(), db.close()
    redirect_to = request.form.get('next') or url_for("admin_manage")
    return redirect(redirect_to)

@app.route("/admin/assignments")
@require_auth('admin')
def admin_assignments_page():
    return render_template("admin/assignments.html")

@app.route("/admin/api/users")
@require_auth('admin')
def admin_api_get_users():
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    # Lấy những user không phải admin và đang active
    cur.execute("SELECT id, username FROM users WHERE role = 'user' AND status = 'active' ORDER BY username")
    users = cur.fetchall()
    cur.close()
    db.close()
    return jsonify(users)

@app.route("/admin/api/assignments", methods=['GET'])
@require_auth('admin')
def admin_api_get_assignments():
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    query = """
        SELECT 
            da.id, 
            u.username, 
            hd.tag_name, 
            da.assigned_at, 
            da.expires_at
        FROM device_assignments da
        JOIN users u ON da.user_id = u.id
        JOIN hardware_devices hd ON da.device_id = hd.id
        ORDER BY da.assigned_at DESC
    """
    cur.execute(query)
    assignments = cur.fetchall()
    cur.close()
    db.close()
    return jsonify(assignments)

@app.route("/admin/api/assignments", methods=['POST'])
@require_auth('admin')
def admin_api_add_assignment():
    data = request.get_json()
    user_id = data.get('user_id')
    device_id = data.get('device_id')
    if not all([user_id, device_id]):
        return jsonify(success=False, error="Thiếu thông tin user hoặc thiết bị."), 400
    try:
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("INSERT INTO device_assignments (user_id, device_id) VALUES (%s, %s)", (user_id, device_id))
        db.commit()
        cur.close()
        db.close()
        return jsonify(success=True, message="Cấp quyền thành công!")
    except mysql.connector.Error as err:
        if err.errno == 1062: return jsonify(success=False, error="Người dùng này đã được cấp quyền cho thiết bị này."), 409
        return jsonify(success=False, error=f"Lỗi Database: {err}"), 500

@app.route("/admin/devices")
@require_auth('admin')
def admin_devices_page():
    return render_template("admin/devices.html")

@app.route("/admin/api/devices", methods=['GET'])
@require_auth('admin')
def admin_api_get_devices():
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM hardware_devices ORDER BY tag_name")
    devices = cur.fetchall()
    cur.close()
    db.close()
    return jsonify(devices)

@app.route("/admin/api/devices", methods=['POST'])
@require_auth('admin')
def admin_api_add_device():
    data = request.get_json()
    tag_name = data.get('tag_name')
    device_type = data.get('type')
    port = data.get('port')

    if not all([tag_name, device_type, port]):
        return jsonify(success=False, error="Vui lòng điền đầy đủ thông tin."), 400

    try:
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("INSERT INTO hardware_devices (tag_name, type, port) VALUES (%s, %s, %s)", (tag_name, device_type, port))
        db.commit()
        cur.close()
        db.close()
        return jsonify(success=True, message="Thêm thiết bị thành công!")
    except mysql.connector.Error as err:
        return jsonify(success=False, error=f"Lỗi Database: {err}"), 500

@app.route("/admin/missions")
@require_auth('admin')
def admin_missions_page():
    return render_template("admin/missions.html")

@app.route("/admin/api/missions", methods=['POST'])
@require_auth('admin')
def admin_api_create_mission():
    data = request.get_json()
    mission_name = data.get('mission_name')
    user_ids = data.get('user_ids')
    device_ids = data.get('device_ids')

    if not all([mission_name, user_ids, device_ids]):
        return jsonify(success=False, error="Vui lòng điền tên mission và chọn ít nhất một user và một thiết bị."), 400

    if not isinstance(user_ids, list) or not isinstance(device_ids, list):
        return jsonify(success=False, error="Dữ liệu không hợp lệ."), 400

    db = get_db_connection()
    cur = db.cursor()
    
    success_count = 0
    fail_count = 0
    errors = []

    for user_id in user_ids:
        for device_id in device_ids:
            # Dùng INSERT IGNORE để bỏ qua các quyền đã tồn tại, không báo lỗi
            cur.execute("INSERT IGNORE INTO device_assignments (user_id, device_id) VALUES (%s, %s)", (user_id, device_id))
            if cur.rowcount > 0:
                success_count += 1

    db.commit()
    cur.close()
    db.close()
    
    log_action(session['username'], f"Giao mission '{mission_name}': {success_count} quyền được cấp.")
    message = f"Giao mission '{mission_name}' hoàn tất. Đã cấp {success_count} quyền mới."
    return jsonify(success=True, message=message)

@app.route("/admin/api/assignments/<int:assignment_id>", methods=['DELETE'])
@require_auth('admin')
def admin_api_delete_assignment(assignment_id):
    try:
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("DELETE FROM device_assignments WHERE id = %s", (assignment_id,))
        db.commit()
        cur.close()
        db.close()
        if cur.rowcount == 0: return jsonify(success=False, error="Không tìm thấy quyền để xóa."), 404
        return jsonify(success=True, message="Đã thu hồi quyền!")
    except mysql.connector.Error as err: return jsonify(success=False, error=f"Lỗi Database: {err}"), 500

@app.route("/admin/api/devices/<int:device_id>", methods=['DELETE'])
@require_auth('admin')
def admin_api_delete_device(device_id):
    """API để xóa một thiết bị phần cứng."""
    try:
        db = get_db_connection()
        cur = db.cursor(dictionary=True)

        # Lấy thông tin thiết bị trước khi xóa để ghi log
        cur.execute("SELECT tag_name FROM hardware_devices WHERE id = %s", (device_id,))
        device = cur.fetchone()
        
        if not device:
            cur.close()
            db.close()
            return jsonify(success=False, error="Không tìm thấy thiết bị."), 404

        # Tiến hành xóa
        cur.execute("DELETE FROM hardware_devices WHERE id = %s", (device_id,))
        db.commit()
        
        # Ghi log hành động
        log_action(session['username'], f"Admin deleted device: {device['tag_name']}", success=True)
        
        cur.close()
        db.close()

        return jsonify(success=True, message="Đã xóa thiết bị thành công!")

    except mysql.connector.Error as err:
        # Xử lý trường hợp thiết bị đang được gán cho user
        if err.errno == 1451: # Foreign key constraint fails
            return jsonify(success=False, error="Không thể xóa! Thiết bị này đang được cấp quyền cho một hoặc nhiều user. Vui lòng thu hồi quyền trước."), 409
        return jsonify(success=False, error=f"Lỗi Database: {err}"), 500
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

# ================== SOCKET.IO FOR TERMINAL ==================
@socketio.on('connect', namespace='/terminal')
def terminal_connect():
    if 'username' not in session:
        return False

    username = session['username']
    sid = request.sid 
    
    try:
        client = get_ssh_client(username)
        chan = client.invoke_shell(term='xterm-color')
        
        # Lưu client và channel vào session của SocketIO cho kết nối này
        session['ssh_client'] = client
        session['ssh_chan'] = chan
        log_action(username, "Terminal: User connected")

        def forward_output():
            """Gửi output từ container đến trình duyệt."""
            try:
                while chan.active:
                    if chan.recv_ready():
                        data = chan.recv(1024)
                        if not data:
                            break
                        socketio.emit('output', data.decode('utf-8', errors='ignore'), 
                                    namespace='/terminal', room=sid) 
                    else:
                        socketio.sleep(0.1)
            except Exception as e:
                app.logger.warning(f"Terminal forward_output thread for {username} ended: {e}")
                socketio.emit('output', f'\r\n\x1b[31mConnection lost: {e}\x1b[0m\r\n', 
                            namespace='/terminal', room=sid)
        
        socketio.start_background_task(target=forward_output)
        return True
        
    except Exception as e:
        app.logger.error(f"SOCKET CONNECT ERROR for {username}: {e}")
        emit('output', f'\r\n\x1b[31mError connecting to terminal: {e}\x1b[0m\r\n', room=sid)
        return False

@socketio.on('input', namespace='/terminal')
def terminal_input(data):
    if 'ssh_chan' in session and session['ssh_chan'].active:
        try:
            # Kiểm tra data có hợp lệ không
            if isinstance(data, str):
                session['ssh_chan'].send(data)
            else:
                app.logger.warning(f"Invalid input data type: {type(data)}")
        except Exception as e:
            app.logger.error(f"SOCKET INPUT ERROR: {e}")
            # Thông báo lỗi đến client
            emit('output', f'\r\n\x1b[31mInput error: {e}\x1b[0m\r\n')

@socketio.on('disconnect', namespace='/terminal')
def terminal_disconnect():
    username = session.get("username", "unknown")
    
    # Đóng SSH channel an toàn
    if 'ssh_chan' in session:
        try:
            if session['ssh_chan'].active:
                session['ssh_chan'].close()
        except Exception as e:
            app.logger.warning(f"Error closing SSH channel for {username}: {e}")
        finally:
            session.pop('ssh_chan', None)
    
    # Đóng SSH client an toàn  
    if 'ssh_client' in session:
        try:
            session['ssh_client'].close()
        except Exception as e:
            app.logger.warning(f"Error closing SSH client for {username}: {e}")
        finally:
            session.pop('ssh_client', None)
            
    log_action(username, "Terminal: User disconnected")
#---KET THUC HAM ---

@require_auth('user')
@app.route('/user/<username>/editor/new', methods=['POST'])
@require_auth('user')
def new_file_api(username):
    # 1. PHẢI chuẩn hóa tên trước khi làm bất cứ việc gì
    safe_username = make_safe_name(username)
    
    if session.get('username') != username:
        return jsonify(success=False, error="Unauthorized"), 403

    data = request.get_json()
    filename = data.get("filename", "").strip()
    path = data.get("path", ".")

    if not filename or '..' in filename or '/' in filename:
        return jsonify(success=False, error="Tên file không hợp lệ"), 400

    if '.' not in filename:
        filename += '.ino'

    try:
        # 2. Dung lai bien username de lay tu db goc
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        # 3. Đường dẫn trong container phải dùng safe_username (/home/sinh_vien/...)
        filepath = os.path.join("/home", safe_username, path, filename)

        try:
            sftp.stat(filepath)
            sftp.close()
            client.close()
            return jsonify(success=False, error="File đã tồn tại"), 400
        except FileNotFoundError:
            pass

        with sftp.open(filepath, 'w') as f:
            f.write("")  

        sftp.close()
        client.close()
        
        # Log hành động dùng username gốc cho dễ đọc
        log_action(username, f"Create new file: {filepath}")
        return jsonify(success=True)
    except Exception as e:
        app.logger.error(f"New File Error for {safe_username}: {e}")
        return jsonify(success=False, error=str(e)), 500

# ---- KET THUC HAM ---


@app.route('/user/<username>/upload', methods=['POST'])
@require_auth('user')
def upload_files_alias(username):
    return upload_files_api(username)


@app.route('/user/<username>/debug-devices', methods=['GET'])
@require_auth('user')  
def debug_devices_api(username):
    """API debug để kiểm tra thiết bị có sẵn"""
    if session['username'] != username:
        return jsonify(error="Unauthorized"), 403
    
    # --- FIX: Dùng tên an toàn ---
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    
    try:
        # Kiểm tra trên host
        host_devices = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        
        # Kiểm tra trong container
        device_cmd = ["docker", "exec", cname, "ls", "/dev/tty*"]
        device_result = subprocess.run(device_cmd, capture_output=True, text=True, timeout=10)
        
        container_devices = []
        if device_result.returncode == 0:
            for line in device_result.stdout.split('\n'):
                if 'ttyUSB' in line or 'ttyACM' in line:
                    container_devices.append(line.strip())
        
        # Kiểm tra arduino-cli
        arduino_cmd = ["docker", "exec", cname, "arduino-cli", "board", "list"]
        arduino_result = subprocess.run(arduino_cmd, capture_output=True, text=True, timeout=10)
        
        # Kiểm tra quyền user (dùng safe_username vì user trong linux docker cũng là safe_name)
        perm_cmd = ["docker", "exec", cname, "groups", safe_username]
        perm_result = subprocess.run(perm_cmd, capture_output=True, text=True, timeout=5)
        
        return jsonify({
            'success': True,
            'host_devices': host_devices,
            'container_devices': container_devices,
            'arduino_cli_output': arduino_result.stdout,
            'arduino_cli_error': arduino_result.stderr,
            'user_groups': perm_result.stdout.strip() if perm_result.returncode == 0 else "Error"
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/user/<username>/fix-permissions', methods=['POST'])
@require_auth('user')
def fix_permissions_api(username):
    """API để sửa quyền truy cập thiết bị"""
    if session['username'] != username:
        return jsonify(error="Unauthorized"), 403
    
    # --- FIX: Dùng tên an toàn ---
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    # -----------------------------
    
    try:
        # Thêm user vào group dialout (Dùng safe_username cho user Linux bên trong)
        cmd1 = ["docker", "exec", cname, "usermod", "-a", "-G", "dialout", safe_username]
        result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=10)
        
        # Set quyền cho serial devices
        cmd2 = ["docker", "exec", cname, "sh", "-c", "chmod 666 /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true"]
        result2 = subprocess.run(cmd2, capture_output=True, text=True, timeout=10)
        
        log_action(username, "Fix device permissions")
        return jsonify({
            'success': True, 
            'message': "Đã sửa quyền truy cập thiết bị",
            'details': {
                'usermod_output': result1.stdout + result1.stderr,
                'chmod_output': result2.stdout + result2.stderr
            }
        })
            
    except Exception as e:
        app.logger.error(f"Fix permissions error for {username}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Ánh xạ ID của nhà sản xuất/sản phẩm sang tên gọi thân thiện
DEVICE_ID_MAP = {
    "1a86:7523": {"type": "CH340/CH341", "tag_prefix": "USB-SERIAL-CH340"},
    "10c4:ea60": {"type": "CP2102", "tag_prefix": "USB-UART-CP2102"},
    "0403:6001": {"type": "FTDI", "tag_prefix": "FTDI-Device"},
    "2341:0043": {"type": "Arduino Uno", "tag_prefix": "Arduino-Uno"},
}

# ▼▼▼ TÌM HÀM require_internal_secret VÀ THAY THẾ BẰNG ĐOẠN NÀY ▼▼▼
def require_internal_secret(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Đảm bảo secret này khớp 100% với file udev_listener.py
        INTERNAL_API_SECRET = 'yiehfoie9f5feifh' 
        
        if request.headers.get('X-Internal-Secret') != INTERNAL_API_SECRET:
            log_action('internal_api', 'Unauthorized hardware event', success=False, details={'ip': request.remote_addr, 'reason': 'Invalid secret key'})
            return jsonify(success=False, error="Unauthorized - Invalid Secret Key"), 403
        return f(*args, **kwargs)
    return decorated_function
# --- KET THUV HAM ^^ ---


@app.route('/api/hardware/event', methods=['POST'])
@require_internal_secret
def hardware_event_api():
    data = request.get_json()
    port = data.get("port") # ví dụ: /dev/ttyUSB0
    vendor_id = data.get("vendor_id")
    product_id = data.get("product_id")
    event_type = data.get("event_type", "add") # 'add' hoặc 'remove'

    if not port:
        return jsonify(success=False, error="Missing port information"), 400

    db = get_db_connection()
    if not db: return jsonify(success=False, error="Database connection failed"), 500
    cur = db.cursor(dictionary=True)

    if event_type == "add":
        device_key = f"{vendor_id}:{product_id}"
        device_info = DEVICE_ID_MAP.get(device_key, { "type": "Generic USB-Serial", "tag_prefix": f"GENERIC-{vendor_id}-{product_id}" })
        
        # Tạo tag_name duy nhất và thân thiện
        tag_name = f"{device_info['tag_prefix']}-{port.split('/')[-1]}"
        device_type = device_info['type']
        
        try:
            cur.execute("SELECT id FROM hardware_devices WHERE port = %s", (port,))
            existing_device = cur.fetchone()

            if existing_device:
                cur.execute("UPDATE hardware_devices SET tag_name = %s, type = %s, status = 'available' WHERE id = %s", (tag_name, device_type, existing_device['id']))
                log_action('udev_listener', f"Hardware re-connected: {port}", success=True, details=data)
            else:
                cur.execute("INSERT INTO hardware_devices (tag_name, type, port, status) VALUES (%s, %s, %s, 'available')", (tag_name, device_type, port))
                log_action('udev_listener', f"New hardware detected: {port}", success=True, details=data)
            
            db.commit()
            return jsonify(success=True, message=f"Device {tag_name} on {port} registered.")
        finally:
            cur.close(), db.close()

    elif event_type == "remove":
        try:
            # Khi rút thiết bị, cập nhật trạng thái là 'maintenance' (bảo trì) thay vì xóa hẳn
            cur.execute("UPDATE hardware_devices SET status = 'maintenance', in_use_by = NULL WHERE port = %s", (port,))
            db.commit()
            log_action('udev_listener', f"Hardware removed: {port}", success=True, details=data)
            return jsonify(success=True, message=f"Device on {port} marked as removed.")
        finally:
            cur.close(), db.close()
    
@app.route('/api/hardware/rescan', methods=['POST'])
def hardware_rescan_api():
    try:
        # Lấy danh sách các cổng đang thực sự tồn tại trên máy chủ
        physical_ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        physical_ports_set = set(physical_ports)

        db = get_db_connection()
        if not db:
            return jsonify(success=False, error="Database connection failed"), 500

        cur = db.cursor(dictionary=True)

        # Lấy tất cả các cổng đang có trong database
        cur.execute("SELECT port FROM hardware_devices")
        db_ports_set = {row['port'] for row in cur.fetchall()}

        # Các cổng cần thêm vào DB (có trên máy nhưng chưa có trong DB)
        ports_to_add = physical_ports_set - db_ports_set
        # Các cổng cần cập nhật trạng thái (đã có trong DB nhưng không còn trên máy)
        ports_to_remove = db_ports_set - physical_ports_set

        added_count = 0
        for port in ports_to_add:
            # Dùng logic đơn giản để tạo tên, có thể cải thiện sau
            tag_name = f"Device-{port.split('/')[-1]}"
            device_type = "Auto-Scanned"
            cur.execute(
                "INSERT INTO hardware_devices (tag_name, type, port, status) VALUES (%s, %s, %s, 'available') ON DUPLICATE KEY UPDATE status='available'",
                (tag_name, device_type, port)
            )
            added_count += 1

        removed_count = 0
        if ports_to_remove:
            # Chuyển trạng thái các cổng đã bị rút ra thành 'maintenance'
            query = "UPDATE hardware_devices SET status = 'maintenance' WHERE port IN ({})".format(
                ', '.join(['%s'] * len(ports_to_remove))
            )
            cur.execute(query, tuple(ports_to_remove))
            removed_count = cur.rowcount

        db.commit()
        cur.close()
        db.close()

        message = f"Rescan complete. Added: {added_count}, Removed: {removed_count}."
        log_action('watcher_script', message, success=True)
        return jsonify(success=True, message=message)

    except Exception as e:
        app.logger.error(f"Hardware rescan failed: {e}")
        return jsonify(success=False, error=str(e)), 500
# ================== SOCKET.IO FOR SERIAL MONITOR ==================
serial_sessions = {}
serial_threads = {}

# ================== SOCKET.IO FOR UPLOAD STATUS ==================
@socketio.on('connect', namespace='/upload_status')
def upload_status_connect():
    username = session.get("username")
    if not username:
        return False # Từ chối kết nối nếu chưa đăng nhập
    
    if username not in user_sids:
        user_sids[username] = []
    user_sids[username].append(request.sid)
    app.logger.info(f"User {username} connected for upload status with SID: {request.sid}")

@socketio.on('disconnect', namespace='/upload_status')
def upload_status_disconnect():
    username = session.get("username")
    if username and username in user_sids:
        if request.sid in user_sids[username]:
            user_sids[username].remove(request.sid)
            if not user_sids[username]:
                del user_sids[username]
    app.logger.info(f"User {username} disconnected from upload status with SID: {request.sid}")
def read_serial_data(sid, ser, username):
    """
    Background thread to read serial data. This thread should ONLY read.
    It should NOT be responsible for closing the connection.
    """
    app.logger.info(f"Starting serial read thread for {username} on {ser.port}")
    try:
        while True:
            # Kiểm tra xem kết nối có còn được quản lý hay không
            if sid not in serial_sessions or not serial_sessions[sid].is_open:
                break

            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                decoded_data = data.decode('utf-8', errors='ignore')
                socketio.emit('serial_data',
                              {'data': decoded_data},
                              namespace='/serial',
                              room=sid)
            
            socketio.sleep(0.05) # Dùng sleep của socketio để nhường quyền kiểm soát

    except serial.SerialException as e:
        app.logger.error(f"Serial port disconnected or error for {username}: {e}")
        socketio.emit('serial_error', {'error': f'Device on port {ser.port} disconnected.'}, namespace='/serial', room=sid)
    except Exception as e:
        app.logger.error(f"Unexpected error in serial thread for {username}: {e}")
    finally:
        # Thread này kết thúc, thông báo cho client để nó tự ngắt kết nối
        socketio.emit('force_disconnect', {}, namespace='/serial', room=sid)
        app.logger.info(f"Serial read thread for {username} has ended.")


@socketio.on('start_monitor', namespace='/serial')
def start_serial_monitor(data):
    username = session.get("username")
    if not username: return
    
    port = data.get('port')
    baud_rate = int(data.get('baud_rate', 9600))
    sid = request.sid
    
    if not port:
        emit('serial_error', {'error': 'Port is required'})
        return
        
    # Dọn dẹp session cũ trước khi bắt đầu cái mới
    stop_existing_monitor(sid)
    
    try:
        ser = serial.Serial(port=port, baudrate=baud_rate, timeout=0.1)
        serial_sessions[sid] = ser
        
        # Dùng socketio.start_background_task thay vì threading.Thread
        # để quản lý tốt hơn trong môi trường Flask-SocketIO
        socketio.start_background_task(target=read_serial_data, sid=sid, ser=ser, username=username)

        emit('status', {'message': f'Monitoring {port} @ {baud_rate} baud'})
    except serial.SerialException as e:
        app.logger.error(f"Cannot open {port}: {e}")
        emit('serial_error', {'error': f'Cannot open port {port}: {str(e)}'})
    except Exception as e:
        app.logger.error(f"Serial monitor error: {e}")
        emit('serial_error', {'error': f'Monitor error: {str(e)}'})

def stop_existing_monitor(sid):
    """
    Helper function to safely stop an existing monitor for a session.
    This is the ONLY place where ser.close() should be called.
    """
    if sid in serial_sessions:
        ser = serial_sessions.pop(sid, None)
        if ser and ser.is_open:
            try:
                ser.close()
                app.logger.info(f"Cleanly closed serial port {ser.port} for session {sid}.")
            except Exception as e:
                # Bắt lỗi nếu port đã bị đóng bởi OS
                app.logger.warning(f"Ignoring error while closing port in helper: {e}")
    
    # Xóa thread cũ khỏi danh sách quản lý
    serial_threads.pop(sid, None)

@socketio.on('disconnect', namespace='/serial')
def serial_disconnect():
    username = session.get("username", "unknown")
    sid = request.sid
    app.logger.info(f"User {username} disconnected. Cleaning up resources for {sid}.")
    stop_existing_monitor(sid)
def get_all_running_users():
    """Lấy danh sách username có container đang chạy theo format 'user-USERNAME'."""
    try:
        # Lệnh docker ps để liệt kê container có tên theo format 'user-...'
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}", "--filter", "name=user-"],
            capture_output=True, text=True, check=True
        )
        names = result.stdout.strip().split('\n')
        # Trích xuất username từ tên container 'user-USERNAME'
        users = [name.split('-', 1)[1] for name in names if name]
        return users
    except Exception as e:
        app.logger.error(f"Failed to get running user containers: {e}")
        return []

# rescan_hardware_and_update_db 
@app.route('/api/hardware/rescan', methods=['POST'])
def rescan_hardware_and_update_db():
    """
    Quét cổng USB, cập nhật DB và khởi động lại container nếu cần.
    """
    app.logger.info("Received device rescan request.")
    
    summary_message = "Scan complete."
    
    # --- PHẦN 1: QUÉT VÀ CẬP NHẬT DATABASE ---
    try:
        # 1. Quét thực tế
        physical_ports_list = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        physical_ports = set(physical_ports_list)
        app.logger.info(f"Physical scan found: {physical_ports}")

        db = get_db_connection()
        if db:
            cur = db.cursor(dictionary=True)

            # 2. Lấy DB hiện tại
            cur.execute("SELECT port, status FROM hardware_devices")
            db_ports = {row['port']: row['status'] for row in cur.fetchall()}

            # 3. Xử lý logic Thêm/Xóa
            # Cổng mới cắm vào -> Thêm vào DB
            for port in physical_ports:
                if port not in db_ports:
                    tag_name = f"Auto-{port.split('/')[-1]}"
                    cur.execute("INSERT INTO hardware_devices (tag_name, type, port, status) VALUES (%s, 'USB-Serial', %s, 'available')", (tag_name, port))
                elif db_ports[port] == 'maintenance':
                    # Cổng cắm lại -> Chuyển sang available
                    cur.execute("UPDATE hardware_devices SET status='available' WHERE port=%s", (port,))

            # Cổng bị rút ra -> Chuyển sang maintenance
            for port in db_ports:
                if port not in physical_ports and db_ports[port] != 'maintenance':
                    cur.execute("UPDATE hardware_devices SET status='maintenance', in_use_by=NULL WHERE port=%s", (port,))

            db.commit()
            cur.close()
            db.close()
    except Exception as e:
        app.logger.error(f"Error during DB update: {e}")

    # --- PHẦN 2: KHỞI ĐỘNG LẠI CONTAINER ĐỂ NHẬN DIỆN THIẾT BỊ MỚI ---
    # Docker container cần restart (hoặc dùng cgroup rules) để nhận thiết bị mới cắm vào
    try:
        running_users = get_all_running_users()
        if running_users:
            app.logger.info(f"Checking containers for users: {', '.join(running_users)}")
            for username in running_users:

                ensure_user_container_and_setup(username)

        return jsonify(success=True, message="Rescan and container sync complete.")

    except Exception as e:
        app.logger.error(f"Error checking user containers: {e}")
        return jsonify(success=False, error=str(e)), 500
# ket Thuc Ham

# ------ HAM CHAY NGAM THU HOI QUYEN TAT CONTAINER KHI TIMEOUT
def resource_cleanup_worker():
    while True:
        try:
            db = get_db_connection()
            if db:
                cur = db.cursor(dictionary=True)
                # Chỉ lấy những đứa THỰC SỰ hết hạn (khác NULL và nhỏ hơn hiện tại)
                cur.execute("""
                    SELECT da.id, u.username 
                    FROM device_assignments da
                    JOIN users u ON da.user_id = u.id
                    WHERE da.expires_at IS NOT NULL 
                      AND da.expires_at < NOW()
                      AND da.expires_at > '2000-01-01 00:00:00'
                """)
                expired = cur.fetchall()
                
                for item in expired:
                    username = item['username']
                    safe_username = make_safe_name(username)
                    cname = f"{safe_username}-dev"
                    
                    # Bước 1: Xóa quyền trong DB trước
                    cur.execute("DELETE FROM device_assignments WHERE id = %s", (item['id'],))
                    # Bước 2: Kiểm tra xem user còn quyền nào khác không rồi mới xóa container
                    cur.execute("SELECT COUNT(*) as count FROM device_assignments WHERE user_id = (SELECT id FROM users WHERE username=%s)", (username,))
                    if cur.fetchone()['count'] == 0:
                        subprocess.run(["docker", "rm", "-f", cname], check=False)
                        app.logger.info(f"[CLEANUP] Da xoa container het han cua: {username}")

                db.commit()
                cur.close(), db.close()
        except Exception as e:
            app.logger.error(f"Cleanup Error: {e}")
        time.sleep(60) 
# Khởi động luồng dọn dẹp khi Server chạy
# cleanup_thread = threading.Thread(target=resource_cleanup_worker, daemon=True)
# cleanup_thread.start()
#----KET THUC HAM ^^ ---
# ================== MAIN EXECUTION ==================
if __name__ == "__main__":
    init_db()
    app.logger.info("Enhanced Flask App with Security Features Started")
    # Dùng socketio.run thay cho app.run
    socketio.run(app, host="::", port=5000, debug=True)