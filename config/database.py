"""
Database configuration and initialization
"""
import os
import mysql.connector
from mysql.connector import pooling
import logging
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

# Global connection pool caching
_db_pool = None

def get_db_connection():
    """Get MySQL database connection from the Connection Pool"""
    global _db_pool
    try:
        if _db_pool is None:
            logger.info("Initializing MySQL Connection Pool (size=15)...")
            _db_pool = pooling.MySQLConnectionPool(
                pool_name="epu_tech_pool",
                pool_size=15,
                pool_reset_session=True,
                host=os.getenv('DB_HOST', 'localhost'),
                user=os.getenv('DB_USER', 'chuongdev_admin'),
                password=os.getenv('DB_PASSWORD', 'Chuong2004@'),
                database=os.getenv('DB_DATABASE', 'flask_app'),
                autocommit=True
            )
        return _db_pool.get_connection()
    except Exception as e:
        logger.error(f"DATABASE POOL CONNECTION ERROR: {e}")
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
    
    # --------- EXAM & MISSION TABLES ---------
    
    # Create missions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            type ENUM('exam', 'test', 'assignment') NOT NULL DEFAULT 'assignment',
            duration_minutes INT DEFAULT 90,
            template_code TEXT NULL,
            start_time DATETIME NULL,
            end_time DATETIME NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create mission assignments table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mission_assignments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            mission_id INT NOT NULL,
            user_id INT NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE KEY (mission_id, user_id)
        )
    """)
    
    # Create submissions table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            mission_id INT NOT NULL,
            user_id INT NOT NULL,
            files JSON,
            is_auto_submit BOOLEAN DEFAULT FALSE,
            score DECIMAL(4, 2) NULL,
            ai_feedback TEXT NULL,
            ai_criteria JSON NULL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (mission_id) REFERENCES missions(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE KEY (mission_id, user_id)
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
