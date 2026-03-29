#  Báo Cáo Hệ Thống - IoT Lab Management System

**Ngày cập nhật:** 29/03/2026  
**Dự án:** `flask-kerberos-demo` — EPU IoT Lab Platform  
**Stack:** Flask + Flask-SocketIO + MySQL + Docker (SSH Containers)

---

##  Kiến Trúc Tổng Quan

```
┌─────────────────────────────────────────────────────────┐
│  Browser (Admin / User)                                  │
│  ├── Admin Dashboard  → Quản lý User, Thiết bị, Mission │
│  └── User IDE         → Code space + Serial Monitor      │
└───────────────────┬─────────────────────────────────────┘
                    │ HTTPS (Ngrok tunnel)
┌───────────────────▼─────────────────────────────────────┐
│  Flask App (app.py)                                      │
│  ├── routes/auth.py       — Xác thực (Kerberos + session)│
│  ├── routes/admin.py      — Admin APIs                   │
│  ├── routes/user.py       — User APIs + Code workspace   │
│  ├── routes/hardware.py   — USB device management        │
│  ├── sockets.py           — SocketIO event handlers      │
│  └── services/            — AI grader, background tasks  │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│  MySQL Database                                          │
│  ├── users              — Tài khoản + roles              │
│  ├── missions           — Bài thi / bài tập              │
│  ├── mission_assignments — Giao bài cho user             │
│  ├── submissions        — File nộp + điểm AI             │
│  └── ai_training_dataset — Dữ liệu huấn luyện AI        │
└─────────────────────────────────────────────────────────┘
                    │ SSH + SFTP
┌───────────────────▼─────────────────────────────────────┐
│  Docker Containers (mỗi user 1 container)                │
│  └── Arduino CLI + FreeRTOS build environment            │
└─────────────────────────────────────────────────────────┘
```

---

##  Danh Sách Tính Năng Đã Nâng Cấp

###  1. Ổn Định Session — Không Văng Khi Code Reload

| | |
|---|---|
| **Vấn đề** | Server reload → sinh `SECRET_KEY` mới → session hết hạn → user bị đăng xuất |
| **Giải pháp** | Load `.env` bằng đường dẫn tuyệt đối trong `app.py`, giữ `SECRET_KEY` cố định |
| **File** | `app.py` |

---

###  2. Admin Dashboard - Quản Lý Mission (CRUD)

| Tính năng | Chi tiết |
|---|---|
| Tạo bài thi | Form nhập tên, loại (Assignment/Exam/Test), thời gian, mô tả Markdown, chọn sinh viên |
| **Tên tự động** | Cho phép ký tự đặc biệt (dấu câu, hai chấm) trong tên bài |
| **Thời gian tự tính** | Chọn Bắt đầu + nhập Số phút → End Time tự động cộng, readonly |
| Chỉnh sửa | Nút 📝 Edit điền lại form để cập nhật |
| Xoá | Nút 🗑️ Trash xóa bài + toàn bộ dữ liệu nộp bài liên quan |
| **Phân loại bảng** | Bài được nhóm: 🟢 Đang diễn ra / ⏰ Sắp tới / ✅ Đã kết thúc |
| **Tiến độ nộp bài** | Cột mới hiển thị `X/Y (%)` số sinh viên đã nộp |
| **Row mờ** | Bài có 100% nộp rồi sẽ mờ đi để dễ phân biệt |
| Xuất điểm | Nút 📊 Export xuất file Excel điểm bài thi |

---

###  3. Real-Time Notification cho Sinh Viên

| | |
|---|---|
| **Cơ chế** | Flask-SocketIO emit event `new_mission` khi Admin giao bài |
| **Phía user** | Bắt event → hiện Toast popup ngay lập tức |
| **IDE** | Sau notification tự trigger kiểm tra bài thi đang active |

---

###  4. Giao Diện Sinh Viên - Bài Thi / Bài Tập

| Tính năng | Chi tiết |
|---|---|
| **Phân nhóm** | 🟢 Đang diễn ra / ⏰ Sắp tới / ✅ Đã kết thúc + Đã nộp |
| Countdown timer | Đồng hồ đếm ngược trong card + banner top của trang |
| **Vào làm bài** | Mở IDE trong tab mới (`target=_blank`) — không mất trang bài thi |
| Đồng hồ IDE | Timer hiển thị trên thanh menu IDE khi đang thi |
| **Preview file** | Modal nộp bài liệt kê file `.ino/.cpp/.c/.h/.py` sẽ được nộp kèm dung lượng |
| Auto-submit | Hết giờ → hệ thống tự snapshot toàn bộ file và nộp |
| **Nộp bài** | 1-click → AI chấm điểm ngay sau đó |
| **Auto-poll điểm** | Sau nộp, tự poll API mỗi 8 giây → Toast khi AI chấm xong, không cần F5 |
| Font chữ | Đổi từ Syne → **Inter** cho dễ đọc hơn |
| Thông tin user | Tên sinh viên hiển thị góc phải navbar |

---

###  5. AI Grader — Chấm Điểm Tự Động

| | |
|---|---|
| **Primary** | Google Gemini 2.5 Flash |
| **Fallback** | Anthropic Claude 3.5 Sonnet (tự động nếu Gemini lỗi/hết quota) |
| **Output** | Điểm 0–10, nhận xét chi tiết, 5 tiêu chí đánh giá |
| **Dataset** | Lưu vào `data/ai_training_dataset.jsonl` để sau xây model tự train |

---

###  6. Quản Lý Phần Cứng (Hardware)

| | |
|---|---|
| Tự động theo dõi | `udev_listener` bắt sự kiện cắm/rút USB |
| **Rescan thủ công** | Nút "Quét lại USB & Đồng bộ" trên trang Admin Thiết bị — không cần restart server |
| Compile + Upload | Sinh viên compile sketch → Upload thẳng lên board qua IDE |

---

###  7. Bug Fixes Quan Trọng

| Bug | Nguyên nhân | Fix |
|---|---|---|
| API `/user/api/my-missions` báo 500 | Thiếu import `get_db_connection` | Thêm import |
| Submit bài báo lỗi 415 | `request.json` yêu cầu Content-Type header | Dùng `request.get_json(silent=True)` |
| Nút Giao bài không sáng | JS validate chạy sai thứ tự | Đảo lại: cập nhật `state.validation` trước, render sau |
| Alert popup trình duyệt | `alert()` bị gọi khi thiếu toast container | Thay bằng toast tùy chỉnh tạo động |
| Cây thư mục IDE hiện file hệ thống | Thiếu filter `.arduino`, `libraries`, `Arduino` | Thêm blacklist vào API cây file |
| FQBN nhận nhầm thành path | Truyền tham số ngược trong `compile_sketch()` | Đổi lại thứ tự tham số |

---

##  Cấu Trúc File Quan Trọng

```
flask-kerberos-demo/
├── app.py                          # Flask entry point + SocketIO
├── config/
│   ├── settings.py                 # Board config (FQBN, etc.)
│   └── database.py                 # DB connection pool
├── routes/
│   ├── admin.py                    # Admin CRUD APIs
│   ├── user.py                     # User workspace APIs + Submit + Preview
│   ├── hardware.py                 # USB & Arduino APIs
│   └── auth.py                     # Kerberos auth
├── services/
│   ├── ai_grader.py                # Gemini + Claude AI grading
│   └── background_services.py     # Timer tasks
├── templates/
│   ├── layout.html                 # Base layout + user identity
│   ├── user.html                   # IDE workspace
│   ├── user_missions.html          # Student mission list
│   └── admin/
│       └── missions.html           # Admin mission management
├── data/
│   └── ai_training_dataset.jsonl   # Training data cho AI
└── docs/
    └── SYSTEM_REPORT.md            # File này
```

---


*Generated: 2026-03-29 — EPU IoT Lab Platform*
