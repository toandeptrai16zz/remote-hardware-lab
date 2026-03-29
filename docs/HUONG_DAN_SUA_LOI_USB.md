# HƯỚNG DẪN KHẮC PHỤC: USER KHÔNG NHÌN THẤY ESP32 ĐỂ NẠP CODE

## 📋 MÔ TẢ VẤN ĐỀ

**Triệu chứng:**
- ✅ Cắm ESP32 vào máy chủ → Phát hiện được thiết bị `/dev/ttyUSB0`
- ✅ Admin đã cấp quyền thiết bị cho user trong hệ thống
- ❌ User vào workspace → KHÔNG thấy cổng COM để nạp code
- ❌ Nút "Scan Serial Ports" không trả về thiết bị nào

## 🔍 NGUYÊN NHÂN (Từ Phân Tích Log)

### Lỗi chính phát hiện trong log:
```
2026-01-31 13:45:07 - USBWatcher - ERROR - ❌ Truncate failed: [Errno 13] Permission denied: '/tmp/usb_event_trigger'
[sudo] password for toan: 2026-01-31 13:45:09 - USBWatcher - ERROR - ❌ Sudo remove failed: Command '['sudo', 'rm', '-f', '/tmp/usb_event_trigger']' timed out after 2 seconds
```

### Chuỗi sự kiện dẫn đến lỗi:

1. **Khi cắm ESP32:**
   ```
   Udev rule phát hiện USB → Tạo file /tmp/usb_event_trigger
   ```

2. **USB Watcher Service (chạy với user 'toan'):**
   ```
   Phát hiện trigger file → Gọi API /api/hardware/rescan → Cố xóa trigger file
   → FAILED: Permission denied (vì user 'toan' không có quyền sudo)
   → Timeout chờ password sudo
   → Trigger file không bị xóa
   → Watcher bị stuck, không thể xử lý event tiếp theo
   ```

3. **Container của User:**
   ```
   Không nhận được tín hiệu rescan
   → Không restart/refresh device list
   → /dev/ttyUSB0 có trong host nhưng container không nhận ra
   → arduino-cli board list trả về rỗng
   → User không thấy cổng để nạp code
   ```

## ✅ GIẢI PHÁP TOÀN DIỆN

### 🛠️ **PHƯƠNG ÁN 1: SỬA NGAY (KHUYẾN NGHỊ)**

#### Bước 1: Chạy USB Watcher với quyền root

```bash
# Dừng service hiện tại
sudo systemctl stop usb-watcher

# Sửa file service
sudo nano /etc/systemd/system/usb-watcher.service
```

**Thay đổi dòng User:**
```ini
[Service]
Type=simple
User=root          # ← ĐỔI TỪ "toan" THÀNH "root"
WorkingDirectory=/home/toan/flask-kerberos-demo/scripts
ExecStart=/usr/bin/python3 /home/toan/flask-kerberos-demo/scripts/watcher.py
Restart=always
RestartSec=5
```

**Reload và khởi động lại:**
```bash
sudo systemctl daemon-reload
sudo systemctl restart usb-watcher
sudo systemctl status usb-watcher
```

#### Bước 2: Fix quyền cho /tmp/usb_event_trigger

```bash
# Xóa trigger file cũ (nếu có)
sudo rm -f /tmp/usb_event_trigger

# Đảm bảo /tmp có quyền đúng
sudo chmod 1777 /tmp
```

#### Bước 3: Kiểm tra hoạt động

```bash
# Test 1: Xem log real-time
sudo journalctl -u usb-watcher -f

# Test 2: Tạo trigger file thử
sudo touch /tmp/usb_event_trigger

# Nếu watcher hoạt động đúng:
# - File sẽ tự động bị xóa sau 1-2 giây
# - Log sẽ hiện: "🔔 USB event detected!"
# - API rescan được gọi: "✅ API success: Rescan and container sync complete"
```

#### Bước 4: Test với ESP32 thật

```bash
# Cắm ESP32 vào USB
# Đợi 2-3 giây

# Kiểm tra log
sudo journalctl -u usb-watcher -n 20

# Kỳ vọng thấy:
# - "🔔 USB event detected!"
# - "✅ API success: Rescan and container sync complete"

# Kiểm tra trong container của user (thay USERNAME bằng tên user thực)
docker exec USERNAME-dev ls -la /dev/ttyUSB* /dev/ttyACM*
docker exec USERNAME-dev arduino-cli board list
```

---

### 🛠️ **PHƯƠNG ÁN 2: NÂNG CAO (Nếu không muốn chạy watcher với root)**

#### Cấu hình sudo không cần password cho watcher

```bash
# Tạo file sudoers riêng
sudo nano /etc/sudoers.d/usb-watcher
```

**Thêm nội dung:**
```
toan ALL=(ALL) NOPASSWD: /bin/rm -f /tmp/usb_event_trigger
toan ALL=(ALL) NOPASSWD: /usr/bin/docker exec * chmod *
toan ALL=(ALL) NOPASSWD: /usr/bin/docker restart *
```

**Set quyền:**
```bash
sudo chmod 440 /etc/sudoers.d/usb-watcher

# Kiểm tra syntax
sudo visudo -c
```

**Restart watcher:**
```bash
sudo systemctl restart usb-watcher
```

---

### 🛠️ **PHƯƠNG ÁN 3: SỬA CODE (Tối ưu dài hạn)**

#### Cập nhật `scripts/watcher.py` để tự động retry:

```python
def _safe_remove_trigger(self):
    """Safely remove trigger file with multiple fallback methods"""
    try:
        # Method 1: Standard remove
        if self.trigger_file.exists():
            self.trigger_file.unlink()
            self.logger.info("✅ Trigger file removed successfully")
            return True
    except PermissionError:
        self.logger.warning("⚠️ Permission denied, trying alternative methods...")
        
        # Method 2: Use sudo with NOPASSWD (if configured)
        try:
            import subprocess
            result = subprocess.run(
                ['sudo', '-n', 'rm', '-f', str(self.trigger_file)], 
                check=True, 
                timeout=2, 
                capture_output=True
            )
            self.logger.info("✅ Trigger file removed with sudo")
            return True
        except subprocess.CalledProcessError:
            self.logger.error("❌ Sudo failed - check sudoers config")
        except subprocess.TimeoutExpired:
            self.logger.error("❌ Sudo timeout - requires password?")
        except FileNotFoundError:
            self.logger.error("❌ sudo command not found")
    
    # Method 3: Fallback - rename instead of delete
    try:
        renamed = self.trigger_file.with_suffix('.processed')
        self.trigger_file.rename(renamed)
        self.logger.warning("⚠️ Renamed trigger file instead of deleting")
        return True
    except Exception as e:
        self.logger.error(f"❌ All methods failed: {e}")
    
    return False
```

---

## 🔧 KIỂM TRA VÀ DEBUG

### 1. Kiểm tra USB Watcher hoạt động

```bash
# Xem status
sudo systemctl status usb-watcher

# Xem log gần đây
sudo journalctl -u usb-watcher -n 50 --no-pager

# Xem log real-time
sudo journalctl -u usb-watcher -f
```

**Dấu hiệu hoạt động tốt:**
```
✅ USB Watcher started. Monitoring: /tmp/usb_event_trigger
✅ 🔔 USB event detected!
✅ ✅ API success: Rescan and container sync complete
✅ ✅ Trigger file removed successfully
```

**Dấu hiệu có vấn đề:**
```
❌ Permission denied
❌ Sudo remove failed
❌ Timeout
```

### 2. Kiểm tra thiết bị trong container

```bash
# Thay USERNAME bằng username thực của user
USERNAME="huhu"  # Ví dụ

# Xem container có chạy không
docker ps | grep ${USERNAME}-dev

# Xem thiết bị trong container
docker exec ${USERNAME}-dev ls -la /dev/tty* | grep -E "USB|ACM"

# Xem arduino-cli nhận ra không
docker exec ${USERNAME}-dev arduino-cli board list

# Xem user có trong nhóm dialout không
docker exec ${USERNAME}-dev groups ${USERNAME}
```

### 3. Kiểm tra permissions

```bash
# Trong container
docker exec ${USERNAME}-dev ls -la /dev/ttyUSB0
# Kỳ vọng: crw-rw-rw- hoặc crw-rw----

# Nếu không có quyền, fix bằng:
docker exec --user root ${USERNAME}-dev chmod 666 /dev/ttyUSB* /dev/ttyACM*
docker exec --user root ${USERNAME}-dev usermod -a -G dialout ${USERNAME}

# Sau đó restart container
docker restart ${USERNAME}-dev
```

### 4. Test manual rescan API

```bash
# Gọi API rescan thủ công
curl -X POST http://localhost:5000/api/hardware/rescan

# Xem response
# Nếu thành công: {"success": true, "message": "Rescan and container sync complete."}
```

---

## 🚑 GIẢI PHÁP KHẨN CẤP (Fix tạm khi đang có user đang chờ)

Nếu cần fix ngay mà chưa có thời gian restart service:

```bash
# Bước 1: Manual rescan
curl -X POST http://localhost:5000/api/hardware/rescan

# Bước 2: Restart container của user cụ thể
USERNAME="huhu"  # Thay bằng username thực
docker restart ${USERNAME}-dev

# Bước 3: Fix permissions trong container
docker exec --user root ${USERNAME}-dev sh -c "chmod 666 /dev/ttyUSB* /dev/ttyACM* 2>/dev/null; usermod -a -G dialout ${USERNAME}"

# Bước 4: Yêu cầu user click "Scan Serial Ports" lại trong giao diện web
```

---

## 📊 CHECKLIST SAU KHI SỬA

- [ ] USB Watcher service đang chạy: `sudo systemctl status usb-watcher`
- [ ] USB Watcher có quyền xóa trigger file (test bằng `sudo touch /tmp/usb_event_trigger`)
- [ ] Cắm ESP32 vào → Log hiện "USB event detected"
- [ ] Container của user restart tự động hoặc nhận được thiết bị
- [ ] Trong container: `ls /dev/ttyUSB*` hiện thiết bị
- [ ] Trong container: `arduino-cli board list` hiện board
- [ ] User vào web interface → Click "Scan Serial Ports" → Thấy cổng COM
- [ ] User có thể compile và upload code thành công

---

## 📞 TÌM HIỂU THÊM

### Kiến trúc hoạt động của hệ thống:

```
[USB Device Plugged] 
    ↓
[Udev Rules: /etc/udev/rules.d/99-usb-event.rules]
    ↓
[Tạo file: /tmp/usb_event_trigger]
    ↓
[USB Watcher Service: scripts/watcher.py]
    ↓
[Gọi API: POST /api/hardware/rescan]
    ↓
[Hardware Route: routes/hardware.py]
    ↓ 
[Update Database + Restart Containers]
    ↓
[Container nhận device: /dev bind mount]
    ↓
[Arduino CLI scan: arduino-cli board list]
    ↓
[User Interface: GET /user/<username>/serial-ports]
```

### Log files quan trọng:

```bash
# Application logs
tail -f /home/toan/flask-kerberos-demo/logs/app.log

# USB Watcher logs
sudo journalctl -u usb-watcher -f

# Docker logs
docker logs USERNAME-dev --tail 50 -f

# System logs
sudo dmesg | tail -20
```

---

## ✨ KẾT LUẬN

**Nguyên nhân chính:** USB Watcher không có quyền xóa trigger file → không gọi được API rescan → container không nhận thiết bị mới

**Giải pháp tốt nhất:** Chạy USB Watcher service với quyền root

**Sau khi fix:**
```
Cắm ESP32 
→ USB Watcher phát hiện 
→ Gọi API rescan 
→ Container restart/refresh 
→ User thấy cổng COM 
→ Upload code thành công ✅
```
