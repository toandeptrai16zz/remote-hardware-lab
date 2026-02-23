"""
Routes package initialization
"""
from .auth import auth_bp
from .admin import admin_bp
from .user import user_bp
from .hardware import hardware_bp

__all__ = ['auth_bp', 'admin_bp', 'user_bp', 'hardware_bp']
