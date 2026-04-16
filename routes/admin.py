"""
Admin routes: dashboard, user management, device management
"""
import os
import shutil
import subprocess
import io
import pandas as pd
from math import ceil
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash
import mysql.connector
from utils import require_auth, make_safe_name
from config import get_db_connection
from services import log_action

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route("/")
@require_auth('admin')
def admin_dashboard():
    """Admin dashboard with statistics"""
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    
    # Get user statistics
    cur.execute("SELECT status, COUNT(*) as count FROM users GROUP BY status")
    stats = {row['status']: row['count'] for row in cur.fetchall()}
    
    # Get recent logs
    cur.execute("SELECT * FROM logs ORDER BY timestamp DESC LIMIT 50")
    logs = cur.fetchall()
    
    cur.close(), db.close()
    
    return render_template("admin.html", 
                           total_users=sum(stats.values()),
                           active_users=stats.get('active', 0),
                           blocked_users=stats.get('blocked', 0),
                           pending_users=stats.get('pending', 0),
                           logs=logs)

@admin_bp.route("/manage")
@require_auth('admin')
def admin_manage():
    """User management page with pagination and search"""
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
    
    # Get total count
    cur.execute(f"SELECT COUNT(id) as total {base_query}", (search_term, search_term))
    total_users = cur.fetchone()['total']
    total_pages = ceil(total_users / per_page) if total_users > 0 else 1

    # Get users for current page
    query = f"SELECT id, username, email, role, status, created_at {base_query} ORDER BY created_at DESC LIMIT %s OFFSET %s"
    cur.execute(query, (search_term, search_term, per_page, offset))
    users = cur.fetchall()
    
    cur.close(), db.close()
    return render_template("manage.html", users=users, page=page, total_pages=total_pages, search_query=search_query)

@admin_bp.route("/approve")
@require_auth('admin')
def admin_approve_page():
    """Page to approve pending users"""
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, username, email, created_at FROM users WHERE status = 'pending' ORDER BY created_at DESC")
    users = cur.fetchall()
    cur.close(), db.close()
    return render_template("approve.html", users=users)

@admin_bp.route("/api/logs")
@require_auth('admin')
def admin_api_logs():
    """API to get recent logs"""
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT username, action, ip_address, timestamp FROM logs ORDER BY timestamp DESC LIMIT 50")
    logs = cur.fetchall()
    cur.close(), db.close()
    
    for log in logs: 
        log['timestamp'] = log['timestamp'].isoformat()
    
    return jsonify({'success': True, 'logs': logs})

@admin_bp.route("/add_user", methods=["POST"])
@require_auth('admin')
def add_user():
    """Add new user (admin only)"""
    from services import validate_password_strength
    
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    email = request.form.get("email", "").strip() or None
    role = request.form.get("role", "user")
    
    is_strong, message = validate_password_strength(password)
    if not is_strong:
        flash(message, "error")
        return redirect(url_for("admin.admin_manage"))
    
    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute(
            "INSERT INTO users(username, password, email, role, status) VALUES(%s, %s, %s, %s, 'active')",
            (username, generate_password_hash(password), email, role)
        )
        db.commit()
        flash(f"Đã thêm user '{username}' thành công!", "success")
    except mysql.connector.Error as err:
        db.rollback()
        if err.errno == 1062:
            flash("Tên đăng nhập hoặc email đã tồn tại!", "error")
        else:
            flash(f"Lỗi hệ thống: {err}", "error")
    finally:
        cur.close()
        db.close()
    
    return redirect(url_for("admin.admin_manage"))

@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@require_auth('admin')
def delete_user(user_id):
    """Delete user and cleanup container/files"""
    db = get_db_connection()
    if not db: 
        return jsonify(success=False, error="Database connection error"), 500
    
    cur = db.cursor(dictionary=True)
    
    # Get username
    cur.execute("SELECT username FROM users WHERE id=%s", (user_id,))
    user = cur.fetchone()
    
    if user:
        username_raw = user['username']
        safe_username = make_safe_name(username_raw)
        cname = f"{safe_username}-dev"
        host_user_dir = f"/home/toan/QUAN_LY_USER/{safe_username}"

        from flask import current_app
        current_app.logger.info(f"Admin action: Deleting user {username_raw} (Safe name: {safe_username})")

        # Remove Docker container
        try:
            subprocess.run(["docker", "rm", "-f", cname], check=False, timeout=15)
            current_app.logger.info(f"Removed container: {cname}")
        except Exception as e:
            current_app.logger.error(f"Failed to remove container {cname}: {e}")
        
        # Remove user directory
        try:
            if os.path.exists(host_user_dir):
                shutil.rmtree(host_user_dir)
                current_app.logger.info(f"Deleted directory: {host_user_dir}")
            else:
                current_app.logger.warning(f"Directory not found, skipping: {host_user_dir}")
        except Exception as e:
            current_app.logger.error(f"Failed to delete directory {host_user_dir}: {e}")

        # Remove from database
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        db.commit()
        
        log_action(session["username"], f"Deleted user '{username_raw}' and folder '{safe_username}'")
        flash(f"Đã xóa hoàn toàn user '{username_raw}' và thư mục dữ liệu.", "success")
    else:
        flash("Người dùng không tồn tại!", "error")
        
    cur.close()
    db.close()
    return redirect(url_for("admin.admin_manage"))

@admin_bp.route("/change_user_status/<action>/<username>", methods=["POST"])
@require_auth('admin')
def change_user_status(action, username):
    """Change user status (approve/block/unblock)"""
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
    redirect_to = request.form.get('next') or url_for("admin.admin_manage")
    return redirect(redirect_to)

@admin_bp.route("/api/users")
@require_auth('admin')
def admin_api_get_users():
    """API to get active users for mission assignment"""
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, username FROM users WHERE role = 'user' AND status = 'active' ORDER BY username")
    users = cur.fetchall()
    cur.close()
    db.close()
    return jsonify(users)

# ==================== MISSIONS ====================

@admin_bp.route("/missions")
@require_auth('admin')
def admin_missions_page():
    """Missions management page"""
    return render_template("admin/missions.html")

@admin_bp.route("/api/missions", methods=['POST'])
@require_auth('admin')
def admin_api_create_mission():
    """API to create mission / exam and assign to users"""
    data = request.get_json()
    mission_name = data.get('mission_name')
    mission_type = data.get('type', 'assignment')
    description = data.get('description', '')
    duration_minutes = int(data.get('duration_minutes', 90))
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    user_ids = data.get('user_ids')

    if not all([mission_name, user_ids, start_time, end_time]):
        return jsonify(success=False, error="Vui lòng điền tên mission, chọn thời gian và ít nhất một user."), 400

    if not isinstance(user_ids, list):
        return jsonify(success=False, error="Dữ liệu danh sách user không hợp lệ."), 400

    db = get_db_connection()
    cur = db.cursor()
    
    success_count = 0

    try:
        cur.execute(
            "INSERT INTO missions (name, description, type, duration_minutes, start_time, end_time) VALUES (%s, %s, %s, %s, %s, %s)",
            (mission_name, description, mission_type, duration_minutes, start_time, end_time)
        )
        mission_id = cur.lastrowid
        
        for user_id in user_ids:
            cur.execute("INSERT IGNORE INTO mission_assignments (mission_id, user_id) VALUES (%s, %s)", 
                       (mission_id, user_id))
            if cur.rowcount > 0:
                success_count += 1

        db.commit()
    except Exception as e:
        db.rollback()
        cur.close()
        db.close()
        return jsonify(success=False, error=str(e)), 500

    cur.close()
    db.close()
    
    try:
        from flask import current_app
        socket = current_app.extensions.get('socketio')
        if socket:
            socket.emit('new_mission', {'mission_name': mission_name})
    except Exception:
        pass
    
    log_action(session['username'], f"Tạo mission '{mission_name}' [ID: {mission_id}] và giao cho {success_count} user.")
    message = f"Tạo mission '{mission_name}' hoàn tất. Đã cấp quyền cho {success_count} user."
    return jsonify(success=True, message=message)

@admin_bp.route("/api/missions", methods=['GET'])
@require_auth('admin')
def admin_api_get_missions():
    """API to get all missions with submission stats"""
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT m.*,
               COUNT(DISTINCT ma.user_id) AS assigned_count,
               COUNT(DISTINCT s.id)       AS submitted_count
        FROM missions m
        LEFT JOIN mission_assignments ma ON ma.mission_id = m.id
        LEFT JOIN submissions s          ON s.mission_id  = m.id
        GROUP BY m.id
        ORDER BY m.created_at DESC
    """)
    missions = cur.fetchall()
    cur.close()
    db.close()

    for m in missions:
        m['created_at'] = m['created_at'].isoformat() if m['created_at'] else None
        m['start_time'] = m['start_time'].isoformat() if m['start_time'] else None
        m['end_time'] = m['end_time'].isoformat() if m['end_time'] else None

    return jsonify(missions)


@admin_bp.route("/api/missions/<int:mission_id>", methods=['DELETE'])
@require_auth('admin')
def admin_api_delete_mission(mission_id):
    db = get_db_connection()
    cur = db.cursor()
    cur.execute("DELETE FROM mission_assignments WHERE mission_id = %s", (mission_id,))
    cur.execute("DELETE FROM submissions WHERE mission_id = %s", (mission_id,))
    cur.execute("DELETE FROM missions WHERE id = %s", (mission_id,))
    db.commit()
    cur.close()
    db.close()
    log_action(session['username'], f"Xóa mission ID: {mission_id}")
    return jsonify(success=True, message="Đã xóa bài thi thành công.")

@admin_bp.route("/api/missions/<int:mission_id>", methods=['PUT'])
@require_auth('admin')
def admin_api_update_mission(mission_id):
    data = request.get_json()
    db = get_db_connection()
    cur = db.cursor()
    try:
        cur.execute("UPDATE missions SET name=%s, description=%s, type=%s, duration_minutes=%s, start_time=%s, end_time=%s WHERE id=%s",
            (data.get('mission_name'), data.get('description'), data.get('type'), int(data.get('duration_minutes', 90)), data.get('start_time'), data.get('end_time'), mission_id)
        )
        if data.get('user_ids'):
            cur.execute("DELETE FROM mission_assignments WHERE mission_id=%s", (mission_id,))
            for uid in data.get('user_ids'):
                cur.execute("INSERT IGNORE INTO mission_assignments (mission_id, user_id) VALUES (%s, %s)", (mission_id, uid))
        db.commit()
        success, message = True, "Cập nhật bài thi thành công"
        log_action(session['username'], f"Cập nhật mission ID: {mission_id}")
    except Exception as e:
        db.rollback()
        success, message = False, str(e)
    finally:
        cur.close()
        db.close()
    return jsonify(success=success, message=message)

@admin_bp.route("/api/missions/<int:mission_id>/export", methods=['GET'])
@require_auth('admin')
def admin_api_export_mission(mission_id):
    """API to export mission grades to Excel"""
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    
    # Get mission details
    cur.execute("SELECT name FROM missions WHERE id = %s", (mission_id,))
    mission = cur.fetchone()
    if not mission:
        cur.close()
        db.close()
        return "Mission not found", 404
        
    # Get submission details
    query = """
        SELECT u.username, u.email, s.score, s.submitted_at, s.is_auto_submit
        FROM mission_assignments ma
        JOIN users u ON ma.user_id = u.id
        LEFT JOIN submissions s ON ma.mission_id = s.mission_id AND ma.user_id = s.user_id
        WHERE ma.mission_id = %s
        ORDER BY u.username
    """
    cur.execute(query, (mission_id,))
    submissions = cur.fetchall()
    cur.close()
    db.close()
    
    # Prepare DataFrame
    data = []
    for sub in submissions:
        data.append({
            'Tài khoản': sub['username'],
            'Email': sub['email'],
            'Điểm': sub['score'] if sub['score'] is not None else 'Chưa có điểm',
            'Trạng thái': 'Đã nộp tự động' if sub['is_auto_submit'] else ('Đã nộp' if sub['submitted_at'] else 'Chưa nộp'),
            'Thời gian nộp': sub['submitted_at'].strftime('%Y-%m-%d %H:%M:%S') if sub['submitted_at'] else ''
        })
        
    df = pd.DataFrame(data)
    
    # Write to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Grades')
    output.seek(0)
    
    safe_mission_name = make_safe_name(mission['name'])
    filename = f"Ket_qua_{safe_mission_name}.xlsx"
    
    log_action(session['username'], f"Xuất điểm mission '{mission['name']}' ra Excel")
    
    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# ==================== DEVICES (HARDWARE-FLASH FEATURE) ====================

@admin_bp.route("/devices")
@require_auth('admin')
def admin_devices_page():
    """Devices management page for hardware flashing feature"""
    return render_template("admin/devices.html")

@admin_bp.route("/api/devices/scan", methods=['POST'])
@require_auth('admin')
def admin_api_scan_devices():
    """Tự động quét các cổng USB vật lý đang cắm vào Server và đồng bộ vào CSDL"""
    import glob
    ports = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    db = get_db_connection()
    cur = db.cursor()
    
    new_count = 0
    for i, port in enumerate(ports):
        # Tự động cấp tên Tag theo tên cổng USB
        tag = f"Phần cứng vật lý ({os.path.basename(port)})"
        board_type = "esp32" if "USB" in port else "arduino"
        try:
            cur.execute("INSERT IGNORE INTO hardware_devices (tag_name, type, port, status) VALUES (%s, %s, %s, 'available')",
                       (tag, board_type, port))
            if cur.rowcount > 0:
                new_count += 1
        except Exception as e:
            pass
            
    db.commit()
    cur.close()
    db.close()
    log_action(session['username'], f"Quét thiết bị USB phát hiện {len(ports)} cổng, thêm mới {new_count} cổng.")
    return jsonify({'success': True, 'message': f'Đã quét xong. Tìm thấy {len(ports)} cổng kết nối vật lý, đã thêm vào kho {new_count} thiết bị mới.'})

@admin_bp.route("/api/devices", methods=['GET'])
@require_auth('admin')
def admin_api_get_devices():
    """Lấy danh sách các USB đã đồng bộ vào CSDL"""
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, tag_name, type, port, status, in_use_by FROM hardware_devices")
    devices = cur.fetchall()
    cur.close()
    db.close()
    return jsonify(devices)

@admin_bp.route("/api/devices/assign", methods=['POST'])
@require_auth('admin')
def admin_api_assign_device():
    """Giao hoặc Lấy lại quyền sử dụng cổng USB vật lý cho một Sinh viên cụ thể"""
    data = request.get_json()
    device_id = data.get('device_id')
    username = data.get('username')
    
    db = get_db_connection()
    cur = db.cursor()
    if username:
        # Check if username exists
        cur.execute("SELECT id FROM users WHERE username = %s LIMIT 1", (username,))
        user_row = cur.fetchone()
        if not user_row:
            cur.close(), db.close()
            return jsonify({'success': False, 'message': f'User {username} không tồn tại'})

        cur.execute("UPDATE hardware_devices SET in_use_by = %s, status = 'in_use' WHERE id = %s", (username, device_id))
        log_msg = f"Đã giao Thiết bị ID {device_id} cho User {username}"
    else:
        cur.execute("UPDATE hardware_devices SET in_use_by = NULL, status = 'available' WHERE id = %s", (device_id,))
        log_msg = f"Đã thu hồi Thiết bị ID {device_id}"
        
    db.commit()
    cur.close()
    db.close()
    
    log_action(session['username'], log_msg)
    return jsonify({'success': True, 'message': 'Cập nhật phân quyền Cổng thiết bị thành công!'})

