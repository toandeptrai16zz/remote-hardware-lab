"""
Enhanced Hardware Routes với Full USB Support & Smart Naming
"""
import glob
from flask import Blueprint, request, jsonify, current_app
from utils import require_internal_secret
from config import get_db_connection, DEVICE_ID_MAP
from services import log_action

# --- FIX IMPORT: Import đúng từ package services ---
try:
    from services.docker_usb_sync import handle_usb_rescan
except ImportError:
    def handle_usb_rescan():
        return {'success': False, 'message': 'Module docker_usb_sync not found'}

hardware_bp = Blueprint('hardware', __name__, url_prefix='/api/hardware')

# --- HÀM THÔNG MINH ĐỂ ĐẶT TÊN BOARD ---
def smart_detect_board(port):
    """
    Đoán tên board dựa trên tên cổng Linux
    ttyACM* -> Thường là Arduino Uno/Mega
    ttyUSB* -> Thường là ESP32/ESP8266 hoặc Arduino Nano
    """
    name = port.split('/')[-1] # Lấy phần cuối (ttyUSB0)
    
    if "ttyACM" in name:
        return {
            "tag_name": f"Arduino-Uno-{name}", 
            "type": "Arduino AVR"
        }
    elif "ttyUSB" in name:
        return {
            "tag_name": f"ESP32-NodeMCU-{name}", 
            "type": "ESP32/ESP8266"
        }
    else:
        return {
            "tag_name": f"Device-{name}", 
            "type": "Generic Serial"
        }

@hardware_bp.route('/event', methods=['POST'])
@require_internal_secret
def hardware_event_api():
    """Handle hardware connection/disconnection events from udev"""
    data = request.get_json()
    port = data.get("port")
    vendor_id = data.get("vendor_id")
    product_id = data.get("product_id")
    event_type = data.get("event_type", "add")

    if not port:
        return jsonify(success=False, error="Missing port information"), 400

    db = get_db_connection()
    if not db: 
        return jsonify(success=False, error="Database connection failed"), 500
    cur = db.cursor(dictionary=True)

    if event_type == "add":
        # === LOGIC ĐẶT TÊN MỚI TẠI ĐÂY ===
        smart_info = smart_detect_board(port)
        
        # Nếu có trong Map cứng thì ưu tiên, không thì dùng Smart Detect
        device_key = f"{vendor_id}:{product_id}"
        if device_key in DEVICE_ID_MAP:
             device_info = DEVICE_ID_MAP[device_key]
             tag_name = f"{device_info['tag_prefix']}-{port.split('/')[-1]}"
             device_type = device_info['type']
        else:
             tag_name = smart_info['tag_name']
             device_type = smart_info['type']
        
        try:
            cur.execute("SELECT id FROM hardware_devices WHERE port = %s", (port,))
            existing_device = cur.fetchone()

            if existing_device:
                cur.execute(
                    "UPDATE hardware_devices SET tag_name = %s, type = %s, status = 'available' WHERE id = %s", 
                    (tag_name, device_type, existing_device['id'])
                )
                log_action('udev_listener', f"Hardware re-connected: {port}", success=True, details=data)
            else:
                cur.execute(
                    "INSERT INTO hardware_devices (tag_name, type, port, status) VALUES (%s, %s, %s, 'available')", 
                    (tag_name, device_type, port)
                )
                log_action('udev_listener', f"New hardware detected: {port}", success=True, details=data)
            
            db.commit()
            return jsonify(success=True, message=f"Device {tag_name} on {port} registered.")
        finally:
            cur.close()
            db.close()

    elif event_type == "remove":
        try:
            cur.execute(
                "UPDATE hardware_devices SET status = 'maintenance', in_use_by = NULL WHERE port = %s", 
                (port,)
            )
            db.commit()
            log_action('udev_listener', f"Hardware removed: {port}", success=True, details=data)
            return jsonify(success=True, message=f"Device on {port} marked as removed.")
        finally:
            cur.close()
            db.close()
    
    return jsonify(success=False, error="Invalid event type"), 400

@hardware_bp.route('/rescan', methods=['POST'])
def hardware_rescan_api():
    """ULTIMATE USB RESCAN API"""
    current_app.logger.info("=" * 70)
    current_app.logger.info("🔍 USB RESCAN REQUEST RECEIVED")
    current_app.logger.info("=" * 70)
    
    result = {
        'success': False, 'database_updated': False, 'containers_synced': False,
        'devices_found': 0, 'devices': [], 'errors': []
    }
    
    # ========================================================================
    # PART 1: SCAN AND UPDATE DATABASE
    # ========================================================================
    try:
        current_app.logger.info(" PART 1: Scanning and updating database...")
        physical_ports_list = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
        physical_ports = set(physical_ports_list)
        
        result['devices_found'] = len(physical_ports)
        result['devices'] = list(physical_ports)
        
        db = get_db_connection()
        if db:
            cur = db.cursor(dictionary=True)
            cur.execute("SELECT port, status FROM hardware_devices")
            db_ports = {row['port']: row['status'] for row in cur.fetchall()}

            for port in physical_ports:
                # === LOGIC ĐẶT TÊN MỚI CHO RESCAN ===
                smart_info = smart_detect_board(port)
                
                if port not in db_ports:
                    cur.execute(
                        "INSERT INTO hardware_devices (tag_name, type, port, status) VALUES (%s, %s, %s, 'available')", 
                        (smart_info['tag_name'], smart_info['type'], port)
                    )
                    current_app.logger.info(f"Added new device: {port} as {smart_info['tag_name']}")
                    
                elif db_ports[port] == 'maintenance':
                    # Update lại tên luôn nếu cắm lại để nó mới nhất
                    cur.execute(
                        "UPDATE hardware_devices SET status='available', tag_name=%s, type=%s WHERE port=%s", 
                        (smart_info['tag_name'], smart_info['type'], port)
                    )
                    current_app.logger.info(f"🔄 Re-activated device: {port}")

            for port in db_ports:
                if port not in physical_ports and db_ports[port] != 'maintenance':
                    cur.execute(
                        "UPDATE hardware_devices SET status='maintenance', in_use_by=NULL WHERE port=%s", 
                        (port,)
                    )
            db.commit()
            cur.close()
            db.close()
            result['database_updated'] = True
            
    except Exception as e:
        error_msg = f"Database update error: {e}"
        current_app.logger.error(f"❌ {error_msg}")
        result['errors'].append(error_msg)

    # ========================================================================
    # PART 2: SYNC CONTAINERS
    # ========================================================================
    try:
        current_app.logger.info("🐳 PART 2: Syncing Docker containers...")
        sync_result = handle_usb_rescan()
        result['containers_synced'] = sync_result.get('success', False)
        if not result['containers_synced']:
             result['errors'].append(sync_result.get('message', 'Sync failed'))

    except Exception as e:
        error_msg = f"Container sync error: {e}"
        current_app.logger.error(f"❌ {error_msg}")
        result['errors'].append(error_msg)

    result['success'] = (result['database_updated'] and result['containers_synced'] and len(result['errors']) == 0)
    status_code = 200 if result['success'] else 500
    return jsonify(result), status_code

@hardware_bp.route('/status', methods=['GET'])
def hardware_status_api():
    """Get current hardware status"""
    try:
        db = get_db_connection()
        if not db: return jsonify(success=False, error="Database connection failed"), 500
        cur = db.cursor(dictionary=True)
        cur.execute("""
            SELECT hd.id, hd.tag_name, hd.type, hd.port, hd.status, hd.in_use_by, u.username as assigned_user
            FROM hardware_devices hd LEFT JOIN users u ON hd.in_use_by = u.id ORDER BY hd.port
        """)
        devices = cur.fetchall()
        cur.close(), db.close()
        return jsonify({'success': True, 'total_devices': len(devices), 'devices': devices})
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500