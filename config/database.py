"""
Database configuration and initialization
"""
import os
import mysql.connector
import logging
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

def get_db_connection():
    """Get MySQL database connection"""
    try:
        db_user = os.getenv('DB_USER', 'chuongdev_admin')
        db_password = os.getenv('DB_PASSWORD', 'Chuong2004@')
        db_database = os.getenv('DB_DATABASE', 'flask_app')
        db_host = os.getenv('DB_HOST', 'localhost')

        return mysql.connector.connect(
            host=db_host, 
            user=db_user, 
            password=db_password, 
            database=db_database, 
            autocommit=True
        )
    except Exception as e:
        logger.error(f"DATABASE CONNECTION ERROR: {e}")
        return None

def init_db():
    """Initialize database tables and default admin user"""
    db = get_db_connection()
    if not db: 
        return
        
    cur = db.cursor()
    
    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY, 
            username VARCHAR(50) NOT NULL UNIQUE, 
            password VARCHAR(255) NOT NULL, 
            email VARCHAR(255) NULL UNIQUE, 
            role ENUM('admin','user') NOT NULL DEFAULT 'user', 
            status ENUM('pending','active','blocked') NOT NULL DEFAULT 'pending', 
            ssh_port INT NULL, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, 
            last_login TIMESTAMP NULL
        )
    """)
    
    # Create hardware_devices table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS hardware_devices (
            id INT AUTO_INCREMENT PRIMARY KEY, 
            tag_name VARCHAR(100) NOT NULL UNIQUE, 
            type VARCHAR(100) NOT NULL, 
            port VARCHAR(100) NOT NULL UNIQUE, 
            status ENUM('available', 'in_use', 'maintenance') NOT NULL DEFAULT 'available', 
            in_use_by VARCHAR(50) NULL, 
            FOREIGN KEY (in_use_by) REFERENCES users(username) ON DELETE SET NULL
        )
    """)
    
    # Create logs table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INT AUTO_INCREMENT PRIMARY KEY, 
            username VARCHAR(50) NOT NULL, 
            action VARCHAR(255) NOT NULL, 
            timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, 
            ip_address VARCHAR(45) NULL, 
            user_agent TEXT NULL, 
            success BOOLEAN DEFAULT TRUE, 
            details JSON NULL
        )
    """)
    
    # Create device_assignments table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS device_assignments (
            id INT AUTO_INCREMENT PRIMARY KEY, 
            user_id INT NOT NULL, 
            device_id INT NOT NULL, 
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
            expires_at TIMESTAMP NULL, 
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE, 
            FOREIGN KEY (device_id) REFERENCES hardware_devices(id) ON DELETE CASCADE, 
            UNIQUE KEY (user_id, device_id)
        )
    """)
    
    # Create default admin user if not exists
    cur.execute("SELECT id FROM users WHERE username='admin'")
    if not cur.fetchone():
        hashed_password = generate_password_hash('admin123@')
        cur.execute(
            "INSERT INTO users (username, password, email, role, status) VALUES (%s, %s, %s, %s, %s)", 
            ('admin', hashed_password, 'admin@eputech.com', 'admin', 'active')
        )
        logger.info("Created default admin user")
    
    db.commit()
    cur.close()
    db.close()
