"""
Services package initialization
"""
from .security import (
    generate_csrf_token, validate_csrf_token,
    generate_captcha, validate_captcha,
    generate_otp, send_otp_email,
    validate_password_strength,
    otp_storage, csrf_tokens, login_attempts
)
from .logger import log_action
from .docker_manager import (
    ensure_user_container, ensure_user_container_and_setup,
    setup_arduino_cli_for_user, setup_container_permissions,
    get_all_running_users, docker_status
)
from .ssh_manager import get_ssh_client
from .arduino import (
    compile_sketch, perform_upload_worker,
    get_serial_ports, 
    analyze_compile_errors,      # Hàm mới
    get_upload_error_suggestions # Hàm mới thay thế cho analyze_upload_errors
)

# Import module USB sync mới
try:
    from .docker_usb_sync import handle_usb_rescan
except ImportError:
    # Fallback nếu chưa có file docker_usb_sync (tránh lỗi import loop)
    pass

__all__ = [
    # Security
    'generate_csrf_token', 'validate_csrf_token',
    'generate_captcha', 'validate_captcha',
    'generate_otp', 'send_otp_email',
    'validate_password_strength',
    'otp_storage', 'csrf_tokens', 'login_attempts',
    
    # Logger
    'log_action',
    
    # Docker
    'ensure_user_container', 'ensure_user_container_and_setup',
    'setup_arduino_cli_for_user', 'setup_container_permissions',
    'get_all_running_users', 'docker_status',
    
    # SSH
    'get_ssh_client',
    
    # Arduino
    'compile_sketch', 'perform_upload_worker',
    'get_serial_ports', 
    'analyze_compile_errors',
    'get_upload_error_suggestions',

    # USB Sync
    'handle_usb_rescan'
]