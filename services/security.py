"""
Security service: CSRF, OTP, Captcha, Password validation
"""
import secrets
import time
import random
import base64
import re
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import defaultdict
from flask import request
from config import SECURITY_CONFIG, EMAIL_CONFIG
import logging

logger = logging.getLogger(__name__)

# In-memory storage
csrf_tokens = {}
otp_storage = {}
login_attempts = defaultdict(lambda: {'count': 0, 'locked_until': None})
rate_limiter = defaultdict(lambda: {'requests': [], 'blocked_until': None})

# ================== CSRF TOKEN ==================
def generate_csrf_token():
    """Generate a new CSRF token"""
    token = secrets.token_urlsafe(32)
    csrf_tokens[token] = {
        'created_at': time.time(), 
        'user_ip': request.remote_addr if request else None
    }
    
    # Clean expired tokens
    expired = [t for t, data in list(csrf_tokens.items()) 
               if time.time() - data['created_at'] > SECURITY_CONFIG['CSRF_EXPIRY']]
    for t in expired: 
        del csrf_tokens[t]
    
    return token

def validate_csrf_token(token):
    """Validate CSRF token"""
    if not token or token not in csrf_tokens: 
        return False
    if time.time() - csrf_tokens[token]['created_at'] > SECURITY_CONFIG['CSRF_EXPIRY']:
        del csrf_tokens[token]
        return False
    return True

# ================== CAPTCHA ==================
def generate_captcha():
    """Generate captcha challenge"""
    chars = string.digits + string.ascii_lowercase + string.ascii_uppercase
    captcha = ''.join(random.choices(chars, k=6))
    token = base64.b64encode(f"{captcha}:{time.time()}".encode()).decode()
    return captcha, token

def validate_captcha(user_input, token):
    """Validate captcha response"""
    try:
        decoded = base64.b64decode(token.encode()).decode()
        captcha, timestamp = decoded.split(':', 1)
        if time.time() - float(timestamp) > 300: 
            return False
        return user_input.upper() == captcha.upper()
    except: 
        return False

# ================== OTP ==================
def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join(random.choices('0123456789', k=6))

def send_otp_email(email, otp, username):
    """Send OTP via email"""
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_CONFIG['FROM_EMAIL']
        msg['To'] = email
        msg['Subject'] = "EPU Tech - Mã xác thực"
        
        body = f"Xin chào {username},\n\nMã xác thực của bạn là: {otp}\n\nMã này có hiệu lực trong 5 phút."
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(EMAIL_CONFIG['SMTP_SERVER'], EMAIL_CONFIG['SMTP_PORT'])
        server.starttls()
        server.login(EMAIL_CONFIG['SMTP_USERNAME'], EMAIL_CONFIG['SMTP_PASSWORD'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"EMAIL SEND ERROR: {e}")
        return False

# ================== PASSWORD VALIDATION ==================
def validate_password_strength(password):
    """Validate password strength"""
    if len(password) < SECURITY_CONFIG['PASSWORD_MIN_LENGTH']: 
        return False, "Mật khẩu phải dài ít nhất 8 ký tự"
    if not re.search("[a-z]", password): 
        return False, "Mật khẩu phải chứa chữ thường"
    if not re.search("[A-Z]", password): 
        return False, "Mật khẩu phải chứa chữ HOA"
    if not re.search("[0-9]", password): 
        return False, "Mật khẩu phải chứa số"
    return True, ""
