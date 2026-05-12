# Remote Hardware Lab - Hệ Thống Thực Hành Nhúng AI-Native 🚀

Đây là nền tảng lập trình nhúng (PaaS) thế hệ mới, cho phép sinh viên thực hành lập trình Arduino, ESP32 và ESP8266 trực tiếp trên trình duyệt web. Khác biệt cốt lõi của nền tảng này là việc chuyển dịch sang mô hình **AI-Native Virtual Lab**, sử dụng Trí tuệ Nhân tạo để chấm điểm chuyên sâu và kiến trúc Microservices cô lập hoàn toàn môi trường thực hành của từng sinh viên.

---

## 💻 Công Nghệ Sử Dụng (Tech Stack)

Hệ thống được thiết kế theo chuẩn công nghiệp (Industry-Standard) với các công nghệ lõi mạnh mẽ:

| Phân hệ | Công nghệ nổi bật | Chức năng cốt lõi |
| :--- | :--- | :--- |
| **Backend** | ![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white) ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) | Xử lý Logic, RESTful API, Routing |
| **Frontend** | ![HTML5](https://img.shields.io/badge/html5-%23E34F26.svg?style=for-the-badge&logo=html5&logoColor=white) ![JavaScript](https://img.shields.io/badge/javascript-%23323330.svg?style=for-the-badge&logo=javascript&logoColor=%23F7DF1E) ![Bootstrap](https://img.shields.io/badge/bootstrap-%238511FA.svg?style=for-the-badge&logo=bootstrap&logoColor=white) | Cloud IDE, Giao diện tương tác người dùng |
| **Realtime** | ![Socket.io](https://img.shields.io/badge/Socket.io-black?style=for-the-badge&logo=socket.io&badgeColor=010101) | Giao tiếp 2 chiều độ trễ thấp (Terminal, Serial) |
| **Virtualization** | ![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white) | Cô lập môi trường (Sandboxing) cho từng sinh viên |
| **Hardware CLI** | ![Arduino](https://img.shields.io/badge/-Arduino-00979D?style=for-the-badge&logo=Arduino&logoColor=white) | Biên dịch & Nạp code (arduino-cli) |
| **Database** | ![MySQL](https://img.shields.io/badge/mysql-%2300f.svg?style=for-the-badge&logo=mysql&logoColor=white) | Lưu trữ thông tin tài khoản, kết quả đánh giá |
| **Testing & CI** | ![Pytest](https://img.shields.io/badge/pytest-%23ffffff.svg?style=for-the-badge&logo=pytest&logoColor=2f9fe3) ![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white) | Kiểm thử bảo mật (Deep Test), Auto-deploy |

---
## 🌟 Tính Năng Nổi Bật

### 1. Web-based Cloud IDE
- Soạn thảo code chuyên nghiệp không cần cài đặt phần mềm.
- Tích hợp Terminal & Serial Monitor ảo tương tác theo thời gian thực qua WebSockets (Socket.IO).
- Hỗ trợ đầy đủ các thư viện cơ bản (LCD, DHT, MQTT,...).

### 2. Kiến Trúc Cô Lập (Docker Sandboxing)
- **Zero-Interference:** Mỗi sinh viên được cấp phát một Docker Container riêng biệt đóng vai trò là một "máy tính ảo".
- **Garbage Collection:** Cơ chế tự động quét và dọn dẹp các Container không hoạt động quá 2 giờ để giải phóng tối đa tài nguyên RAM cho máy chủ.
- **File Lockdown:** Các file hệ thống cốt lõi (`.bashrc`, `WELCOME.txt`) được thiết lập quyền root vĩnh viễn, ngăn chặn sinh viên phá hoại môi trường.

### 3. Engine Chấm Điểm Đa Mô Hình AI (Multi-LLM Grader)
Hệ thống không đánh giá bằng test case tĩnh mà thông qua phân tích mã nguồn bằng AI (Evidence-based assessment):
- **Google Gemini 1.5 Pro / Flash:** Xử lý các bài toán logic phức tạp, kết nối IoT.
- **Anthropic Claude 3.5 Sonnet:** Engine dự phòng thông minh với độ chi tiết cao.
- **GROQ (LLaMA 3):** Engine siêu tốc trả về kết quả tức thì.
Hệ thống hỗ trợ tính năng Fallback tự động: Nếu một API bị quá tải (Rate Limit), nó sẽ lập tức chuyển sang API dự phòng để sinh viên không bao giờ bị gián đoạn.

### 4. Hệ Thống Bảo Mật & Chống Quá Tải
- **Rate Limiting:** Tích hợp bộ lọc IP & Username ngăn chặn hành vi spam click (Ví dụ: Giới hạn click biên dịch 10 giây/lần).
- **Anti-Path Traversal:** Đảm bảo sinh viên không thể truy cập chéo sang không gian mạng của người khác hoặc thư mục gốc của Server.
- CI/CD tự động chạy hơn 5 kịch bản Unit Test và Integration Test mô phỏng hacker để bảo vệ các Endpoints.

---

## 📁 Cấu Trúc Mã Nguồn

Dự án được phân tách thành các module rõ ràng (Clean Architecture):

- `app.py`: Entry point khởi chạy Web Server (Flask).
- `routes/`: Controllers xử lý API (Chia thành `auth.py`, `user.py`, `admin.py`).
- `services/`: Các Service lõi chứa Business Logic:
  - `ai_grader.py`: Thu thập bài tập và kết nối API của AI.
  - `docker_manager.py`: Khởi tạo và dọn dẹp môi trường Container cho sinh viên.
  - `workspace_manager.py`: Quản lý, đọc/ghi và thu thập file trong Workspace.
  - `arduino.py`: Giao tiếp với Arduino CLI để biên dịch và nạp code xuống board vật lý.
- `utils/`: Chứa các hàm hỗ trợ chung (Helpers, Rate Limit Decorators, Security).
- `tests/`: Nơi chứa bộ kiểm thử tự động (Pytest) mô phỏng tải nặng và các kịch bản lỗi hệ thống.
- `docs/`: Chứa báo cáo kiến trúc và lịch sử nâng cấp hệ thống.

---

## 🛠️ Hướng Dẫn Cài Đặt & Chạy (Local)

### Yêu cầu hệ thống:
- Hệ điều hành Linux (Ubuntu/Debian recommended).
- Đã cài đặt Docker, Python 3.10+ và MySQL 8.0+.
- Có board Arduino/ESP cắm sẵn vào cổng `/dev/ttyUSB*` (Nếu muốn test luồng nạp thật).

### Các bước khởi chạy:
1. **Clone dự án & Cài thư viện:**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. **Cấu hình biến môi trường:**
Tạo file `.env` từ file `.env.example` và điền các API Key (GEMINI_API_KEY, GROQ_API_KEY) cùng với thông tin kết nối Database.

3. **Khởi chạy hệ thống:**
```bash
python app.py
```
Server sẽ chạy mặc định tại `http://127.0.0.1:5000`. 

4. **Chạy kiểm thử (CI/Tests):**
```bash
PYTHONPATH=. venv/bin/pytest tests/test_core_security.py -v
```

---
*Dự án NCKH được phát triển với trọng tâm mang đến trải nghiệm học tập IoT tốt nhất, xoá bỏ rào cản phần cứng cho sinh viên.*
