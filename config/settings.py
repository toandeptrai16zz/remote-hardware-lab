"""
Configuration settings for the Flask application
"""

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
    'SMTP_SERVER': 'smtp.gmail.com', 
    'SMTP_PORT': 587,
    'SMTP_USERNAME': 'haquangchuong28@gmail.com',
    'SMTP_PASSWORD': 'ctuo nyxx clvg xxtc',
    'FROM_EMAIL': 'EPU TECH'
}

# List of default Arduino libraries to pre-install for all users.
DEFAULT_ARDUINO_LIBRARIES = [
    "Adafruit NeoPixel", 
    "DHT sensor library", 
    "Adafruit Unified Sensor", 
    "PubSubClient", 
    "ArduinoJson"
]

# Internal API secret for hardware events
INTERNAL_API_SECRET = 'yiehfoie9f5feifh'

# Hidden system files that should not be shown to users
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

# Device ID mapping for hardware identification
DEVICE_ID_MAP = {
    "1a86:7523": {"type": "CH340/CH341", "tag_prefix": "USB-SERIAL-CH340"},
    "10c4:ea60": {"type": "CP2102", "tag_prefix": "USB-UART-CP2102"},
    "0403:6001": {"type": "FTDI", "tag_prefix": "FTDI-Device"},
    "2341:0043": {"type": "Arduino Uno", "tag_prefix": "Arduino-Uno"},
}
