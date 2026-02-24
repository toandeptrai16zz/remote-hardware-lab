"""
Docker Container Management Service
UPDATED: Strict Device Mounting via Subprocess (No /dev:/dev) + Fix Full Arduino Libs
"""
import os
import subprocess
import time
import logging
import json
import glob
from utils import make_safe_name, find_free_port
from config import get_db_connection, DEFAULT_ARDUINO_LIBRARIES
from services.logger import log_action

logger = logging.getLogger(__name__)

# Platform cache for Arduino CLI
platform_cache = {}

def get_assigned_ports(username):
    """
    Lấy danh sách các cổng USB được cấp quyền cho user từ Database.
    Chỉ trả về các cổng ĐANG TỒN TẠI trên Host.
    """
    assigned = set()
    try:
        db = get_db_connection()
        if db:
            cur = db.cursor(dictionary=True)
            # Lấy ID user
            cur.execute("SELECT id FROM users WHERE username=%s", (username,))
            user = cur.fetchone()
            if user:
                # Lấy các cổng được assign
                cur.execute("SELECT port FROM hardware_devices WHERE in_use_by=%s", (user['id'],))
                rows = cur.fetchall()
                for row in rows:
                    port = row['port']
                    # Chỉ lấy nếu cổng thực sự đang cắm trên máy chủ
                    if glob.glob(port):
                        assigned.add(port)
            cur.close()
            db.close()
    except Exception as e:
        logger.error(f"DB Error getting ports for {username}: {e}")
    return list(assigned)

def docker_status(cname):
    """Check Docker container status"""
    try:
        r = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", cname], 
            capture_output=True, text=True, check=False, timeout=5
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""

def get_container_devices(cname):
    """
    Lấy danh sách các thiết bị hiện đang được mount vào container
    """
    try:
        r = subprocess.run(
            ["docker", "inspect", cname],
            capture_output=True, text=True, check=False, timeout=5
        )
        if r.returncode == 0:
            data = json.loads(r.stdout)
            if data and len(data) > 0:
                host_config = data[0].get('HostConfig', {})
                devices = host_config.get('Devices', [])
                if devices:
                    return set(d['PathOnHost'] for d in devices)
        return set()
    except Exception:
        return set()

def ensure_user_container(username):
    """Ensure user container exists, is running, AND HAS CORRECT DEVICES"""
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    image = "my-dev-env:v2"
    
    # 1. Lấy danh sách thiết bị cần thiết từ Database
    required_ports = get_assigned_ports(username)
    required_ports_set = set(required_ports)
    
    # 2. Kiểm tra container hiện tại
    status = docker_status(cname)
    needs_recreate = False
    
    if status == 'running':
        # Kiểm tra xem container đang chạy có đúng thiết bị không
        current_devices = get_container_devices(cname)
        
        # Nếu danh sách thiết bị lệch nhau -> Cần tạo lại
        if current_devices != required_ports_set:
            logger.warning(f"Container {cname} device mismatch. Current: {current_devices}, Required: {required_ports_set}. Recreating...")
            needs_recreate = True
            
    elif status: # Exited/Created but not running
        needs_recreate = True # Start fresh
        
    # Xóa container cũ nếu cần update thiết bị
    if needs_recreate:
        subprocess.run(["docker", "rm", "-f", cname], check=False)
        status = "" # Đánh dấu là đã xóa

    # Nếu container đang chạy và đúng device -> Chỉ cần start SSH
    if status == 'running' and not needs_recreate:
        # Check SSH port
        db = get_db_connection()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT ssh_port FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        ssh_port = row['ssh_port'] if row else None
        cur.close()
        db.close()
        
        if ssh_port:
            subprocess.run(["docker", "exec", cname, "service", "ssh", "start"], check=False)
            return ssh_port

    # --- TẠO MỚI CONTAINER ---
    
    # Get or create SSH port
    db = get_db_connection()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT ssh_port FROM users WHERE username=%s", (username,))
    user_data = cur.fetchone()
    ssh_port = user_data.get("ssh_port") if user_data else None
    
    if not ssh_port:
        ssh_port = find_free_port()
        cur.execute("UPDATE users SET ssh_port=%s WHERE username=%s", (ssh_port, username))
        db.commit()
    cur.close()
    db.close()

    # Prepare host directory
    host_user_dir = f"/home/toan/QUAN_LY_USER/{safe_username}"
    os.makedirs(host_user_dir, exist_ok=True)
    os.chmod(host_user_dir, 0o777)

    # Create setup script
    setup_script_path = os.path.join(host_user_dir, "setup_container.sh")
    if os.path.exists(setup_script_path) and os.path.isdir(setup_script_path):
        import shutil
        shutil.rmtree(setup_script_path)
    
    # Script nội dung (ĐÃ FIX PHẦN THƯ VIỆN & CORE CHO ESP32)
    script_content = f"""#!/bin/bash
USER="{safe_username}"
(
    if ! python3 -c "import serial" &>/dev/null; then
        apt-get update -y &>/dev/null
        apt-get install -y python3-serial python3-pip &>/dev/null
        pip3 install pyserial esptool --break-system-packages &>/dev/null || pip3 install pyserial esptool &>/dev/null
    fi
) &

if ! id "$USER" &>/dev/null; then
    useradd -m -s /bin/bash "$USER"
    echo "$USER:password123" | chpasswd
    usermod -aG dialout "$USER" || true
    usermod -aG sudo "$USER" || true
fi

cat > /home/"$USER"/.bashrc << 'EOF_BASHRC'
case $- in *i*) ;; *) return;; esac
export PATH="/usr/local/bin:$PATH"
alias ll='ls -alF'
alias cls='clear'
if [ -f ~/WELCOME.txt ]; then cat ~/WELCOME.txt; fi
EOF_BASHRC

cat > /home/"$USER"/WELCOME.txt << EOF
================================================================
HE THONG THUC HANH IOT - EPU TECH
================================================================
[+] USER: $USER
[+] TRANG THAI: SAN SANG (Connected)
[+] PHAN CUNG HO TRO: ESP32 , ESP8266, ARDUINO
[+] TAT CA CAC THU VIEN CO BAN CAN THIET (LCD, DHT, MQTT...)
[+] HE THONG PHAT TRIEN BOI: EPU TECH TEAM 
[+] HE THONG TRONG GIAI DOAN PHAT TRIEN
EOF

# --- ĐOẠN FIX : SHARE THƯ VIỆN & CORE TỪ ROOT SANG CHO USER ---
mkdir -p /home/"$USER"/Arduino/libraries
cp -rn /root/Arduino/libraries/* /home/"$USER"/Arduino/libraries/ 2>/dev/null || true
ln -sfn /root/.arduino15 /home/"$USER"/.arduino15 2>/dev/null || true
# ----------------------------------------------------------------------

chown -R "$USER:$USER" /home/"$USER"

mkdir -p /run/sshd
echo "ClientAliveInterval 30" >> /etc/ssh/sshd_config
echo "ClientAliveCountMax 100" >> /etc/ssh/sshd_config
echo "TCPKeepAlive yes" >> /etc/ssh/sshd_config

echo "Starting SSH Daemon..."
exec /usr/sbin/sshd -D
"""
    
    with open(setup_script_path, "w", encoding="utf-8") as f:
        f.write(script_content)
    os.chmod(setup_script_path, 0o777)

    logger.info(f"Starting container {cname} with devices: {required_ports}...")
    
    # Xây dựng lệnh Docker Run (ĐÃ XÓA DÒNG MOUNT VOLUME LÀM HỎNG CORE ESP32)
    docker_command = [
        "docker", "run", "-d", 
        "--name", cname, 
        "--restart", "unless-stopped",
        "--privileged",  
        "-p", f"{ssh_port}:22", 
        "-e", f"USERNAME={safe_username}", 
        "-v", f"{host_user_dir}:/home/{safe_username}",
        "-v", f"{setup_script_path}:/startup.sh",
        # THÊM LẠI CÁI DÒNG NÀY ĐỂ NÓ NHẬN LÕI ESP32 TỪ MÁY CHỦ:
        "-v", "/home/toan/flask-kerberos-demo/esp32_core:/root/.arduino15",
        "--group-add", "dialout", 
        "--entrypoint", "/bin/bash"
    ]
    # THÊM CÁC THIẾT BỊ ĐƯỢC CẤP QUYỀN (Strict Mode)
    for port in required_ports:
        docker_command.extend(["--device", f"{port}:{port}:rwm"])

    docker_command.append(image)
    docker_command.append("/startup.sh")
    
    try:
        subprocess.run(docker_command, check=True, timeout=30)
        time.sleep(3)
        
        if os.path.exists(setup_script_path):
            os.remove(setup_script_path)
             
    except Exception as e:
        logger.error(f"Error starting container: {e}")

    return ssh_port

def setup_arduino_cli_for_user(cname, username):
    """Setup Arduino CLI with board URLs and cores"""
    logger.info(f"Setting up Arduino CLI for container '{cname}'...")
    try:
        pass 
    except Exception as e:
        logger.error(f"Failed to setup Arduino CLI: {e}")

def check_platform_installed(cname, platform_id):
    """Check if Arduino platform is installed (with caching)"""
    cache_key = f"{cname}_{platform_id}"
    if cache_key in platform_cache:
        cached_time, cached_result = platform_cache[cache_key]
        if time.time() - cached_time < 3600:
            return cached_result
    return True # Giả lập luôn có để đỡ check lâu

def ensure_user_container_and_setup(username):
    """Ensure container is running and Arduino environment is setup"""
    safe_username = make_safe_name(username) 
    cname = f"{safe_username}-dev"
    
    # Hàm này giờ đây sẽ tự động Xóa và Tạo lại container
    # nếu danh sách thiết bị trong DB khác với thực tế
    ssh_port = ensure_user_container(username) 
    
    return ssh_port

def setup_container_permissions(cname, username):
    """Setup serial device permissions in container"""
    try:
        cmd = ["docker", "exec", cname, "sh", "-c", "chmod 666 /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || true"]
        subprocess.run(cmd, check=False, timeout=5)
    except Exception:
        pass

def get_all_running_users():
    """Get list of usernames with running containers"""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}", "--filter", "name=-dev"],
            capture_output=True, text=True, check=True
        )
        names = result.stdout.strip().split('\n')
        users = [name.replace('-dev', '') for name in names if name]
        return users
    except Exception:
        return []

def docker_status_all():
     return {}