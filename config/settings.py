"""
Configuration settings for the Flask application
"""
import os
from dotenv import load_dotenv

# Load .env file using absolute path relative to project root
basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_path = os.path.join(basedir, '.env')
load_dotenv(env_path)

# ================== CONFIGURATIONS ==================
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

# List of default Arduino libraries to pre-install for all users.
DEFAULT_ARDUINO_LIBRARIES = [
    "Adafruit NeoPixel", 
    "DHT sensor library", 
    "Adafruit Unified Sensor", 
    "PubSubClient", 
    "ArduinoJson"
]

# System constants for Docker Environments
SYSTEM_CONFIG = {
    'BASE_SSH_PORT': int(os.getenv('BASE_SSH_PORT', 2000)),
    'MAX_WORKSPACE_FILE_SIZE': 5242880,  # 5MB
    'AI_GRADER_TIMEOUT': 45,             # seconds
}

