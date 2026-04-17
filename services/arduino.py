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
import time
from collections import defaultdict
from contextlib import contextmanager
from utils.metrics import FLASH_QUEUE_DEPTH, USB_DEVICE_STATUS
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
    Sử dụng vòng lặp Non-blocking để không làm treo eventlet event loop.
    """
    safe_port = port_address.replace("/", "_").replace(".", "_")
    lock_path = f"/tmp/arduino_flash_{safe_port}.lock"
    
    # Đảm bảo file tồn tại
    with open(lock_path, 'a') as f:
        pass
        
    lock_file = open(lock_path, 'r+')
    try:
        # LOCK_EX | LOCK_NB: Khóa độc quyền, không chặn (Non-blocking)
        # Giúp đồng bộ hóa xuyên Process nhưng không làm treo eventlet loop
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except (IOError, OSError):
                # Nếu đang bị khóa, đợi 0.5s rồi thử lại
                time.sleep(0.5)
        yield
    finally:
        # LOCK_UN: Mở khóa
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        except: pass
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
            if socketio:
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
    """Quy trình nạp kết hợp Hàng đợi (Queue) và Khóa (Lock) phần cứng."""
    print(f"\nDEBUG: [FLASH] perform_upload_worker started for {username}")
    
    if socketio is None:
        try:
            from __main__ import socketio
        except ImportError:
            print("DEBUG: [FLASH] Error: socketio not found in __main__")
            return

    queue_counts[port] += 1
    FLASH_QUEUE_DEPTH.labels(port=port).set(queue_counts[port])
    try:
        safe_username = make_safe_name(username)
        cname = f"{safe_username}-dev"
        sketch_filename = os.path.basename(sketch_path)

        socketio.emit('upload_status', {'status': 'start', 'message': f'Bắt đầu Testbench cho {board_fqbn}...'}, namespace='/upload_status', room=sid)

        container_sketch_path = prepare_sketch_folder(cname, safe_username, sketch_filename)

        # 1. BIÊN DỊCH
        socketio.emit('upload_status', {'status': 'compiling', 'message': '--- ĐANG BIÊN DỊCH CODE ---'}, namespace='/upload_status', room=sid)
        compile_cmd = ["docker", "exec", cname, "arduino-cli", "compile", "--fqbn", board_fqbn, container_sketch_path]
        
        code, log = run_and_stream(compile_cmd, socketio, sid)
        
        if code != 0:
            socketio.emit('upload_status', {'status': 'error', 'message': '❌ Lỗi biên dịch!', 'details': log, 'suggestions': ["Vui lòng kiểm tra cú pháp mã nguồn."]}, namespace='/upload_status', room=sid)
            log_action(username, "Compile failed", success=False)
            return

        # 2. XẾP HÀNG CHỜ PORT VÀ FLASH THẬT
        position = queue_counts[port]
        if position > 1:
            socketio.emit('upload_status', {'status': 'compiling', 'message': f'⏳ Cổng {port} đang bận! Bạn đang ở vị trí #{position}...'}, namespace='/upload_status', room=sid)

        with get_hardware_lock(port):
            # --- [SMART RELEASE] ---
            try:
                # 1. Ngắt Serial Monitor từ phía Client (Frontend) qua SocketIO
                socketio.emit('system_kick_serial', {'port': port}, namespace='/serial', broadcast=True)
                
                # 2. Cưỡng bức đóng Serial Monitor ngay trên Server-side
                try:
                    from sockets.serial_monitor import force_close_port
                    force_close_port(port)
                except ImportError as e:
                    logger.warning(f"Could not import force_close_port: {e}")
                except Exception as e:
                    logger.warning(f"Error calling force_close_port: {e}")

                # 3. Giết các Terminal khác găm port (ngoại trừ process hiện tại)
                try:
                    pids_out = subprocess.check_output(["fuser", port], stderr=subprocess.STDOUT).decode()
                    pids = pids_out.strip().split()
                    my_pid = str(os.getpid())
                    for pid in pids:
                        if pid != my_pid:
                            subprocess.run(["kill", "-9", pid], check=False)
                except subprocess.CalledProcessError:
                    pass 

                time.sleep(1.5)
            except Exception as e:
                logger.warning(f"Smart Release warning: {e}")
            
            time.sleep(1)
            
            max_retries = 3
            up_code = -1
            up_log = ""
            
            for attempt in range(1, max_retries + 1):
                socketio.emit('upload_status', {'status': 'compiling', 'message': f'🔥 Tới lượt bạn! Đang nạp code xuống board {port}... ({attempt}/{max_retries})'}, namespace='/upload_status', room=sid)
                
                upload_cmd = ["docker", "exec", cname, "arduino-cli", "upload", "-p", port, "--fqbn", board_fqbn, container_sketch_path]
                up_code, up_log = run_and_stream(upload_cmd, socketio, sid)
                
                if up_code == 0:
                    break
                
                if attempt < max_retries:
                    socketio.emit('upload_status', {'status': 'compiling', 'message': f'⚠️ Lỗi kết nối. Đang thử lại ({attempt}/{max_retries})...'}, namespace='/upload_status', room=sid)
                    time.sleep(3)
            
            if up_code != 0:
                suggestions = get_upload_error_suggestions(up_log)
                socketio.emit('upload_status', {'status': 'error', 'message': '❌ Lỗi nạp code vật lý!', 'details': up_log, 'suggestions': suggestions}, namespace='/upload_status', room=sid)
                return

        log_action(username, "Flash Hardware success")
        socketio.emit('upload_status', {'status': 'success', 'message': '✅ ĐÃ NẠP THÀNH CÔNG XUỐNG MẠCH THẬT!'}, namespace='/upload_status', room=sid)

    except Exception as e:
        logger.error(f"Worker crash for {username}: {e}")
        if socketio:
            socketio.emit('upload_status', {'status': 'error', 'message': f'❌ Lỗi hệ thống: {str(e)}'}, namespace='/upload_status', room=sid)
    finally:
        queue_counts[port] = max(0, queue_counts[port] - 1)
        FLASH_QUEUE_DEPTH.labels(port=port).set(queue_counts[port])
        print(f"DEBUG: [FLASH] Worker finished for {username}. Queue for {port} now: {queue_counts[port]}")

# ==============================================================================
# 5. CÁC HÀM SCAN & HELPERS KHÁC
# ==============================================================================
def get_upload_error_suggestions(output):
    suggestions = []
    if "Permission denied" in output: suggestions.append("Lỗi quyền truy cập cổng USB.")
    if "Packet content transfer stopped" in output: suggestions.append("Mất kết nối. Thử cáp USB khác.")
    if "Timed out" in output: suggestions.append("Hết thời gian chờ. Kiểm tra nút BOOT.")
    return suggestions

def get_boards_by_type(db_type):
    t = str(db_type).lower() if db_type else "generic"
    esp32_default = {"name": "ESP32 Dev Module", "fqbn": "esp32:esp32:esp32"}
    esp8266_default = {"name": "ESP8266 NodeMCU", "fqbn": "esp8266:esp8266:nodemcuv2"}
    nano_default = {"name": "Arduino Nano", "fqbn": "arduino:avr:nano:cpu=atmega328old"}
    uno_default = {"name": "Arduino Uno", "fqbn": "arduino:avr:uno"}
    
    if "esp32" in t: return [esp32_default]
    elif "esp8266" in t: return [esp8266_default]
    elif "nano" in t: return [nano_default]
    else: return [uno_default, esp32_default]

def get_serial_ports(username):
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    try:
        db_devices = {} 
        db = get_db_connection()
        if db:
            cur = db.cursor(dictionary=True)
            query = """
                SELECT hd.port, hd.tag_name, hd.type, hd.status
                FROM hardware_devices hd
                JOIN device_assignments da ON hd.id = da.device_id
                JOIN users u ON da.user_id = u.id
                WHERE u.username = %s AND hd.status != 'disconnected'
            """
            cur.execute(query, (username,))
            for row in cur.fetchall():
                address = row['port']
                db_devices[address] = row
                # Update USB status metric (1=available as it is in DB and not disconnected)
                USB_DEVICE_STATUS.labels(port=address).set(1)
            cur.close()
            db.close()

        cmd = ["docker", "exec", cname, "arduino-cli", "board", "list", "--format", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        final_list = []
        if result.returncode == 0:
            data = json.loads(result.stdout)
            for item in data.get("detected_ports", []):
                address = item.get("port", {}).get("address")
                if "ttyS" in address: continue 
                if address in db_devices:
                    display_name = db_devices[address]['tag_name']
                    board_type = db_devices[address]['type']
                    boards = get_boards_by_type(board_type)
                    final_list.append({
                        "port": {"address": address, "label": display_name},
                        "boards": boards
                    })
        return {'success': True, 'ports': final_list}
    except Exception as e:
        return {'success': False, 'error': str(e)}

_routing_lock = None

def get_user_assigned_device(username, reserve=False):
    """
    [HARDWARE LOAD BALANCING & POOLING]
    Áp dụng thuật toán Load Balancing với Race Condition Protection (Reserve).
    """
    import threading
    global _routing_lock
    if _routing_lock is None:
        _routing_lock = threading.Lock()
        
    with _routing_lock:
        try:
            db = get_db_connection()
            if not db: return None
            cur = db.cursor(dictionary=True)
            query = """
                SELECT hd.port, hd.type FROM hardware_devices hd
                JOIN device_assignments da ON hd.id = da.device_id
                JOIN users u ON da.user_id = u.id
                WHERE u.username = %s AND hd.status != 'disconnected'
            """
            cur.execute(query, (username,))
            devices = cur.fetchall()
            cur.close()
            db.close()
            
            # --- THUẬT TOÁN ĐỊNH TUYẾN THÔNG MINH (SMART ROUTING) ---
            import random
            
            # 1. Tìm giá trị queue nhỏ nhất hiện tại
            min_queue = min(queue_counts[d['port']] for d in devices)
            
            # 2. Lọc ra danh sách các thiết bị có cùng lượng queue nhỏ nhất này
            candidates = [d for d in devices if queue_counts[d['port']] == min_queue]
            
            # 3. Random 1 cổng trong nhóm rảnh nhất để chia đều hao mòn phần cứng (Round-Robin Random)
            best_device = random.choice(candidates)
            
            if reserve:
                queue_counts[best_device['port']] += 1
                logger.info(f"⚡ [LOAD BALANCER] {username} RESERVED {best_device['port']} (Queue increased to {queue_counts[best_device['port']]}, Candidates size: {len(candidates)})")
            
            boards = get_boards_by_type(best_device['type'])
            return {
                'port': best_device['port'], 
                'fqbn': boards[0]['fqbn'] if boards else "arduino:avr:uno",
                'type': best_device['type']
            }
        except Exception as e:
            logger.error(f"Error in Load Balancing for {username}: {e}")
            return None

def detect_board_from_sketch(username, sketch_path):
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    try:
        read_cmd = ["docker", "exec", cname, "cat", f"/home/{safe_username}/{sketch_path}"]
        result = subprocess.run(read_cmd, capture_output=True, text=True, timeout=10)
        code = result.stdout if result.returncode == 0 else ""
        # Nhận diện ESP32 qua các thư viện và hàm đặc thù, bao gồm cả FreeRTOS
        esp32_keywords = [
            'WiFi.h', 'BLEDevice.h', 'ledcSetup', 
            'xTaskCreate', 'vTaskDelay', 'SemaphoreHandle_t', 
            'xQueueCreate', 'portMAX_DELAY', 'xSemaphore'
        ]
        if any(kw in code for kw in esp32_keywords):
            return 'esp32:esp32:esp32'
        return 'arduino:avr:uno'
    except:
        return 'arduino:avr:uno'

def compile_sketch(username, board_fqbn, sketch_path):
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    sketch_filename = os.path.basename(sketch_path)
    container_sketch_path = prepare_sketch_folder(cname, safe_username, sketch_filename)
    cmd = ["docker", "exec", cname, "arduino-cli", "compile", "--fqbn", board_fqbn, container_sketch_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        analysis = analyze_compile_errors(result.stderr + result.stdout)
        return {'success': result.returncode == 0, 'output': result.stdout + result.stderr, 'analysis': analysis}
    except Exception as e:
        return {'success': False, 'output': str(e)}