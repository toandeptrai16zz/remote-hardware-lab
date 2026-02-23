"""
User workspace routes: file management, editor, Arduino operations
"""
import os
import stat
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from utils import require_auth, make_safe_name, is_safe_path
from config import HIDDEN_SYSTEM_FILES
from services import (
    ensure_user_container_and_setup, get_ssh_client,
    compile_sketch, get_serial_ports, log_action
)

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route("/")
@require_auth('user')
def user_redirect():
    """Redirect to user workspace"""
    return redirect(url_for('user.user_workspace', username=session['username']))

@user_bp.route("/<username>/workspace")
@require_auth('user')
def user_workspace(username):
    """User workspace/IDE page"""
    if session["username"] != username: 
        return redirect(url_for("index"))
    
    try:        
        ensure_user_container_and_setup(username)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Container check failed for {username}: {e}")
        flash(f"Lỗi khởi tạo môi trường làm việc: {e}", "error")
    
    return render_template("user.html", username=username)

# ==================== FILE MANAGEMENT ====================

@user_bp.route('/<username>/files', methods=['POST'])
@require_auth('user')
def list_files_api(username):
    """API to list files in directory"""
    safe_username = make_safe_name(username)
    
    if session['username'] != username: 
        return jsonify(error="Unauthorized"), 403
    
    path = request.json.get("path", ".")
    
    # Validate path
    if '..' in path or path.startswith('/'): 
        return jsonify(error="Invalid path"), 400
    
    try:
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        base_path = os.path.join("/home", safe_username, path)
        
        files = []
        try:
            dir_items = sftp.listdir_attr(base_path)
        except FileNotFoundError:
            return jsonify(error="Directory not found"), 404
            
        for attr in dir_items:
            filename = attr.filename
            
            # Filter hidden/system files
            if filename.startswith('.'):
                continue
                
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
        
        # Sort: folders first
        files.sort(key=lambda x: (not x['is_dir'], x['name']))
        
        return jsonify(files=files, path=path)

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"ERROR List Files user '{safe_username}': {str(e)}")
        return jsonify(error=str(e)), 500

@user_bp.route('/<username>/create-folder', methods=['POST'])
@require_auth('user')
def create_folder_api(username):
    """API to create new folder"""
    safe_username = make_safe_name(username)

    if session.get('username') != username: 
        return jsonify(success=False, error="Unauthorized"), 403

    data = request.get_json()
    folder_name = data.get("folder_name")
    path = data.get("path", ".")

    if not folder_name or not is_safe_path("/home", folder_name):
        return jsonify(success=False, error="Invalid folder name"), 400
    
    home_dir = f"/home/{safe_username}"
    if not is_safe_path(home_dir, path):
        return jsonify(success=False, error="Invalid path"), 400

    try:
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        full_path = os.path.join(home_dir, path, folder_name)
        sftp.mkdir(full_path)
        
        sftp.close()
        client.close()
        log_action(username, f"Create folder: {full_path}")
        return jsonify(success=True)
    except Exception as e: 
        from flask import current_app
        current_app.logger.error(f"Create Folder Error: {e}")
        return jsonify(success=False, error=str(e)), 500

@user_bp.route('/<username>/upload-files', methods=['POST'])
@require_auth('user')
def upload_files_api(username):
    """API to upload files"""
    safe_username = make_safe_name(username)
    if session.get('username') != username: 
        return jsonify(success=False, error="Unauthorized"), 403
    
    path = request.form.get('path', '.')
    files = request.files.getlist('files')
    
    home_dir = f"/home/{safe_username}"
    if not files: 
        return jsonify(success=False, error="No files provided"), 400
    if not is_safe_path(home_dir, path): 
        return jsonify(success=False, error="Invalid path"), 400

    try:
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        count = 0
        for file in files:
            if file.filename:
                safe_filename = secure_filename(file.filename)
                target_path = os.path.join(home_dir, path, safe_filename)
                
                sftp.putfo(file, target_path)
                count += 1
                
        sftp.close()
        client.close()
        log_action(username, f"Uploaded {count} files to {path}")
        return jsonify(success=True, message=f"Uploaded {count} files.")
    except Exception as e: 
        from flask import current_app
        current_app.logger.error(f"Upload Error: {e}")
        return jsonify(success=False, error=str(e)), 500

@user_bp.route('/<username>/rename-item', methods=['POST'])
@require_auth('user')
def rename_item_api(username):
    """API to rename file/folder"""
    safe_username = make_safe_name(username)
    
    if session.get('username') != username: 
        return jsonify(success=False, error="Unauthorized"), 403
    
    data = request.get_json()
    old_path = data.get("old_path")
    new_name = data.get("new_name")
    
    # Validate
    if not old_path or not new_name or '/' in new_name or '..' in new_name:
        return jsonify(success=False, error="Invalid parameters"), 400

    try:
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        base_dir_rel = os.path.dirname(old_path)
        old_full_path = os.path.join("/home", safe_username, old_path)
        new_full_path = os.path.join("/home", safe_username, base_dir_rel, new_name)
        
        sftp.rename(old_full_path, new_full_path)
        
        sftp.close()
        client.close()
        log_action(username, f"Rename: {old_path} -> {new_name}")
        return jsonify(success=True)
    except Exception as e: 
        return jsonify(success=False, error=str(e)), 500

@user_bp.route('/<username>/delete-item', methods=['POST'])
@require_auth('user')
def delete_item_api(username):
    """API to delete file/folder"""
    import shlex
    
    safe_username = make_safe_name(username)
    if session.get('username') != username: 
        return jsonify(success=False, error="Unauthorized"), 403
    
    path = request.json.get("path")
    home_dir = f"/home/{safe_username}"

    if not path or not is_safe_path(home_dir, path):
        return jsonify(success=False, error="Invalid path"), 400

    try:
        client = get_ssh_client(username)

        full_path = os.path.normpath(os.path.join(home_dir, path))
        
        # Prevent deleting home directory
        if full_path == home_dir:
            return jsonify(success=False, error="Cannot delete root home"), 403
             
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
        from flask import current_app
        current_app.logger.error(f"Delete Error: {e}")
        return jsonify(success=False, error=str(e)), 500

# ==================== CODE EDITOR ====================

@user_bp.route('/<username>/editor/new', methods=['POST'])
@require_auth('user')
def new_file_api(username):
    """API to create new file"""
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
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        filepath = os.path.join("/home", safe_username, path, filename)

        # Check if file exists
        try:
            sftp.stat(filepath)
            sftp.close()
            client.close()
            return jsonify(success=False, error="File đã tồn tại"), 400
        except FileNotFoundError:
            pass

        # Create empty file
        with sftp.open(filepath, 'w') as f:
            f.write("")  

        sftp.close()
        client.close()
        
        log_action(username, f"Create new file: {filepath}")
        return jsonify(success=True)
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"New File Error for {safe_username}: {e}")
        return jsonify(success=False, error=str(e)), 500

@user_bp.route('/<username>/editor/load', methods=['POST'])
@require_auth('user')
def load_file_api(username):
    """API to load file content"""
    safe_username = make_safe_name(username)
    if session.get('username') != username: 
        return jsonify(success=False, error="Unauthorized"), 403

    data = request.get_json()
    filename = data.get("filename")
    path = data.get("path", ".")
    
    home_dir = f"/home/{safe_username}"
    if not filename or not is_safe_path(home_dir, os.path.join(path, filename)):
        return jsonify(success=False, error="Invalid file path"), 400

    try:
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        filepath = os.path.join(home_dir, path, filename)
        
        with sftp.open(filepath, 'r') as f: 
            content = f.read().decode('utf-8', errors='ignore')
            
        sftp.close()
        client.close()
        return jsonify(success=True, content=content)
    except Exception as e: 
        return jsonify(success=False, error=str(e)), 500

@user_bp.route('/<username>/editor/save', methods=['POST'])
@require_auth('user')
def save_file_api(username):
    """API to save file content"""
    safe_username = make_safe_name(username)
    
    if session.get('username') != username: 
        return jsonify(success=False, error="Unauthorized"), 403

    data = request.get_json()
    filename = data.get("filename")
    content = data.get("content", "")
    path = data.get("path", ".")

    home_dir = f"/home/{safe_username}"
    if not filename or not is_safe_path(home_dir, os.path.join(path, filename)):
        return jsonify(success=False, error="Invalid file path"), 400

    try:
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        filepath = os.path.join(home_dir, path, filename)
        
        with sftp.open(filepath, 'w') as f: 
            f.write(content)
            
        sftp.close()
        client.close()
        log_action(username, f"Save file: {filename}")
        return jsonify(success=True)
    except Exception as e: 
        from flask import current_app
        current_app.logger.error(f"Save Error: {e}")
        return jsonify(success=False, error=str(e)), 500

# ==================== ARDUINO OPERATIONS ====================

@user_bp.route('/<username>/serial-ports', methods=['GET'])
@require_auth('user')
def get_serial_ports_api(username):
    """API to get available serial ports"""
    if session['username'] != username:
        return jsonify(error="Unauthorized"), 403
    
    result = get_serial_ports(username)
    
    if result['success']:
        return jsonify(result)
    else:
        return jsonify(result), 500

@user_bp.route('/<username>/compile', methods=['POST'])
@require_auth('user')
def compile_sketch_api(username):
    """API to compile Arduino sketch"""
    data = request.get_json()
    sketch_path = data.get("sketch_path")
    board_fqbn = data.get("board_fqbn")
    
    if not sketch_path or not board_fqbn:
        return jsonify(success=False, output="Thiếu thông tin sketch_path hoặc board", error_analysis=None), 400

    result = compile_sketch(username, sketch_path, board_fqbn)
    return jsonify(result)

@user_bp.route('/<username>/upload', methods=['POST'])
@require_auth('user')
def upload_to_board_api(username):
    """API to upload code to board"""
    from flask import current_app
    from services.arduino import perform_upload_worker
    
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
    
    # Use socketio background task
    socketio = current_app.extensions['socketio']
    socketio.start_background_task(
        target=perform_upload_worker, 
        username=username, 
        sid=sid, 
        sketch_path=sketch_path, 
        board_fqbn=board_fqbn, 
        port=port,
        socketio=socketio
    )
    
    return jsonify(success=True, message="Yêu cầu nạp code đã được đưa vào hàng đợi.")

# ==================== DEBUG/MAINTENANCE ====================

@user_bp.route('/<username>/debug-devices', methods=['GET'])
@require_auth('user')  
def debug_devices_api(username):
    """API to debug device detection"""
    import glob
    import subprocess
    import json
    
    if session['username'] != username:
        return jsonify(error="Unauthorized"), 403
    
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    
    try:
        # Check on host
        host_devices = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        
        # Check in container
        device_cmd = ["docker", "exec", cname, "ls", "/dev/tty*"]
        device_result = subprocess.run(device_cmd, capture_output=True, text=True, timeout=10)
        
        container_devices = []
        if device_result.returncode == 0:
            for line in device_result.stdout.split('\n'):
                if 'ttyUSB' in line or 'ttyACM' in line:
                    container_devices.append(line.strip())
        
        # Check arduino-cli
        arduino_cmd = ["docker", "exec", cname, "arduino-cli", "board", "list"]
        arduino_result = subprocess.run(arduino_cmd, capture_output=True, text=True, timeout=10)
        
        # Check user permissions
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

@user_bp.route('/<username>/fix-permissions', methods=['POST'])
@require_auth('user')
def fix_permissions_api(username):
    """API to fix device permissions"""
    import subprocess
    
    if session['username'] != username:
        return jsonify(error="Unauthorized"), 403
    
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    
    try:
        # Add user to dialout group
        cmd1 = ["docker", "exec", cname, "usermod", "-a", "-G", "dialout", safe_username]
        result1 = subprocess.run(cmd1, capture_output=True, text=True, timeout=10)
        
        # Set device permissions
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
        from flask import current_app
        current_app.logger.error(f"Fix permissions error for {username}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
