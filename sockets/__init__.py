"""
Sockets package initialization
"""
from .terminal import register_terminal_handlers
from .serial_monitor import register_serial_handlers, register_upload_status_handlers

__all__ = [
    'register_terminal_handlers',
    'register_serial_handlers', 
    'register_upload_status_handlers'
]
