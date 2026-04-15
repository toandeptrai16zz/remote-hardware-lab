"""
Cấu hình cho ứng dụng Flask - by Chương
"""
import os
from dotenv import load_dotenv

# Tải file .env sử dụng đường dẫn tuyệt đối - by Chương
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(basedir, '.env')
load_dotenv(env_path)

# ================== CÁC CẤU HÌNH - by Chương ==================
SECURITY_CONFIG = {
    'MAX_LOGIN_ATTEMPTS': 5, 
    'LOCKOUT_DURATION': 300, 
    'OTP_EXPIRY': 300,
    'SESSION_TIMEOUT': 1800, 
    'CSRF_EXPIRY': 3600, 
    'PASSWORD_MIN_LENGTH': 8,
    'USERNAME_MIN_LENGTH': 3, 
    'RATE_LIMIT_PER_MINUTE': 60,
}

EMAIL_CONFIG = {
    'SMTP_SERVER': os.getenv('SMTP_SERVER', 'smtp.gmail.com'), 
    'SMTP_PORT': int(os.getenv('SMTP_PORT', 587)),
    'SMTP_USERNAME': os.getenv('SMTP_USERNAME'),
    'SMTP_PASSWORD': os.getenv('SMTP_PASSWORD'),
    'FROM_EMAIL': os.getenv('FROM_EMAIL', 'EPU TECH')
}

# Danh sách các thư viện Arduino mặc định sẽ được cài đặt sẵn - by Chương
DEFAULT_ARDUINO_LIBRARIES = [
    "Adafruit NeoPixel", 
    "DHT sensor library", 
    "Adafruit Unified Sensor", 
    "PubSubClient", 
    "ArduinoJson"
]

# Các hằng số hệ thống cho môi trường Docker ảo hóa máy ảo - by Chương
SYSTEM_CONFIG = {
    'BASE_SSH_PORT': int(os.getenv('BASE_SSH_PORT', 2000)),
    'MAX_WORKSPACE_FILE_SIZE': 5242880,  # 5MB
    'AI_GRADER_TIMEOUT': 45,             # seconds
}

# Các file hệ thống bị ẩn không cho người dùng thấy - by Chương
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
    ".sudo_as_admin_successful",
    "Arduino",
    ".arduino15",
    "sketchbook"
}

