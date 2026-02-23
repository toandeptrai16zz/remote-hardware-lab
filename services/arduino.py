"""
Arduino compilation and upload service
REAL-TIME MODE: Streaming logs & Strict Error Handling & Auto-Compile
FULL VERSION FIXED: Fix 'User cant see ports' bug
"""
import os
import re
import json
import subprocess
import logging
import threading
import glob
from collections import defaultdict
from utils import make_safe_name
from config import get_db_connection
from services.logger import log_action

logger = logging.getLogger(__name__)
device_locks = defaultdict(threading.Lock)

# ==============================================================================
# 1. HÀM HỖ TRỢ PHÂN TÍCH LỖI (GIỮ NGUYÊN)
# ==============================================================================
def analyze_compile_errors(output):
    errors = []
    warnings = []
    lines = output.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if 'error:' in line.lower():
            error_info = extract_error_info(line, lines, i)
            if error_info: errors.append(error_info)
        elif 'warning:' in line.lower():
            warning_info = extract_warning_info(line, lines, i)
            if warning_info: warnings.append(warning_info)
    return {'errors': errors, 'warnings': warnings, 'error_count': len(errors), 'warning_count': len(warnings)}

def extract_error_info(error_line, all_lines, line_index):
    pattern = r'(.+?):(\d+):(\d+):\s*error:\s*(.+)'
    match = re.search(pattern, error_line)
    if match:
        return {'file': os.path.basename(match.group(1)), 'line': int(match.group(2)), 'column': int(match.group(3)), 'message': match.group(4), 'raw': error_line}
    return None

def extract_warning_info(warning_line, all_lines, line_index):
    pattern = r'(.+?):(\d+):(\d+):\s*warning:\s*(.+)'
    match = re.search(pattern, warning_line)
    if match:
        return {'file': os.path.basename(match.group(1)), 'line': int(match.group(2)), 'message': match.group(4), 'raw': warning_line}
    return None

# ==============================================================================
# 2. HÀM STREAMING LOG (REAL-TIME)
# ==============================================================================
def run_and_stream(cmd, socketio, sid):
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    full_log = []
    for line in iter(process.stdout.readline, ''):
        line = line.strip()
        if line:
            full_log.append(line)
            socketio.emit('upload_status', {'status': 'log', 'message': line}, namespace='/upload_status', room=sid)
            
    process.stdout.close()
    return_code = process.wait()
    return return_code, "\n".join(full_log)

# ==============================================================================
# 3. HÀM CHUẨN BỊ FILE (COPY AN TOÀN)
# ==============================================================================
def prepare_sketch_folder(container_name, safe_username, sketch_filename):
    sketch_name = os.path.splitext(sketch_filename)[0]
    base_path = f"/home/{safe_username}" 
    
    current_file_path = f"{base_path}/{sketch_filename}"
    target_folder = f"{base_path}/{sketch_name}"
    target_file_path = f"{target_folder}/{sketch_filename}"
    
    setup_cmd = [
        "docker", "exec", container_name, "sh", "-c",
        f"mkdir -p {target_folder} && [ -f {current_file_path} ] && cp {current_file_path} {target_file_path} || true"
    ]
    subprocess.run(setup_cmd, capture_output=True)
    return target_file_path

# ==============================================================================
# 4. QUY TRÌNH NẠP MỚI (AUTO-COMPILE + STREAMING)
# ==============================================================================
def perform_upload_worker(username, port, sketch_path, sid, board_fqbn, socketio=None):
    if socketio is None:
        try: from __main__ import socketio
        except ImportError: return

    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    sketch_filename = os.path.basename(sketch_path)

    socketio.emit('upload_status', {'status': 'start', 'message': f'Bắt đầu xử lý cho {board_fqbn}...'}, namespace='/upload_status', room=sid)
    try: subprocess.run(["docker", "exec", "-u", "root", cname, "chmod", "666", port], timeout=2)
    except: pass

    container_sketch_path = prepare_sketch_folder(cname, safe_username, sketch_filename)

    with device_locks[port]:
        # B2: Biên dịch (Streaming)
        socketio.emit('upload_status', {'status': 'compiling', 'message': '--- 1. ĐANG BIÊN DỊCH CODE MỚI ---'}, namespace='/upload_status', room=sid)
        compile_cmd = ["docker", "exec", cname, "arduino-cli", "compile", "--fqbn", board_fqbn, container_sketch_path]
        
        code, log = run_and_stream(compile_cmd, socketio, sid)
        
        if code != 0:
            socketio.emit('upload_status', {'status': 'error', 'message': '❌ Lỗi biên dịch!', 'details': log, 'suggestions': ["Kiểm tra cú pháp code."]}, namespace='/upload_status', room=sid)
            log_action(username, "Upload aborted: Compile failed", success=False)
            return

        # B3: Nạp (Streaming)
        socketio.emit('upload_status', {'status': 'uploading', 'message': '--- 2. ĐANG NẠP CODE XUỐNG MẠCH ---'}, namespace='/upload_status', room=sid)
        upload_cmd = ["docker", "exec", cname, "arduino-cli", "upload", "-p", port, "--fqbn", board_fqbn, container_sketch_path]
        
        code, log = run_and_stream(upload_cmd, socketio, sid)
        
        if code == 0:
            log_action(username, "Upload success")
            socketio.emit('upload_status', {'status': 'success', 'message': '✅ NẠP THÀNH CÔNG!'}, namespace='/upload_status', room=sid)
        else:
            log_action(username, "Upload failed", success=False)
            suggestions = get_upload_error_suggestions(log)
            socketio.emit('upload_status', {'status': 'error', 'message': '❌ Nạp thất bại!', 'details': log, 'suggestions': suggestions}, namespace='/upload_status', room=sid)

# ==============================================================================
# 5. CÁC HÀM SCAN & HELPERS KHÁC
# ==============================================================================
def get_upload_error_suggestions(output):
    suggestions = []
    if "Permission denied" in output: suggestions.append("Lỗi quyền truy cập cổng USB. Hãy thử bấm 'Quét lại cổng'.")
    if "Packet content transfer stopped" in output: suggestions.append("Mất kết nối. Thử cáp USB khác.")
    if "Timed out" in output: suggestions.append("Hết thời gian chờ. Kiểm tra lại chế độ Boot (giữ nút BOOT trên mạch).")
    return suggestions

def get_boards_by_type(db_type):
    t = str(db_type).lower() if db_type else "generic"
    esp32_default = {"name": "ESP32 Dev Module", "fqbn": "esp32:esp32:esp32"}
    esp8266_default = {"name": "ESP8266 NodeMCU", "fqbn": "esp8266:esp8266:nodemcuv2"}
    arduino_list = [{"name": "Arduino Uno", "fqbn": "arduino:avr:uno"}]
    
    if "esp32" in t: return [esp32_default, {"name": "AI Thinker ESP32-CAM", "fqbn": "esp32:esp32:esp32cam"}]
    elif "esp8266" in t: return [esp8266_default]
    else: return [esp32_default] + [esp8266_default] + arduino_list

def get_serial_ports(username):
    """
    SỬA LẠI LOGIC: Luôn hiển thị cổng nếu Docker thấy (kể cả khi DB lỗi hoặc chưa khớp)
    """
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    try:
        # 1. Lấy thông tin từ Database
        db_devices = {} 
        try:
            db = get_db_connection()
            if db:
                cur = db.cursor(dictionary=True)
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                user_row = cur.fetchone()
                if user_row:
                    cur.execute("SELECT port, tag_name, type FROM hardware_devices WHERE in_use_by = %s", (user_row['id'],))
                    for row in cur.fetchall():
                        db_devices[row['port']] = row
                cur.close()
                db.close()
        except: pass

        # 2. Quét Docker
        cmd = ["docker", "exec", cname, "arduino-cli", "board", "list", "--format", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        final_list = []
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for item in data.get("detected_ports", []):
                address = item.get("port", {}).get("address")
                
                # Bỏ cổng rác ttyS
                if "ttyS" in address: continue 
                
                # --- [FIXED] LOGIC HIỂN THỊ CỔNG ---
                if address in db_devices:
                    # Nếu có trong DB -> Lấy tên đẹp
                    display_name = db_devices[address]['tag_name']
                    board_type = db_devices[address]['type']
                else:
                    # [QUAN TRỌNG] Nếu không có trong DB nhưng Docker thấy -> Vẫn hiện ra
                    display_name = f"USB Device ({os.path.basename(address)})"
                    board_type = "esp32" # Mặc định

                boards = get_boards_by_type(board_type)
                
                final_list.append({
                    "port": {"address": address, "label": display_name, "protocol": "serial"},
                    "matching_boards": boards,
                    "boards": boards
                })
        
        return {'success': True, 'ports': final_list}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def compile_sketch(username, board_fqbn, sketch_path):
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    sketch_filename = os.path.basename(sketch_path)
    container_sketch_path = prepare_sketch_folder(cname, safe_username, sketch_filename)
    
    cmd = ["docker", "exec", cname, "arduino-cli", "compile", "--fqbn", board_fqbn, container_sketch_path, "--verbose"]
    
    try:
        logger.info(f"Compiling for {username} on {board_fqbn}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        analysis = analyze_compile_errors(result.stderr + result.stdout)
        return {'success': result.returncode == 0, 'output': result.stdout + result.stderr, 'analysis': analysis}
    except subprocess.TimeoutExpired:
        return {'success': False, 'output': "Compilation timed out", 'analysis': {'error_count': 1}}
    except Exception as e:
        logger.error(f"Compile error: {e}")
        return {'success': False, 'output': str(e), 'analysis': {'error_count': 1}}