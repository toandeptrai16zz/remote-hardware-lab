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
import fcntl
from collections import defaultdict
from contextlib import contextmanager
from utils import make_safe_name
from config import get_db_connection
from services.logger import log_action

logger = logging.getLogger(__name__)
# [ARCHITECT PIVOT REVERSED]: Queue mechanism restored for feature/hardware-flash branch
queue_counts = defaultdict(int) 

@contextmanager
def get_hardware_lock(port_address):
    """
    Cơ chế File Lock (Bản tay sắt): Khóa ở cấp độ Hệ điều hành.
    Giúp đồng bộ hóa nạp code xuyên suốt các Process (gunicorn workers) và Containers.
    """
    safe_port = port_address.replace("/", "_").replace(".", "_")
    lock_path = f"/tmp/arduino_flash_{safe_port}.lock"
    
    # Đảm bảo file tồn tại
    with open(lock_path, 'a') as f:
        pass
        
    lock_file = open(lock_path, 'r+')
    try:
        # LOCK_EX: Khóa độc quyền (Exclusive Lock)
        # Sẽ block cho đến khi lấy được khóa
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        # LOCK_UN: Mở khóa
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()
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
    """[VIRTUAL PIVOT] Hàm rút gọn chỉ biên dịch mô phỏng (Testbench), bỏ nạp phần cứng."""
    if socketio is None:
        try: from __main__ import socketio
        except ImportError: return

    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    sketch_filename = os.path.basename(sketch_path)

    socketio.emit('upload_status', {'status': 'start', 'message': f'Bắt đầu Testbench Ảo hóa cho {board_fqbn}...'}, namespace='/upload_status', room=sid)

    container_sketch_path = prepare_sketch_folder(cname, safe_username, sketch_filename)

    socketio.emit('upload_status', {'status': 'compiling', 'message': '--- ĐANG BIÊN DỊCH CODE MÔ PHỎNG ---'}, namespace='/upload_status', room=sid)
    compile_cmd = ["docker", "exec", cname, "arduino-cli", "compile", "--fqbn", board_fqbn, container_sketch_path]
    
    code, log = run_and_stream(compile_cmd, socketio, sid)
    
    if code != 0:
        socketio.emit('upload_status', {'status': 'error', 'message': '❌ Lỗi biên dịch!', 'details': log, 'suggestions': ["Vui lòng kiểm tra cú pháp mã nguồn C/C++."]}, namespace='/upload_status', room=sid)
        log_action(username, "Compile failed", success=False)
        return

    # --- BƯỚC MỚI: XẾP HÀNG CHỜ PORT VÀ FLASH THẬT CẤP ĐỘ PHẦN CỨNG ---
    socketio.emit('upload_status', {'status': 'compiling', 'message': f'Đang xếp hàng chờ cắm mạch vào cổng {port}...'}, namespace='/upload_status', room=sid)
    
    # 1. Thông báo thứ tự chờ
    queue_counts[port] += 1
    position = queue_counts[port]
    if position > 1:
         socketio.emit('upload_status', {'status': 'compiling', 'message': f'⏳ Cổng {port} đang bận! Bạn đang ở vị trí chờ #{position} trong hàng đợi...'}, namespace='/upload_status', room=sid)

    # 2. Bắt đầu Khóa (Global File Lock) cổng để nạp
    with get_hardware_lock(port):
        # --- [SMART RELEASE] Giải phóng port thông minh ---
        try:
            # 1. Phát tín hiệu cho toàn bộ IDE đóng Serial Monitor (SocketIO)
            socketio.emit('system_kick_serial', {'port': port}, namespace='/serial', broadcast=True)
            
            # 2. "Lọc PID" để giết các tiến trình Terminal đang găm port (không giết chính mình)
            import os
            try:
                # Lấy danh sách PID găm port
                pids_out = subprocess.check_output(["fuser", port], stderr=subprocess.STDOUT).decode()
                pids = pids_out.strip().split()
                my_pid = str(os.getpid())
                for pid in pids:
                    if pid != my_pid:
                        subprocess.run(["kill", "-9", pid], check=False)
            except subprocess.CalledProcessError:
                pass # Không ai dùng port

            # 3. Chờ 1s để HĐH dọn dẹp file descriptor và Board hồi phục
            import time
            time.sleep(1.5)
        except Exception as e:
            logger.warning(f"Smart Release warning: {e}")
            
        # Cooldown trước khi nạp: chờ board hồi phục thêm 1 chút
        time.sleep(1)
        
        max_retries = 3
        up_code = -1
        up_log = ""
        
        for attempt in range(1, max_retries + 1):
            socketio.emit('upload_status', {'status': 'compiling', 'message': f'🔥 Tới lượt bạn! Đang nạp code thật xuống board qua cổng {port}... (Lần {attempt}/{max_retries})'}, namespace='/upload_status', room=sid)
            
            # Chạy lệnh upload flash của Arduino-CLI
            upload_cmd = ["docker", "exec", cname, "arduino-cli", "upload", "-p", port, "--fqbn", board_fqbn, container_sketch_path]
            up_code, up_log = run_and_stream(upload_cmd, socketio, sid)
            
            if up_code == 0:
                break  # Nạp thành công, thoát vòng lặp
            
            # Nếu lỗi I/O -> chờ rồi thử lại
            if attempt < max_retries:
                socketio.emit('upload_status', {'status': 'compiling', 'message': f'⚠️ Lỗi kết nối phần cứng. Đang chờ board hồi phục... ({attempt}/{max_retries})'}, namespace='/upload_status', room=sid)
                time.sleep(3)
        
        if up_code != 0:
            suggestions = get_upload_error_suggestions(up_log)
            socketio.emit('upload_status', {'status': 'error', 'message': '❌ Lỗi Nạp Code vào bo mạch!', 'details': up_log, 'suggestions': suggestions}, namespace='/upload_status', room=sid)
            log_action(username, "Flash failed", success=False)
            queue_counts[port] -= 1
            return

    # 3. Mở Khóa cổng, trả lại cho user khác
    queue_counts[port] -= 1
    log_action(username, "Flash Hardware success")
    
    socketio.emit('upload_status', {'status': 'success', 'message': '✅ ĐÃ NẠP XUỐNG BO MẠCH THÀNH CÔNG! Code của bạn đang chạy trên thiết bị vật lý.'}, namespace='/upload_status', room=sid)

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
    else: return arduino_list + [esp32_default] + [esp8266_default]

def get_serial_ports(username):
    """
    SỬA LẠI LOGIC: Truy vấn qua bảng device_assignments (N-N) để hỗ trợ chia sẻ 1 cổng cho N sinh viên.
    Tuyệt đối không hiển thị nếu port không tồn tại hoặc bị ngắt kết nối (status='disconnected').
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
                
                # Sửa [MULTI-USER FIX]: Join qua bảng device_assignments và lấy cột status
                query = """
                    SELECT hd.port, hd.tag_name, hd.type, hd.status
                    FROM hardware_devices hd
                    JOIN device_assignments da ON hd.id = da.device_id
                    JOIN users u ON da.user_id = u.id
                    WHERE u.username = %s AND hd.status != 'disconnected'
                """
                cur.execute(query, (username,))
                for row in cur.fetchall():
                    db_devices[row['port']] = row
                cur.close()
                db.close()
        except: pass

        # 2. Quét Docker (chỉ để verify cổng thật sự tồn tại)
        cmd = ["docker", "exec", cname, "arduino-cli", "board", "list", "--format", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        final_list = []
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for item in data.get("detected_ports", []):
                address = item.get("port", {}).get("address")
                
                # Bỏ cổng rác ttyS
                if "ttyS" in address: continue 
                
                # --- [STRICT MODE] CHỈ HIỂN THỊ NẾU ĐƯỢC ADMIN CẤP QUYỀN VÀ KHÔNG BỊ DISCONNECTED ---
                if address in db_devices:
                    display_name = db_devices[address]['tag_name']
                    board_type = db_devices[address]['type']

                    boards = get_boards_by_type(board_type)
                    
                    final_list.append({
                        "port": {"address": address, "label": display_name, "protocol": "serial"},
                        "matching_boards": boards,
                        "boards": boards
                    })
        
        return {'success': True, 'ports': final_list}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_user_assigned_device(username):
    """Tự động tìm Port và FQBN tương ứng đã được cấp quyền cho User"""
    try:
        db = get_db_connection()
        if not db: return None
        cur = db.cursor(dictionary=True)
        query = """
            SELECT hd.port, hd.type, hd.status
            FROM hardware_devices hd
            JOIN device_assignments da ON hd.id = da.device_id
            JOIN users u ON da.user_id = u.id
            WHERE u.username = %s AND hd.status != 'disconnected'
            LIMIT 1
        """
        cur.execute(query, (username,))
        device = cur.fetchone()
        cur.close()
        db.close()
        
        if not device:
            return None
            
        boards = get_boards_by_type(device['type'])
        if boards and len(boards) > 0:
            fqbn = boards[0]['fqbn']
        else:
            fqbn = "arduino:avr:uno"
            
        return {
            'port': device['port'],
            'fqbn': fqbn,
            'type': device['type']
        }
    except Exception as e:
        logger.error(f"Error getting assigned device for {username}: {e}")
        return None

def detect_board_from_sketch(username, sketch_path):
    """
    Tự động nhận diện loại board từ nội dung code .ino
    Dựa vào các thư viện #include đặc trưng của từng platform:
    - ESP32: WiFi.h, BluetoothSerial.h, ESP32Servo.h, esp_camera.h, ...
    - Mặc định: Arduino Uno (arduino:avr:uno)
    """
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    
    # Đọc nội dung file sketch từ container
    try:
        read_cmd = ["docker", "exec", cname, "cat", f"/home/{safe_username}/{sketch_path}"]
        result = subprocess.run(read_cmd, capture_output=True, text=True, timeout=10)
        code = result.stdout if result.returncode == 0 else ""
    except Exception:
        code = ""
    
    # Danh sách thư viện đặc trưng chỉ có trên ESP32
    ESP32_LIBS = [
        'WiFi.h', 'WiFiClient.h', 'WiFiServer.h', 'WiFiUdp.h',
        'BluetoothSerial.h', 'BLEDevice.h', 'BLEServer.h',
        'ESP32Servo.h', 'esp_camera.h', 'esp_wifi.h',
        'WebServer.h', 'HTTPClient.h', 'SPIFFS.h',
        'esp_sleep.h', 'driver/ledc.h', 'esp32-hal-ledc.h',
    ]
    
    for lib in ESP32_LIBS:
        if f'#include <{lib}>' in code or f'#include "{lib}"' in code:
            logger.info(f"Auto-detect: Found {lib} → ESP32 for {username}")
            return 'esp32:esp32:esp32'
    
    # Danh sách các hàm đặc trưng chỉ có trên ESP32
    ESP32_FUNCS = ['ledcSetup', 'ledcWrite', 'ledcAttachPin', 'ledcAttach', 'analogReadResolution', 'hallRead']
    for func in ESP32_FUNCS:
        if func in code:
            logger.info(f"Auto-detect: Found function {func} → ESP32 for {username}")
            return 'esp32:esp32:esp32'
    
    # Mặc định: Arduino Uno
    logger.info(f"Auto-detect: No ESP32 indicators found → Arduino Uno for {username}")
    return 'arduino:avr:uno'


def compile_sketch(username, board_fqbn, sketch_path):
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    sketch_filename = os.path.basename(sketch_path)
    container_sketch_path = prepare_sketch_folder(cname, safe_username, sketch_filename)
    
    cmd = ["docker", "exec", cname, "arduino-cli", "compile", "--fqbn", board_fqbn, container_sketch_path]
    
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