# HƯỚNG DẪN SỬA LỖI: USER KHÔNG THẤY ESP32 ĐỂ NẠP CODE

## VẤN ĐỀ
Khi cắm ESP32 vào:
- ✅ Host phát hiện được thiết bị (`/dev/ttyUSB0`)
- ✅ Admin đã cấp quyền cho user trong database
- ❌ User vẫn KHÔNG thấy cổng để nạp code

## NGUYÊN NHÂN
Từ log, phát hiện 2 vấn đề:

### 1. USB Watcher không hoạt động đúng:
```
❌ Truncate failed: [Errno 13] Permission denied: '/tmp/usb_event_trigger'
❌ Sudo remove failed: Command '['sudo', 'rm', '-f', '/tmp/usb_event_trigger']' timed out after 2 seconds
```
→ **USB Watcher không thể xóa trigger file** 
→ Không gọi được API `/api/hardware/rescan`
→ Container không được restart
→ Thiết bị mới không được nhận diện

### 2. Container cần restart để nhận thiết bị mới:
Khi thiết bị USB được cắm vào SAU KHI container đã chạy, container cần:
- Restart để bind lại `/dev`
- Hoặc exec lệnh để re-scan devices

## CÁCH SỬA (3 BƯỚC)

### BƯỚC 1: SỬA USB WATCHER PERMISSIONS

#### Cách 1: Chạy watcher với sudo (Khuyến nghị)
```bash
# Dừng service hiện tại
sudo systemctl stop usb-watcher

# Sửa file service
sudo nano /etc/systemd/system/usb-watcher.service
```

Thay đổi:
```ini
[Service]
Type=simple
User=root          # ← ĐỔI TỪ toan THÀNH root
WorkingDirectory=/home/toan/flask-kerberos-demo/scripts
ExecStart=/usr/bin/python3 /home/toan/flask-kerberos-demo/scripts/watcher.py
Restart=always
RestartSec=5
```

Reload và restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart usb-watcher
sudo systemctl status usb-watcher
```

#### Cách 2: Cho user quyền sudo không cần password (Nếu không muốn chạy với root)
```bash
# Thêm vào sudoers
echo "toan ALL=(ALL) NOPASSWD: /bin/rm -f /tmp/usb_event_trigger" | sudo tee /etc/sudoers.d/usb-watcher
sudo chmod 440 /etc/sudoers.d/usb-watcher
```

### BƯỚC 2: SỬA DOCKER_MANAGER.PY ĐỂ TỰ ĐỘNG RESTART CONTAINER

Thêm logic restart container khi phát hiện thiết bị mới:

```python
# File: services/docker_manager.py

def restart_container_for_device_scan(username):
    """Restart container to recognize new USB devices"""
    safe_username = make_safe_name(username)
    cname = f"{safe_username}-dev"
    
    try:
        # Check if container is running
        status = docker_status(cname)
        if status == 'running':
            logger.info(f"Restarting container {cname} to recognize new devices...")
            subprocess.run(["docker", "restart", cname], check=True, timeout=30)
            time.sleep(5)  # Wait for container to fully start
            
            # Re-setup permissions
            setup_container_permissions(cname, safe_username)
            logger.info(f"Container {cname} restarted successfully")
            return True
    except Exception as e:
        logger.error(f"Failed to restart container {cname}: {e}")
        return False
    
    return False
```

Sau đó sửa file `routes/hardware.py`:

```python
# File: routes/hardware.py
# Trong hàm hardware_rescan_api(), sau phần cập nhật database:

# PART 2: RESTART CONTAINERS TO RECOGNIZE NEW DEVICES
try:
    running_users = get_all_running_users()
    if running_users:
        current_app.logger.info(f"Restarting containers for users: {', '.join(running_users)}")
        for username in running_users:
            # THÊM DÒNG NÀY:
            from services.docker_manager import restart_container_for_device_scan
            restart_container_for_device_scan(username)
            # Hoặc nếu không muốn restart:
            # ensure_user_container_and_setup(username)
```

### BƯỚC 3: KIỂM TRA VÀ VERIFY

#### Test 1: Kiểm tra USB Watcher
```bash
# Xem log watcher
sudo journalctl -u usb-watcher -f

# Test bằng cách tạo trigger file
sudo touch /tmp/usb_event_trigger
# Watcher phải tự động xóa file này và gọi API
```

#### Test 2: Kiểm tra container nhận được thiết bị
```bash
# Xem thiết bị trên host
ls -la /dev/ttyUSB* /dev/ttyACM*

# Xem thiết bị trong container (thay USER bằng username thực)
docker exec USER-dev ls -la /dev/ttyUSB* /dev/ttyACM*
docker exec USER-dev arduino-cli board list

# Kiểm tra quyền
docker exec USER-dev groups USER
# Phải có: USER dialout
```

#### Test 3: Từ giao diện web
1. Login vào workspace
2. Click nút "Scan Serial Ports"
3. Phải thấy danh sách cổng và board tương ứng

## GIẢI PHÁP NHANH (TẠM THỜI)

Nếu cần fix ngay mà chưa restart được service:

```bash
# Chạy manual rescan
curl -X POST http://localhost:5000/api/hardware/rescan

# Hoặc restart container của user cụ thể
docker restart USER-dev  # Thay USER bằng username

# Sau đó fix permissions trong container
docker exec --user root USER-dev chmod 666 /dev/ttyUSB* /dev/ttyACM*
docker exec --user root USER-dev usermod -a -G dialout USER
```

## KIỂM TRA CÁC VẤN ĐỀ KHÁC

### Nếu vẫn không hoạt động, check:

1. **Database permissions:**
```sql
-- Kiểm tra user có quyền với thiết bị không
SELECT u.username, hd.tag_name, hd.port, da.assigned_at 
FROM device_assignments da
JOIN users u ON da.user_id = u.id
JOIN hardware_devices hd ON da.device_id = hd.id
WHERE u.username = 'USERNAME';
```

2. **Container có mount /dev không:**
```bash
docker inspect USER-dev | grep -A 5 "Mounts"
# Phải thấy: "/dev:/dev"
```

3. **Udev rules:**
```bash
# Kiểm tra udev rules
cat /etc/udev/rules.d/99-usb-serial.rules
# Nên có: SUBSYSTEM=="tty", MODE="0666"
```

4. **Check flask app logs:**
```bash
tail -f /home/toan/flask-kerberos-demo/logs/app.log
```

## TÓM TẮT

**Root cause:** USB Watcher không có quyền xóa trigger file → không gọi rescan API → container không nhận thiết bị mới

**Giải pháp tốt nhất:**
1. Chạy USB Watcher service với quyền root
2. Tự động restart container khi có thiết bị mới
3. Verify permissions trong container

**Sau khi sửa:**
- Cắm ESP32 → USB Watcher phát hiện → Gọi API rescan → Container restart → User thấy cổng → Có thể nạp code ✅
