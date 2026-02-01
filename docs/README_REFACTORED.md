# Flask Kerberos Demo - Refactored Structure

## 📁 Cấu trúc thư mục mới

```
flask-kerberos-demo/
│
├── app.py                          # Main application (60 dòng - đã giảm từ 3000+ dòng)
├── app_old_backup.py               # Backup của file cũ
│
├── config/                         # Cấu hình
│   ├── __init__.py
│   ├── settings.py                 # Các hằng số cấu hình
│   └── database.py                 # Database connection & initialization
│
├── models/                         # Models (chưa sử dụng - dành cho tương lai)
│   └── __init__.py
│
├── routes/                         # Các routes chính
│   ├── __init__.py
│   ├── auth.py                     # Authentication (login, register, OTP)
│   ├── admin.py                    # Admin dashboard & management
│   ├── user.py                     # User workspace & IDE
│   └── hardware.py                 # Hardware device management
│
├── services/                       # Business logic
│   ├── __init__.py
│   ├── security.py                 # CSRF, OTP, Password validation
│   ├── logger.py                   # Logging service
│   ├── docker_manager.py           # Docker container operations
│   ├── ssh_manager.py              # SSH connection management
│   └── arduino.py                  # Arduino compile & upload
│
├── utils/                          # Utility functions
│   ├── __init__.py
│   ├── helpers.py                  # Helper functions
│   └── decorators.py               # Route decorators (@require_auth...)
│
├── sockets/                        # Socket.IO handlers
│   ├── __init__.py
│   ├── terminal.py                 # Terminal WebSocket
│   └── serial_monitor.py           # Serial monitor & upload status
│
├── static/                         # Static files (CSS, JS, images)
├── templates/                      # HTML templates
└── venv/                           # Virtual environment

```

## 🎯 Các cải tiến chính

### 1. **Tách biệt logic rõ ràng**
- **Config**: Cấu hình tập trung
- **Routes**: Xử lý HTTP requests
- **Services**: Business logic
- **Utils**: Các hàm tiện ích
- **Sockets**: WebSocket handlers

### 2. **File app.py gọn gàng (60 dòng thay vì 3000+)**
```python
# Trước: 3000+ dòng code lộn xộn
# Sau: 60 dòng, chỉ import và khởi tạo
```

### 3. **Dễ bảo trì & mở rộng**
- Mỗi module có trách nhiệm riêng
- Dễ tìm và sửa lỗi
- Thêm tính năng mới không ảnh hưởng code cũ

### 4. **Import sạch sẽ**
```python
# Thay vì import lung tung ở đầu file
from services import log_action, compile_sketch
from utils import require_auth, make_safe_name
```

## 🚀 Cách chạy

### Chạy như bình thường:
```bash
python app.py
```

### Nếu có lỗi import:
```bash
# Đảm bảo bạn đang ở đúng thư mục
cd flask-kerberos-demo
python app.py
```

## 📝 Chi tiết các module

### **config/settings.py**
- `SECURITY_CONFIG`: Các thiết lập bảo mật
- `EMAIL_CONFIG`: Cấu hình email
- `DEVICE_ID_MAP`: Mapping thiết bị phần cứng
- `HIDDEN_SYSTEM_FILES`: Files cần ẩn khỏi user

### **services/docker_manager.py**
- `ensure_user_container()`: Tạo/khởi động container
- `setup_arduino_cli_for_user()`: Cài Arduino CLI
- `check_platform_installed()`: Kiểm tra board đã cài

### **services/arduino.py**
- `compile_sketch()`: Biên dịch code Arduino
- `perform_upload_worker()`: Nạp code lên board (background task)
- `get_serial_ports()`: Quét cổng serial

### **routes/auth.py**
- `/login`: Trang đăng nhập
- `/register`: Đăng ký tài khoản
- `/api/verify-otp`: Xác thực OTP

### **routes/user.py**
- `/user/<username>/workspace`: IDE chính
- `/user/<username>/files`: Quản lý files
- `/user/<username>/compile`: Biên dịch code
- `/user/<username>/upload`: Nạp code

### **routes/admin.py**
- `/admin`: Dashboard admin
- `/admin/manage`: Quản lý users
- `/admin/devices`: Quản lý thiết bị
- `/admin/assignments`: Phân quyền thiết bị

## ⚠️ Lưu ý quan trọng

1. **File cũ đã backup** tại `app_old_backup.py`
2. **Logic hoàn toàn giữ nguyên** - chỉ tái cấu trúc code
3. **Database không thay đổi** - vẫn dùng schema cũ
4. **Templates không đổi** - vẫn dùng HTML files cũ

## 🐛 Troubleshooting

### Lỗi import module:
```bash
ModuleNotFoundError: No module named 'config'
```
**Giải pháp**: Đảm bảo bạn chạy từ thư mục gốc `flask-kerberos-demo/`

### Lỗi routes không tìm thấy:
```bash
werkzeug.routing.BuildError: Could not build url for endpoint 'login_page'
```
**Giải pháp**: Routes giờ có namespace Blueprint, dùng `auth.login_page` thay vì `login_page`

### Container không khởi động:
- Kiểm tra Docker daemon đang chạy
- Xem logs trong `app.log`

## 📚 Tài liệu tham khảo

- Flask Blueprints: https://flask.palletsprojects.com/en/stable/blueprints/
- Flask-SocketIO: https://flask-socketio.readthedocs.io/
- Python Package Structure: https://docs.python.org/3/tutorial/modules.html

---
**Phiên bản**: 2.0 (Refactored)  
**Ngày cập nhật**: 30/01/2026  
**Tác giả**: EPU Tech Team
