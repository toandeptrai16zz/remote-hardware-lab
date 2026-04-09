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
    """Handle hardware connection/disconnection events from udev [DISABLED]"""
    return jsonify(success=True, message="Hardware tracking physically disabled for Cloud Pivot."), 200

@hardware_bp.route('/rescan', methods=['POST'])
def hardware_rescan_api():
    """VIRTUAL API RESCAN (DISABLED)"""
    return jsonify({
        'success': True, 'database_updated': True, 'containers_synced': True,
        'devices_found': 0, 'devices': [], 'errors': []
    }), 200

@hardware_bp.route('/status', methods=['GET'])
def hardware_status_api():
    """Mock Hardware Status for Virtual Pivot"""
    return jsonify({'success': True, 'total_devices': 0, 'devices': []})