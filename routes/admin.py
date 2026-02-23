"""
Admin routes: dashboard, user management, device management
"""
import os
import shutil
import subprocess
from math import ceil
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
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
    cur.execute(
        "INSERT INTO users(username, password, email, role, status) VALUES(%s, %s, %s, %s, 'active')",
        (username, generate_password_hash(password), email, role)
    )
    db.commit()
    cur.close(), db.close()
    
    flash(f"Đã thêm user '{username}' thành công!", "success")
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

# ==================== DEVICE MANAGEMENT ====================

@admin_bp.route("/devices")
@require_auth('admin')
def admin_devices_page():
    """Device management page"""
    return render_template("admin/devices.html")

@admin_bp.route("/api/devices", methods=['GET'])
@require_auth('admin')
def admin_api_get_devices():
    """API to get all devices"""
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM hardware_devices ORDER BY tag_name")
    devices = cur.fetchall()
    cur.close()
    db.close()
    return jsonify(devices)

@admin_bp.route("/api/devices", methods=['POST'])
@require_auth('admin')
def admin_api_add_device():
    """API to add new device"""
    data = request.get_json()
    tag_name = data.get('tag_name')
    device_type = data.get('type')
    port = data.get('port')

    if not all([tag_name, device_type, port]):
        return jsonify(success=False, error="Vui lòng điền đầy đủ thông tin."), 400

    try:
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("INSERT INTO hardware_devices (tag_name, type, port) VALUES (%s, %s, %s)", 
                   (tag_name, device_type, port))
        db.commit()
        cur.close()
        db.close()
        return jsonify(success=True, message="Thêm thiết bị thành công!")
    except mysql.connector.Error as err:
        return jsonify(success=False, error=f"Lỗi Database: {err}"), 500

@admin_bp.route("/api/devices/<int:device_id>", methods=['DELETE'])
@require_auth('admin')
def admin_api_delete_device(device_id):
    """API to delete device"""
    try:
        db = get_db_connection()
        cur = db.cursor(dictionary=True)

        # Get device info
        cur.execute("SELECT tag_name FROM hardware_devices WHERE id = %s", (device_id,))
        device = cur.fetchone()
        
        if not device:
            cur.close()
            db.close()
            return jsonify(success=False, error="Không tìm thấy thiết bị."), 404

        # Delete device
        cur.execute("DELETE FROM hardware_devices WHERE id = %s", (device_id,))
        db.commit()
        
        log_action(session['username'], f"Admin deleted device: {device['tag_name']}", success=True)
        
        cur.close()
        db.close()

        return jsonify(success=True, message="Đã xóa thiết bị thành công!")

    except mysql.connector.Error as err:
        if err.errno == 1451:  # Foreign key constraint
            return jsonify(success=False, error="Không thể xóa! Thiết bị này đang được cấp quyền cho user."), 409
        return jsonify(success=False, error=f"Lỗi Database: {err}"), 500
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500

# ==================== DEVICE ASSIGNMENTS ====================

@admin_bp.route("/assignments")
@require_auth('admin')
def admin_assignments_page():
    """Device assignments management page"""
    return render_template("admin/assignments.html")

@admin_bp.route("/api/users")
@require_auth('admin')
def admin_api_get_users():
    """API to get active users"""
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, username FROM users WHERE role = 'user' AND status = 'active' ORDER BY username")
    users = cur.fetchall()
    cur.close()
    db.close()
    return jsonify(users)

@admin_bp.route("/api/assignments", methods=['GET'])
@require_auth('admin')
def admin_api_get_assignments():
    """API to get all device assignments"""
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

@admin_bp.route("/api/assignments", methods=['POST'])
@require_auth('admin')
def admin_api_add_assignment():
    """API to add device assignment"""
    data = request.get_json()
    user_id = data.get('user_id')
    device_id = data.get('device_id')
    
    if not all([user_id, device_id]):
        return jsonify(success=False, error="Thiếu thông tin user hoặc thiết bị."), 400
    
    try:
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("INSERT INTO device_assignments (user_id, device_id) VALUES (%s, %s)", 
                   (user_id, device_id))
        db.commit()
        cur.close()
        db.close()
        return jsonify(success=True, message="Cấp quyền thành công!")
    except mysql.connector.Error as err:
        if err.errno == 1062:
            return jsonify(success=False, error="Người dùng này đã được cấp quyền cho thiết bị này."), 409
        return jsonify(success=False, error=f"Lỗi Database: {err}"), 500

@admin_bp.route("/api/assignments/<int:assignment_id>", methods=['DELETE'])
@require_auth('admin')
def admin_api_delete_assignment(assignment_id):
    """API to delete device assignment"""
    try:
        db = get_db_connection()
        cur = db.cursor()
        cur.execute("DELETE FROM device_assignments WHERE id = %s", (assignment_id,))
        db.commit()
        affected = cur.rowcount
        cur.close()
        db.close()
        
        if affected == 0: 
            return jsonify(success=False, error="Không tìm thấy quyền để xóa."), 404
        
        return jsonify(success=True, message="Đã thu hồi quyền!")
    except mysql.connector.Error as err: 
        return jsonify(success=False, error=f"Lỗi Database: {err}"), 500

# ==================== MISSIONS ====================

@admin_bp.route("/missions")
@require_auth('admin')
def admin_missions_page():
    """Missions management page"""
    return render_template("admin/missions.html")

@admin_bp.route("/api/missions", methods=['POST'])
@require_auth('admin')
def admin_api_create_mission():
    """API to create mission (bulk assign devices to users)"""
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

    for user_id in user_ids:
        for device_id in device_ids:
            # Use INSERT IGNORE to skip existing assignments
            cur.execute("INSERT IGNORE INTO device_assignments (user_id, device_id) VALUES (%s, %s)", 
                       (user_id, device_id))
            if cur.rowcount > 0:
                success_count += 1

    db.commit()
    cur.close()
    db.close()
    
    log_action(session['username'], f"Giao mission '{mission_name}': {success_count} quyền được cấp.")
    message = f"Giao mission '{mission_name}' hoàn tất. Đã cấp {success_count} quyền mới."
    return jsonify(success=True, message=message)
