"""
Authentication routes: login, register, OTP verification
"""
import sys
import time
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from config import get_db_connection, SECURITY_CONFIG
from services import (
    generate_csrf_token, validate_csrf_token,
    generate_captcha, validate_captcha,
    generate_otp, send_otp_email,
    validate_password_strength,
    otp_storage, log_action
)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login")
def login_page():
    """Show login page"""
    return render_template("login.html")

@auth_bp.route("/api/generate-csrf", methods=["GET"])
def generate_csrf_api():
    """Generate CSRF token API"""
    return jsonify({'csrf_token': generate_csrf_token()})

@auth_bp.route("/api/login", methods=["POST"])
def login_api():
    """Login API endpoint"""
    # Debug logging
    print(f"--- LOGIN REQUEST ---", file=sys.stderr)
    print(f"Content-Type: {request.content_type}", file=sys.stderr)
    
    # Get data from JSON or Form
    data = {}
    if request.is_json:
        print("Data Source: JSON", file=sys.stderr)
        data = request.get_json()
    else:
        print("Data Source: FORM", file=sys.stderr)
        data = request.form

    # Extract fields
    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()
    captcha = data.get("captcha", "").strip()
    captcha_token = data.get("captcha_token", "")
    csrf_token = data.get("csrf_token", "")
    
    ip_address = request.remote_addr

    # Validate required fields
    missing = []
    if not username: missing.append("username")
    if not password: missing.append("password")
    if not captcha: missing.append("captcha")
    if not captcha_token: missing.append("captcha_token")
    if not csrf_token: missing.append("csrf_token")
    
    if missing:
        print(f"❌ MISSING FIELDS: {missing}", file=sys.stderr)
        return jsonify({'success': False, 'message': f'Thiếu thông tin: {", ".join(missing)}'}), 400

    # Validate tokens
    if not validate_csrf_token(csrf_token):
        print("❌ Invalid CSRF Token", file=sys.stderr)
        return jsonify({'success': False, 'message': 'Token bảo mật không hợp lệ'}), 400
        
    if not validate_captcha(captcha, captcha_token):
        print(f"❌ Invalid Captcha. Input: {captcha}", file=sys.stderr)
        return jsonify({'success': False, 'message': 'Mã xác thực không đúng'}), 400

    # Database authentication
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE username=%s", (username,))
    user = cur.fetchone()

    if user and check_password_hash(user['password'], password):
        if user["status"] == "active":
            cur.execute("UPDATE users SET last_login=NOW() WHERE id=%s", (user['id'],))
            db.commit()
            
            if user.get('email'):
                # Send OTP
                otp = generate_otp()
                otp_storage[username] = {
                    'otp': otp, 
                    'expires_at': time.time() + SECURITY_CONFIG['OTP_EXPIRY'], 
                    'ip': ip_address
                }
                send_otp_email(user['email'], otp, username)
                log_action(username, "Login: OTP sent")
                cur.close(), db.close()
                return jsonify({'success': True, 'requireOTP': True})
            else:
                # Direct login without OTP
                session["username"] = user["username"]
                session["role"] = user["role"]
                session["last_activity"] = time.time()
                log_action(username, "Login: Success")
                cur.close(), db.close()
                redirect_url = url_for('admin.admin_dashboard' if user['role'] == 'admin' else 'user.user_redirect')
                return jsonify({'success': True, 'requireOTP': False, 'redirect': redirect_url})
        else:
            cur.close(), db.close()
            return jsonify({'success': False, 'message': 'Tài khoản đã bị khóa hoặc đang chờ xử lý.'}), 403
    else:
        cur.close(), db.close()
        log_action(username, "Login: Failed", False)
        return jsonify({'success': False, 'message': 'Sai tài khoản hoặc mật khẩu!'}), 401

@auth_bp.route("/api/verify-otp", methods=["POST"])
def verify_otp():
    """Verify OTP code"""
    otp = request.json.get('otp')
    username = next((user for user, data in otp_storage.items() 
                    if data.get('ip') == request.remote_addr), None)
    
    if not username or username not in otp_storage: 
        return jsonify({'success': False, 'error': 'Không tìm thấy phiên OTP'}), 400
    
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
            session["username"] = user["username"]
            session["role"] = user["role"]
            session["last_activity"] = time.time()
            otp_storage.pop(username, None)
            log_action(username, "Login: OTP verified")
            redirect_url = url_for('admin.admin_dashboard' if user['role'] == 'admin' else 'user.user_redirect')
            return jsonify({'success': True, 'redirect': redirect_url})
    
    return jsonify({'success': False, 'error': 'Mã OTP không đúng'}), 400

@auth_bp.route("/api/resend-otp", methods=["POST"])
def resend_otp_api():
    """Resend OTP for both registration and login"""
    # CASE 1: During registration (data in session)
    if 'registration_data' in session:
        try:
            reg_data = session['registration_data']
            new_otp = generate_otp()
            
            reg_data['otp'] = new_otp
            reg_data['expires_at'] = time.time() + SECURITY_CONFIG['OTP_EXPIRY']
            session['registration_data'] = reg_data
            
            if send_otp_email(reg_data['email'], new_otp, reg_data['username']):
                return jsonify({'success': True, 'message': 'Đã gửi lại mã OTP vào email đăng ký.'})
            else:
                return jsonify({'success': False, 'message': 'Lỗi hệ thống gửi email.'}), 500
        except Exception as e:
            return jsonify({'success': False, 'message': 'Lỗi không xác định.'}), 500

    # CASE 2: During login (data in otp_storage)
    data = request.get_json(silent=True) or {}
    username = data.get("username")
    
    if not username:
        username = next((u for u, d in otp_storage.items() 
                        if d.get('ip') == request.remote_addr), None)

    if username:
        try:
            db = get_db_connection()
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT email FROM users WHERE username=%s", (username,))
            user = cur.fetchone()
            cur.close()
            db.close()
            
            if user and user['email']:
                new_otp = generate_otp()
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
                return jsonify({'success': False, 'message': 'Không tìm thấy email liên kết.'}), 400
        except Exception as e:
            return jsonify({'success': False, 'message': 'Lỗi Database.'}), 500
            
    return jsonify({'success': False, 'message': 'Không tìm thấy phiên xác thực.'}), 400

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """User registration with OTP"""
    if "username" in session: 
        return redirect(url_for("index"))
    
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"].strip()
        email = request.form.get("email", "").strip()
        
        is_strong, message = validate_password_strength(password)
        if not is_strong:
            flash(message, "error")
            return redirect(url_for("auth.register"))
        
        if not email:
            flash("Vui lòng nhập email để xác thực.", "error")
            return redirect(url_for("auth.register"))

        db = get_db_connection()
        cur = db.cursor()
        cur.execute("SELECT id FROM users WHERE username=%s OR email=%s", (username, email))
        if cur.fetchone():
            flash("Username hoặc Email đã tồn tại!", "error")
            cur.close(), db.close()
            return redirect(url_for("auth.register"))

        otp = generate_otp()
        session['registration_data'] = {
            'username': username, 
            'password': generate_password_hash(password), 
            'email': email,
            'otp': otp, 
            'expires_at': time.time() + SECURITY_CONFIG['OTP_EXPIRY']
        }
        send_otp_email(email, otp, username)
        log_action(username, f"Register: OTP sent to {email}")
        return redirect(url_for('auth.verify_email'))
    
    return render_template("register.html")

@auth_bp.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    """Verify email with OTP during registration"""
    if 'registration_data' not in session: 
        return redirect(url_for('auth.register'))
    
    reg_data = session['registration_data']
    if time.time() > reg_data['expires_at']:
        session.pop('registration_data', None)
        flash("Mã OTP đã hết hạn. Vui lòng đăng ký lại.", "error")
        return redirect(url_for('auth.register'))
    
    if request.method == 'POST' and request.form.get('otp', '') == reg_data['otp']:
        db = get_db_connection()
        cur = db.cursor()

        # Insert with pending status (requires admin approval)
        cur.execute(
            "INSERT INTO users(username, password, email, status, role) VALUES(%s, %s, %s, 'pending', 'user')",
            (reg_data['username'], reg_data['password'], reg_data['email'])
        )

        db.commit()
        cur.close(), db.close()
        log_action(reg_data['username'], "Register success, pending approval")
        session.pop('registration_data', None)

        flash("Xác thực và đăng ký thành công! Tài khoản của bạn đang chờ quản trị viên phê duyệt.", "success")
        return redirect(url_for('auth.login_page'))

    elif request.method == 'POST':
        flash("Mã OTP không chính xác!", "error")
    
    return render_template('verify_email.html', email=reg_data['email'])

@auth_bp.route("/logout")
def logout():
    """Logout user"""
    log_action(session.get("username", "unknown"), "Logout: Success")
    session.clear()
    flash("Đã đăng xuất.", "info")
    return redirect(url_for("auth.login_page"))
