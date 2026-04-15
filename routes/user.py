"""
User workspace routes: file management, editor, Arduino operations
"""
import os
import re
import unicodedata
import json
import stat
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.utils import secure_filename
from utils import require_auth, make_safe_name, is_safe_path
from config import HIDDEN_SYSTEM_FILES
from services import (
    ensure_user_container_and_setup, get_ssh_client,
    compile_sketch, log_action
)
from config.database import get_db_connection
from services.ai_grader import grade_submission_with_ai
from utils.helpers import slugify_vn
from services.workspace_manager import list_workspace_files, load_workspace_file, save_workspace_file

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
        # Tự động tạo folder bài tập cho tất cả mission đang diễn ra
        initialize_assigned_missions(username)
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
    if session.get('username') != username: 
        return jsonify(error="Unauthorized"), 403
    
    path = request.json.get("path", ".")
    if '..' in path or path.startswith('/'): 
        return jsonify(error="Invalid path"), 400
    
    try:
        from services.ssh_manager import get_ssh_client
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        result = list_workspace_files(username, safe_username, sftp, path)
        
        sftp.close()
        client.close()
        
        if result["success"]:
            return jsonify(files=result["files"], path=result["path"])
        else:
            status_code = result.get("status_code", 500)
            return jsonify(error=result["error"]), status_code

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
        from services.ssh_manager import get_ssh_client
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        result = load_workspace_file(username, safe_username, sftp, path, filename)
        
        sftp.close()
        client.close()
        
        if result["success"]:
            return jsonify(success=True, content=result["content"])
        else:
            status_code = result.get("status_code", 500)
            return jsonify(success=False, error=result["error"]), status_code
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
        from services.ssh_manager import get_ssh_client
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        
        result = save_workspace_file(username, safe_username, sftp, path, filename, content)
        
        sftp.close()
        client.close()
        
        if result["success"]:
            from services import log_action
            log_action(username, f"Save file via service: {filename}")
            return jsonify(success=True)
        else:
            status_code = result.get("status_code", 500)
            return jsonify(success=False, error=result["error"]), status_code
            
    except Exception as e: 
        from flask import current_app
        current_app.logger.error(f"Save Error for {username}: {e} (Path: {path}, File: {filename})")
        return jsonify(success=False, error=str(e)), 500

# ==================== ARDUINO OPERATIONS ====================

# ==================== KẾT THÚC ARDUINO OPERATIONS ====================

@user_bp.route('/<username>/compile', methods=['POST'])
@require_auth('user')
def compile_sketch_api(username):
    """API to compile Arduino sketch"""
    data = request.get_json()
    sketch_path = data.get("sketch_path")
    board_fqbn = data.get("board_fqbn")
    
    if not sketch_path or not board_fqbn:
        return jsonify(success=False, output="Thiếu thông tương tin sketch_path hoặc board", error_analysis=None), 400

    result = compile_sketch(username, board_fqbn, sketch_path)
    return jsonify(result)

# API nạp code vòng ngoài (Upload) đã bị xóa bỏ thay bằng AI Grader.


# ==================== MISSIONS ====================

@user_bp.route('/missions')
@require_auth('user')
def user_missions_page():
    """User missions/exam page"""
    return render_template('user_missions.html')


@user_bp.route('/api/my-missions')
@require_auth('user')
def user_api_my_missions():
    """API: Get missions assigned to current user"""
    username = session['username']
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT id FROM users WHERE username=%s", (username,))
    user = cur.fetchone()
    if not user:
        cur.close(); db.close()
        return jsonify([])
    user_id = user['id']
    cur.execute("""
        SELECT DISTINCT m.id, m.name, m.description, m.template_code,
               m.start_time, m.end_time, m.duration_minutes, m.created_at,
               sub.id as sub_id, sub.submitted_at, sub.score,
               sub.ai_feedback, sub.ai_criteria
        FROM missions m
        JOIN mission_assignments ma ON m.id = ma.mission_id
        LEFT JOIN submissions sub ON m.id = sub.mission_id AND sub.user_id = %s
        WHERE ma.user_id = %s
        ORDER BY m.start_time DESC
    """, (user_id, user_id))
    missions = cur.fetchall()
    cur.close(); db.close()
    result = []
    for m in missions:
        d = dict(m)
        d['start_time'] = m['start_time'].isoformat() if m['start_time'] else None
        d['end_time'] = m['end_time'].isoformat() if m['end_time'] else None
        d['created_at'] = m['created_at'].isoformat() if m.get('created_at') else None
        d['submitted'] = m['sub_id'] is not None
        if m['sub_id']:
            d['submission'] = {
                'id': m['sub_id'],
                'submitted_at': m['submitted_at'].isoformat() if m['submitted_at'] else None,
                'score': float(m['score']) if m['score'] is not None else None,
                'ai_feedback': m['ai_feedback'],
                'ai_criteria': json.loads(m['ai_criteria']) if isinstance(m.get('ai_criteria'), str) else m.get('ai_criteria'),
            }
        else:
            d['submission'] = None
        for k in ['sub_id', 'submitted_at', 'score', 'ai_feedback', 'ai_criteria']:
            d.pop(k, None)
        result.append(d)
    return jsonify(result)


def initialize_assigned_missions(username):
    """
    Helper to auto-initialize all active missions assigned to user.
    Creates folders and .ino files.
    """
    from utils import make_safe_name
    safe_username = make_safe_name(username)
    
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    # Lấy danh sách missions active mà user được giao
    cur.execute("""
        SELECT m.* FROM missions m
        JOIN mission_assignments ma ON m.id = ma.mission_id
        JOIN users u ON u.id = ma.user_id
        WHERE u.username = %s 
        AND m.start_time <= CURRENT_TIMESTAMP 
        AND m.end_time >= CURRENT_TIMESTAMP
    """, (username,))
    missions = cur.fetchall()
    cur.close(); db.close()
    
    if not missions:
        return
        
    try:
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        home_dir = f"/home/{safe_username}"
        
        for m in missions:
            mission_slug = slugify_vn(m['name'])
            if not mission_slug: mission_slug = f"mission_{m['id']}"
            
            # Đề phòng tên cũ bị lỗi (ví dụ đề 18 thành e_18)
            # Ta sẽ kiểm tra và đổi tên nếu cần
            def broken_slugify(text):
                import unicodedata
                text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
                text = re.sub(r'[^\w\s-]', '', text).strip().lower()
                text = re.sub(r'[-\s]+', '_', text)
                return text
            old_slug = broken_slugify(m['name'])
            
            mission_dir = os.path.join(home_dir, mission_slug)
            old_dir = os.path.join(home_dir, old_slug) if old_slug and old_slug != mission_slug else None
            
            # Kiểm tra di cư thư mục cũ sang mới
            if old_dir:
                try:
                    sftp.stat(old_dir)
                    # Nếu tồn tại thư mục cũ, hãy đổi tên nó sang tên mới chuẩn nếu tên mới chưa có
                    try:
                        sftp.stat(mission_dir)
                    except FileNotFoundError:
                        sftp.rename(old_dir, mission_dir)
                        from flask import current_app
                        current_app.logger.info(f"Migrated folder {old_slug} -> {mission_slug} for {username}")
                except FileNotFoundError:
                    pass

            # 1. Tạo thư mục mới (nếu chưa có sau khi migrate)
            try:
                sftp.mkdir(mission_dir)
            except IOError: pass
                
            # 2. Tạo file .ino (nếu chưa có)
            ino_path = os.path.join(mission_dir, f"{mission_slug}.ino")
            try:
                sftp.stat(ino_path)
            except FileNotFoundError:
                template = m.get('template_code') or "// Bắt đầu code bài làm của bạn tại đây\nvoid setup() {\n  Serial.begin(115200);\n}\n\nvoid loop() {\n  \n}\n"
                with sftp.open(ino_path, 'w') as f:
                    f.write(template)
        
        sftp.close(); client.close()
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Auto-init missions error for {username}: {e}")

@user_bp.route('/api/preview-files', methods=['GET'])
@require_auth('user')
def user_api_preview_files():
    """API: List files that would be snapshotted on submission (preview only)."""
    import stat as stat_mod
    username = session['username']
    safe_username = make_safe_name(username)
    files_list = []
    try:
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        home_dir = f"/home/{safe_username}"
        def collect(path, depth=0):
            if depth > 4: return
            try:
                EXCLUDED_DIRS = {'libraries', 'node_modules', 'venv', '__pycache__', '.git', '.arduino15', 'Arduino'}
                for item in sftp.listdir_attr(path):
                    if item.filename.startswith('.'): continue
                    if item.filename in EXCLUDED_DIRS: continue
                    
                    fp = f"{path}/{item.filename}"
                    if stat_mod.S_ISDIR(item.st_mode):
                        collect(fp, depth + 1)
                    elif item.filename.endswith(('.ino', '.cpp', '.c', '.h', '.py')):
                        if 'libraries/' in fp or 'node_modules/' in fp: continue
                        files_list.append({
                            'name': item.filename,
                            'path': fp.replace(home_dir, ''),
                            'size': item.st_size
                        })
            except: pass
        collect(home_dir)
        sftp.close(); client.close()
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    return jsonify(success=True, files=files_list)


@user_bp.route('/api/missions/<int:mission_id>/start', methods=['POST'])
@require_auth('user')
def user_api_missions_start(mission_id):
    """API to initialize specific mission (fallback or manual trigger)"""
    username = session['username']
    safe_username = make_safe_name(username)
    
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM missions WHERE id=%s", (mission_id,))
    mission = cur.fetchone()
    cur.close(); db.close()
    
    if not mission:
        return jsonify(success=False, error="Không tìm thấy bài thi"), 404
        
    mission_slug = slugify_vn(mission['name'])
    if not mission_slug: mission_slug = f"mission_{mission_id}"
    
    try:
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        home_dir = f"/home/{safe_username}"
        mission_dir = os.path.join(home_dir, mission_slug)
        
        try:
            sftp.mkdir(mission_dir)
        except IOError: pass
            
        ino_path = os.path.join(mission_dir, f"{mission_slug}.ino")
        try:
            sftp.stat(ino_path)
        except FileNotFoundError:
            template = mission.get('template_code') or "// Bắt đầu code bài làm của bạn tại đây\nvoid setup() {\n  Serial.begin(115200);\n}\n\nvoid loop() {\n  \n}\n"
            with sftp.open(ino_path, 'w') as f:
                f.write(template)
        
        sftp.close(); client.close()
        return jsonify(success=True, mission_slug=mission_slug)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500


@user_bp.route('/api/missions/<int:mission_id>/submit', methods=['POST'])
@require_auth('user')
def user_api_submit_mission(mission_id):
    """API: Submit mission - snapshot files and trigger AI grading"""
    import threading
    username = session['username']
    safe_username = make_safe_name(username)
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM missions WHERE id=%s", (mission_id,))
    mission = cur.fetchone()
    if not mission:
        cur.close(); db.close()
        return jsonify(success=False, error="Không tìm thấy bài thi"), 404
    cur.execute("SELECT id FROM users WHERE username=%s", (username,))
    user = cur.fetchone()
    if not user:
        cur.close(); db.close()
        return jsonify(success=False, error="Không tìm thấy người dùng"), 404
    user_id = user['id']
    cur.execute("SELECT id FROM mission_assignments WHERE mission_id=%s AND user_id=%s", (mission_id, user_id))
    if not cur.fetchone():
        cur.close(); db.close()
        return jsonify(success=False, error="Bạn không được giao bài thi này"), 403
    cur.execute("SELECT id FROM submissions WHERE mission_id=%s AND user_id=%s", (mission_id, user_id))
    if cur.fetchone():
        cur.close(); db.close()
        return jsonify(success=False, error="Bạn đã nộp bài thi này rồi"), 409
    # Snapshot files from container
    files_snapshot = []
    try:
        import stat as stat_mod
        client = get_ssh_client(username)
        sftp = client.open_sftp()
        home_dir = f"/home/{safe_username}"
        def collect(path, depth=0):
            if depth > 4: return
            try:
                # Các thư mục cần loại bỏ không thu thập file bài làm
                EXCLUDED_DIRS = {'libraries', 'node_modules', 'venv', '__pycache__', '.git', '.arduino15', 'Arduino'}
                
                for item in sftp.listdir_attr(path):
                    if item.filename.startswith('.'): continue
                    if item.filename in EXCLUDED_DIRS: continue
                    
                    fp = f"{path}/{item.filename}"
                    if stat_mod.S_ISDIR(item.st_mode):
                        collect(fp, depth + 1)
                    elif item.filename.endswith(('.ino', '.cpp', '.c', '.h', '.py')):
                        # Không lấy file trong thư mục libraries (lớp bảo vệ 2)
                        if 'libraries/' in fp or 'node_modules/' in fp: continue
                        
                        try:
                            with sftp.open(fp, 'r') as f:
                                # Đọc tối đa 50k ký tự mỗi file
                                content = f.read(50000).decode('utf-8', errors='replace')
                            files_snapshot.append({
                                'name': item.filename, 
                                'path': fp.replace(home_dir, ''), 
                                'content': content, 
                                'size': item.st_size
                            })
                        except: pass
            except: pass
        collect(home_dir)
        sftp.close(); client.close()
    except Exception as e:
        files_snapshot = [{'name': 'error.txt', 'path': '/', 'content': f'Lỗi thu thập file: {e}', 'size': 0}]
    is_auto = (request.get_json(silent=True) or {}).get('auto', False)
    try:
        cur.execute(
            "INSERT INTO submissions (mission_id, user_id, files, is_auto_submit) VALUES (%s,%s,%s,%s)",
            (mission_id, user_id, json.dumps(files_snapshot), is_auto)
        )
        db.commit()
        sub_id = cur.lastrowid
        log_action(username, f"Submitted mission {mission_id} ({'auto' if is_auto else 'manual'})")
        
        # KIỂM TRA ĐIỀU KIỆN KẾT THÚC BÀI THI SỚM
        cur.execute("SELECT user_id FROM mission_assignments WHERE mission_id = %s", (mission_id,))
        assigned_users = [row['user_id'] for row in cur.fetchall()]
        if assigned_users:
            format_strings = ','.join(['%s'] * len(assigned_users))
            # Lấy số lượng user_id đã có status submit trong table submissions cho mission này
            cur.execute(f"SELECT COUNT(DISTINCT user_id) as submitted_count FROM submissions WHERE mission_id = %s AND user_id IN ({format_strings})", (mission_id, *assigned_users))
            result = cur.fetchone()
            submitted_count = result['submitted_count'] if result else 0
            if submitted_count >= len(assigned_users):
                # 100% học viên đã nộp bài -> Kết thúc bài thi ngay lập tức
                cur.execute("UPDATE missions SET end_time = CURRENT_TIMESTAMP WHERE id = %s", (mission_id,))
                db.commit()
        # Background AI grading
        mission_snap = dict(mission)
        def bg_grade():
            import traceback
            import sys
            try:
                from services.ai_grader import grade_submission_with_ai
                result = grade_submission_with_ai(
                    mission_description=mission_snap['description'],
                    mission_name=mission_snap['name'],
                    files=files_snapshot
                )
                bg_db = get_db_connection()
                if not bg_db:
                    with open("/tmp/ai_err.log", "a") as f: f.write("Lỗi: Không thể lấy get_db_connection trong bg_grade\n")
                    return
                bg_cur = bg_db.cursor()
                if result['success']:
                    bg_cur.execute(
                        "UPDATE submissions SET score=%s, ai_feedback=%s, ai_criteria=%s WHERE id=%s",
                        (result['score'], result['feedback'], json.dumps(result['criteria']), sub_id)
                    )
                else:
                    bg_cur.execute(
                        "UPDATE submissions SET score=%s, ai_feedback=%s, ai_criteria=%s WHERE id=%s",
                        (0.0, f"LỖI CHẤM ĐIỂM AI: {result.get('error', 'Không xác định')}", "[]", sub_id)
                    )
                bg_db.commit(); bg_cur.close(); bg_db.close()
            except Exception as ex:
                err_trace = traceback.format_exc()
                with open("/tmp/ai_err.log", "a") as f: f.write(f"CRASH:\n{err_trace}\n")
                try:
                    bg_db = get_db_connection()
                    if bg_db:
                        bg_cur = bg_db.cursor()
                        bg_cur.execute(
                            "UPDATE submissions SET score=%s, ai_feedback=%s, ai_criteria=%s WHERE id=%s",
                            (0.0, f"LỖI HỆ THỐNG: {ex}", "[]", sub_id)
                        )
                        bg_db.commit(); bg_cur.close(); bg_db.close()
                except Exception as inner_ex:
                    with open("/tmp/ai_err.log", "a") as f: f.write(f"INNER CRASH:\n{traceback.format_exc()}\n")
        threading.Thread(target=bg_grade, daemon=True).start()
        return jsonify(success=True, message="Nộp bài thành công! Đang chấm điểm...", submission_id=sub_id)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        cur.close(); db.close()


# ==================== DEBUG/MAINTENANCE ====================

@user_bp.route('/<username>/debug-devices', methods=['GET'])
@require_auth('user')  
def debug_devices_api(username):
    """API to debug device detection"""
    import glob
    import subprocess
    
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
