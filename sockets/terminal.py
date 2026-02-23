"""
Terminal Socket.IO handlers
"""
import logging
from flask import session, request
from flask_socketio import emit
from services import get_ssh_client, log_action

logger = logging.getLogger(__name__)

def register_terminal_handlers(socketio):
    """Register terminal namespace handlers"""
    
    @socketio.on('connect', namespace='/terminal')
    def terminal_connect():
        """Handle terminal connection"""
        if 'username' not in session:
            return False

        username = session['username']
        sid = request.sid 
        
        try:
            client = get_ssh_client(username)
            chan = client.invoke_shell(term='xterm-color')
            
            # Store in session
            session['ssh_client'] = client
            session['ssh_chan'] = chan
            log_action(username, "Terminal: User connected")

            def forward_output():
                """Forward output from container to browser"""
                try:
                    while chan.active:
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
            emit('output', f'\r\n\x1b[31mError connecting to terminal: {e}\x1b[0m\r\n', room=sid)
            return False

    @socketio.on('input', namespace='/terminal')
    def terminal_input(data):
        """Handle terminal input"""
        if 'ssh_chan' in session and session['ssh_chan'].active:
            try:
                if isinstance(data, str):
                    session['ssh_chan'].send(data)
                else:
                    logger.warning(f"Invalid input data type: {type(data)}")
            except Exception as e:
                logger.error(f"SOCKET INPUT ERROR: {e}")
                emit('output', f'\r\n\x1b[31mInput error: {e}\x1b[0m\r\n')

    @socketio.on('disconnect', namespace='/terminal')
    def terminal_disconnect():
        """Handle terminal disconnection"""
        username = session.get("username", "unknown")
        
        # Close SSH channel
        if 'ssh_chan' in session:
            try:
                if session['ssh_chan'].active:
                    session['ssh_chan'].close()
            except Exception as e:
                logger.warning(f"Error closing SSH channel for {username}: {e}")
            finally:
                session.pop('ssh_chan', None)
        
        # Close SSH client
        if 'ssh_client' in session:
            try:
                session['ssh_client'].close()
            except Exception as e:
                logger.warning(f"Error closing SSH client for {username}: {e}")
            finally:
                session.pop('ssh_client', None)
                
        log_action(username, "Terminal: User disconnected")
