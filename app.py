"""
Flask-Kerberos-Demo - EPU Tech IoT Lab Management System
Main application entry point
"""
import os
import logging
import signal
import sys
from flask import Flask, redirect, url_for, session
from flask_socketio import SocketIO

# Import configurations
from config import init_db

# Import routes
from routes import auth_bp, admin_bp, user_bp, hardware_bp

# Import socket handlers
from sockets import (
    register_terminal_handlers,
    register_serial_handlers,
    register_upload_status_handlers
)

# Import background services
from services.background_services import init_background_services, stop_background_services

# ================== LOGGING SETUP ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# ================== APP INITIALIZATION ==================
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# ================== REGISTER BLUEPRINTS ==================
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(user_bp)
app.register_blueprint(hardware_bp)

# ================== REGISTER SOCKET.IO HANDLERS ==================
register_terminal_handlers(socketio)
register_serial_handlers(socketio)
register_upload_status_handlers(socketio)

# ================== MAIN ROUTES ==================
@app.route("/")
def index():
    """Main index route - redirect based on user role"""
    if "username" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin.admin_dashboard"))
        else:
            return redirect(url_for("user.user_redirect"))
    return redirect(url_for("auth.login_page"))

# ================== ERROR HANDLERS ==================
@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return "Page not found", 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal error: {e}")
    return "Internal server error", 500

# ================== BACKGROUND SERVICES ==================
background_services = None

def cleanup_on_exit(signum=None, frame=None):
    """Cleanup handler for graceful shutdown"""
    logger.info("🛑 Shutting down application...")
    
    # Stop background services
    if background_services:
        stop_background_services()
    
    logger.info("✅ Application shutdown complete")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, cleanup_on_exit)
signal.signal(signal.SIGTERM, cleanup_on_exit)

# ================== MAIN EXECUTION ==================
if __name__ == "__main__":
    try:
        # Initialize database
        init_db()
        logger.info("=" * 60)
        logger.info("🚀 EPU Tech IoT Lab Management System")
        logger.info("=" * 60)
        
        # Start background services (USB watcher, etc.)
        logger.info("🔧 Starting background services...")
        background_services = init_background_services()
        
        logger.info("✅ Application initialization complete")
        logger.info("🌐 Server running on http://[::]:5000")
        logger.info("=" * 60)
        
        # Run with SocketIO
        socketio.run(app, host="::", port=5000, debug=True)
        
    except KeyboardInterrupt:
        logger.info("\n⏹️ Received keyboard interrupt")
        cleanup_on_exit()
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        cleanup_on_exit()
