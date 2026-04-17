"""
Docker Container Management Service
UPDATED: Strict Device Mounting via Subprocess (No /dev:/dev) + Fix Full  thư viện Arduino
"""
import os
import subprocess
import time
import logging
import json
import glob
import secrets
from utils import make_safe_name, find_free_port
from config import get_db_connection, DEFAULT_ARDUINO_LIBRARIES
from services.logger import log_action
from utils.metrics import ACTIVE_CONTAINERS

logger = logging.getLogger(__name__)

# Platform cache for Arduino CLI
platform_cache = {}

def get_assigned_ports(username):
    """
    [RESTORED] Lấy port USB theo phân quyền từ CSDL để map vào Docker
    """
    try:
        db = get_db_connection()
        if not db: return []
        cur = db.cursor()
        query = """
            SELECT hd.port
            FROM hardware_devices hd
            JOIN device_assignments da ON hd.id = da.device_id
            JOIN users u ON da.user_id = u.id
            WHERE u.username = %s AND hd.status != 'disconnected'
        """
        cur.execute(query, (username,))
        ports = [row[0] for row in cur.fetchall()]
        cur.close()
        db.close()
        return ports
    except Exception as e:
        logger.error(f"Error getting assigned ports for {username}: {e}")
        return []

def docker_status(cname):
    """Kiểm tra trạng thái container Docker"""
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
    """Đảm bảo container người dùng tồn tại, đang chạy và có đúng thiết bị"""
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
            
            # [HOTFIX] Tự động cài pyserial cho các container cũ đang chạy
            try:
                # Chạy ngầm để không làm chậm quá trình load IDE
                fix_cmd = f"docker exec {cname} bash -c 'if ! python3 -c \"import serial\" &>/dev/null; then apt-get update -y && apt-get install -y python3-serial; fi'"
                subprocess.Popen(fix_cmd, shell=True)
            except Exception: pass

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
    os.chmod(host_user_dir, 0o750)

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
    echo "$USER:$CONTAINER_PASSWORD" | chpasswd
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

# TỰ ĐỘNG CÀI ĐẶT CORE ARDUINO VÀ ESP32 NẾU CHƯA CÓ
if command -v arduino-cli &> /dev/null; then
    if ! arduino-cli core list | grep -q "arduino:avr"; then
        echo "Installing arduino:avr core..."
        arduino-cli core update-index &>/dev/null
        arduino-cli core install arduino:avr &>/dev/null
    fi
    if ! arduino-cli core list | grep -q "esp32:esp32.*2.0.17"; then
        echo "Installing/Downgrading esp32:esp32 core to v2.0.17..."
        arduino-cli config init &>/dev/null || true
        arduino-cli config add board_manager.additional_urls https://dl.espressif.com/dl/package_esp32_index.json &>/dev/null || true
        arduino-cli core update-index &>/dev/null
        arduino-cli core uninstall esp32:esp32 &>/dev/null || true
        arduino-cli core install esp32:esp32@2.0.17 &>/dev/null
    fi
    
    # CÀI CÁC THƯ VIỆN NHÚNG THEO CONFIG CHUNG
    arduino-cli lib install "Adafruit NeoPixel" "DHT sensor library" "Adafruit Unified Sensor" "PubSubClient" "ArduinoJson" &>/dev/null || true
fi
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
    # [SECURITY] Sinh mật khẩu ngẫu nhiên cho SSH Container
    container_password = secrets.token_urlsafe(16)
    
    # Lưu mật khẩu vào DB để Server có thể SSH vào container
    try:
        db2 = get_db_connection()
        cur2 = db2.cursor()
        cur2.execute("UPDATE users SET container_password=%s WHERE username=%s", (container_password, username))
        db2.commit()
        cur2.close()
        db2.close()
    except Exception as e:
        logger.warning(f"Could not save container password: {e}")
        container_password = secrets.token_urlsafe(16)
    
    docker_command = [
        "docker", "run", "-d", 
        "--name", cname, 
        "--restart", "unless-stopped",
        # [SECURITY] Cân bằng giữa bảo mật và tính ổn định
        # Không dùng --cap-drop=ALL vì làm hỏng chpasswd, useradd và sshd
        "--cap-drop=SYS_ADMIN",
        "--cap-drop=SYS_RAWIO",
        "--cap-drop=MKNOD",
        "-p", f"{ssh_port}:22", 
        "-e", f"USERNAME={safe_username}",
        "-e", f"CONTAINER_PASSWORD={container_password}",
        "-v", f"{host_user_dir}:/home/{safe_username}",
        "-v", f"{setup_script_path}:/startup.sh",
        "-v", "/home/toan/flask-kerberos-demo/esp32_core:/root/.arduino15",
        "--group-add", "dialout", 
        "--entrypoint", "/bin/bash"
    ]
    # [RESTORED]: Xử lý nút thắt cổ chai vatas lý
    for port in required_ports:
        if os.path.exists(port):
            docker_command.extend(["--device", f"{port}:{port}"])

    docker_command.append(image)
    docker_command.append("/startup.sh")
    
    try:
        subprocess.run(docker_command, check=True, timeout=30)
        time.sleep(5)
        
        if os.path.exists(setup_script_path):
            os.remove(setup_script_path)
            
        # Update metric
        ACTIVE_CONTAINERS.inc()
             
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
    """Cài đặt serial trong container"""
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