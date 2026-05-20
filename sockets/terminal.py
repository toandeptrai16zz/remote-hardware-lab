"""
Terminal Socket.IO handlers
"""
import logging
from flask import session, request
from flask_socketio import emit
from services import get_ssh_client, log_action

logger = logging.getLogger(__name__)
terminal_sessions = {}


def _close_terminal_session(sid):
    entry = terminal_sessions.pop(sid, None)
    if not entry:
        return

    username = entry.get("username", "unknown")
    chan = entry.get("chan")
    client = entry.get("client")

    try:
        if chan and getattr(chan, "active", False):
            chan.close()
    except Exception as e:
        logger.warning(f"Error closing SSH channel for {username}: {e}")

    try:
        if client:
            client.close()
    except Exception as e:
        logger.warning(f"Error closing SSH client for {username}: {e}")


def register_terminal_handlers(socketio):
    """Đăng ký các trình xử lý namespace terminal"""
    
    @socketio.on('connect', namespace='/terminal')
    def terminal_connect():
        """Xử lý kết nối terminal"""
        if 'username' not in session:
            return False

        username = session['username']
        sid = request.sid 
        
        try:
            _close_terminal_session(sid)
            client = get_ssh_client(username)
            chan = client.invoke_shell(term='xterm-256color', width=120, height=32)
            terminal_sessions[sid] = {
                "username": username,
                "client": client,
                "chan": chan,
            }
            log_action(username, "Terminal: User connected")

            def forward_output():
                """Chuyển tiếp output từ container đến trình duyệt"""
                try:
                    while terminal_sessions.get(sid, {}).get("chan") is chan and chan.active:
                        if chan.recv_ready():
                            data = chan.recv(1024)
                            if not data:
                                break
                            socketio.emit('output', data.decode('utf-8', errors='ignore'), 
                                        namespace='/terminal', room=sid) 
                        else:
                            socketio.sleep(0.1)
                except Exception as e:
                    logger.warning(f"Terminal forward_output thread for {username} ended: {e}")
                    socketio.emit('output', f'\r\n\x1b[31mConnection lost: {e}\x1b[0m\r\n', 
                                namespace='/terminal', room=sid)
            
            socketio.start_background_task(target=forward_output)
            return True
            
        except Exception as e:
            logger.error(f"SOCKET CONNECT ERROR for {username}: {e}")
            _close_terminal_session(sid)
            emit('output', f'\r\n\x1b[31mError connecting to terminal: {e}\x1b[0m\r\n', room=sid)
            return False

    @socketio.on('input', namespace='/terminal')
    def terminal_input(data):
        """Xử lý đầu vào terminal"""
        entry = terminal_sessions.get(request.sid)
        chan = entry.get("chan") if entry else None
        if not chan or not getattr(chan, "active", False):
            emit('output', '\r\n\x1b[31mTerminal session is not active.\x1b[0m\r\n')
            return

        try:
            if isinstance(data, str):
                chan.send(data)
            else:
                logger.warning(f"Invalid input data type: {type(data)}")
        except Exception as e:
            logger.error(f"SOCKET INPUT ERROR: {e}")
            emit('output', f'\r\n\x1b[31mInput error: {e}\x1b[0m\r\n')

    @socketio.on('resize', namespace='/terminal')
    def terminal_resize(data):
        """Resize remote PTY to match xterm dimensions."""
        entry = terminal_sessions.get(request.sid)
        chan = entry.get("chan") if entry else None
        if not chan or not getattr(chan, "active", False):
            return

        try:
            cols = max(20, min(int(data.get("cols", 120)), 300))
            rows = max(5, min(int(data.get("rows", 32)), 120))
            chan.resize_pty(width=cols, height=rows)
        except Exception as e:
            logger.warning(f"Terminal resize error for {entry.get('username', 'unknown')}: {e}")

    @socketio.on('disconnect', namespace='/terminal')
    def terminal_disconnect():
        """Xử lý ngắt kết nối terminal"""
        username = session.get("username", "unknown")
        sid = request.sid
        _close_terminal_session(sid)
                
        log_action(username, "Terminal: User disconnected")
