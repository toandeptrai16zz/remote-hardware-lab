"""
Serial monitor and upload status Socket.IO handlers
OPTIMIZED: Batching data to prevent Browser Freeze (Web đơ)
"""
import serial
import logging
import time
from flask import session, request
from flask_socketio import emit
from services.logger import log_action

logger = logging.getLogger(__name__)

# Storage for serial sessions and user SIDs
serial_sessions = {}
user_sids = {}

def read_serial_data(socketio, sid, ser, username):
    """
    Background task to read serial data
    OPTIMIZATION: 
    - Sử dụng bộ đệm (buffer) để gom dữ liệu
    - Chỉ gửi dữ liệu 100ms/lần (Throttling) để tránh làm đơ trình duyệt
    """
    logger.info(f"Started serial reader thread for {username} on {ser.port}")
    
    buffer = ""
    last_emit_time = time.time()

    try:
        while True:
            # Check if session is still valid
            if sid not in serial_sessions or not ser.is_open:
                break
                
            # 1. Đọc dữ liệu vào bộ đệm
            try:
                available = ser.in_waiting
                if available > 0:
                    data = ser.read(min(available, 4096))
                    if data:
                        buffer += data.decode('utf-8', errors='replace')
            except Exception as e:
                logger.error(f"Serial read error: {e}")
                socketio.emit('serial_error', {'error': str(e)}, namespace='/serial', room=sid)
                break
            
            # 2. Gom lô (Batching) để gửi qua WebSocket
            current_time = time.time()
            if buffer and ((current_time - last_emit_time) > 0.2 or len(buffer) > 2048):
                socketio.emit('serial_data', {'data': buffer}, namespace='/serial', room=sid)
                buffer = ""
                last_emit_time = current_time

            # 3. Tránh ăn CPU vọt lên 100%
            # Ngủ 50ms nếu đang rảnh rỗi (Không có data chờ), ngược lại ngủ 10ms để dọn nốt buffer
            socketio.sleep(0.01 if ser.in_waiting > 0 else 0.05)
                        
    except Exception as e:
        logger.error(f"Serial thread crash: {e}")
    finally:
        logger.info(f"Serial reader thread stopped for {username}")
        if ser.is_open:
            ser.close()

def stop_existing_monitor(sid):
    """Stop existing serial monitor"""
    if sid in serial_sessions:
        ser = serial_sessions.pop(sid, None)
        if ser and ser.is_open:
            try:
                ser.close()
                logger.info(f"Cleanly closed serial port {ser.port} for session {sid}.")
            except Exception as e:
                logger.warning(f"Ignoring error while closing port: {e}")

def force_close_port(port):
    """[SMART RELEASE] Đóng ngay lập tức đối tượng pyserial đang giữ port này trên Server-side"""
    for sid, ser in list(serial_sessions.items()):
        if ser and ser.port == port:
            if ser.is_open:
                try:
                    ser.close()
                    logger.info(f"Forcefully closed serial port {port} for session {sid} on server-side.")
                except Exception as e:
                    logger.warning(f"Ignoring error while force closing port: {e}")
            serial_sessions.pop(sid, None)

def register_serial_handlers(socketio):
    """Register serial monitor namespace handlers"""
    
    @socketio.on('start_monitor', namespace='/serial')
    def start_serial_monitor(data):
        """Bắt đầu Serrial"""
        username = session.get("username")
        if not username: 
            return
        
        port = data.get('port')
        baud_rate = int(data.get('baud_rate', 9600))
        sid = request.sid
        
        if not port:
            emit('serial_error', {'error': 'Port is required'})
            return
            
        # Xóa các session cũ
        stop_existing_monitor(sid)
        
        try:
            # Open Serial Port (Non-blocking mode slightly safer)
            ser = serial.Serial(port=port, baudrate=baud_rate, timeout=0)
            serial_sessions[sid] = ser
            
            # Start background task
            socketio.start_background_task(
                target=read_serial_data, 
                socketio=socketio, 
                sid=sid, 
                ser=ser, 
                username=username
            )

            emit('status', {'message': f'Đang đọc {port} @ {baud_rate} baud...'})
            log_action(username, f"Started Serial Monitor on {port}")
            
        except serial.SerialException as e:
            logger.error(f"Cannot open {port}: {e}")
            emit('serial_error', {'error': f'Không thể mở cổng {port}. Có thể đang được sử dụng.'})
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            emit('serial_error', {'error': str(e)})

    @socketio.on('stop_monitor', namespace='/serial')
    def stop_serial_monitor():
        """Stop serial monitor"""
        stop_existing_monitor(request.sid)
        emit('status', {'message': 'Đã ngắt kết nối.'})

    @socketio.on('send_data', namespace='/serial')
    def send_serial_data(data):
        """Send data to serial port"""
        sid = request.sid
        if sid in serial_sessions:
            ser = serial_sessions[sid]
            if ser and ser.is_open:
                try:
                    payload = data.get('data', '')
                    if payload:
                        # Thêm ký tự xuống dòng nếu cần (tùy chọn)
                        ser.write(payload.encode('utf-8'))
                except Exception as e:
                    emit('serial_error', {'error': str(e)})

    @socketio.on('disconnect', namespace='/serial')
    def serial_disconnect():
        """Handle disconnection"""
        stop_existing_monitor(request.sid)

def register_upload_status_handlers(socketio):
    """Register upload status namespace handlers"""
    
    @socketio.on('connect', namespace='/upload_status')
    def upload_status_connect():
        """Handle upload status connection"""
        username = session.get("username")
        if not username:
            return False
        
        if username not in user_sids:
            user_sids[username] = []
        user_sids[username].append(request.sid)