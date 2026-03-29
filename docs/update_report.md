# Báo cáo Cập nhật & Nâng cấp Hệ thống Admin Exam

*Ngày tạo:* Ngày 11 tháng 03 năm 2026
*Project:* EPU Tech IoT Lab Management System (Flask)

## Tổng quan các chức năng đã triển khai
1. **Thiết lập Môi trường & Bảo mật**: Di dời các secret key ra tệp `.env`.
2. **Cơ sở dữ liệu (Database)**: Khởi tạo các bảng phục vụ tính năng mở rộng thi/kiểm tra.
3. **Admin Dashboard**: Giao diện tạo bài thi, giao bài cho sinh viên, quản lý danh sách và xuất Excel điểm số.
4. **Hệ thống AI chấm điểm**: Tích hợp Google Gemini (gemini-2.5-flash) thay thế framework cũ và bổ sung cơ chế lưu data tự động.
5. **Tối ưu hóa Codebase**: Fix lỗi Linting (Flake8), dọn dẹp các import thừa và tái cấu trúc (refactoring).

---

## Chi tiết các thay đổi theo File

### 1. `app.py`
- Tích hợp `dotenv` (`from dotenv import load_dotenv`) để nạp các hằng số môi trường (như `FLASK_SECRET_KEY`) nhằm bảo mật session của người dùng, không còn phụ thuộc vào `os.urandom(24)` gây mất session khi khởi động lại server.
- Tái cấu trúc chuẩn PEP 8: Đưa toàn bộ các import module lên đầu tệp, loại bỏ các thư viện khai báo nhưng không dùng (`asgiref.wsgi`, `requests`, v.v.).
- Khắc phục lỗi `global background_services` và đảm bảo lệnh Stop Services chạy mượt mà khi server tắt (graceful shutdown).
- Chỉnh lại cấu trúc Socket handlers: Sử dụng `init_sockets(socketio)` thay vì tách lẻ các hàm đăng ký không cần thiết.

### 2. `config/database.py`
- Sửa hàm `init_db()` để bao gồm logic **tạo thêm 3 bảng mới** nếu chưa tồn tại:
  - `missions`: Chứa thông tin đề thi (Tên, mô tả nội dung Markdown, loại bài làm, thời gian làm mặc định, thời gian bắt đầu và kết thúc).
  - `mission_assignments`: Mapper liên kết bài thi với ID của sinh viên được giao.
  - `submissions`: Nơi lưu trữ nội dung bài nộp gốc, điểm số AI đánh giá, và phản hồi của hệ thống.

### 3. `routes/admin.py`
- **Tạo Mission Mới (`POST /api/missions`)**: Cập nhật logic backend để lấy các tham số quan trọng (`mission_name`, `type`, `duration_minutes`, `start_time`, `end_time`) từ giao diện và cấp quyền (assignment) dựa trên ID sinh viên.
- **Danh sách Mission (`GET /api/missions`)**: API trả về danh sách lịch sử đề thi cho UI.
- **Export Excel (`GET /api/missions/<id>/export`)**: Tích hợp `pandas` và `openpyxl`. Backend sẽ thực hiện join SQL để lấy Username, Email, Trạng thái bài nộp và Điểm số để xuất ra file có tên động định dạng `.xlsx`.
- *Linting Fix*: Xóa bỏ các lệnh `import shutil, subprocess, math.ceil` không dùng đến và khắc phục các sai sót về dãn dòng (indentation error).

### 4. `services/ai_grader.py`
- **Nâng cấp AI Provider**: Chuyển đổi từ `anthropic` client cũ sang `google-genai` (SDK chính thức của Google) với model tiên tiến `gemini-2.5-flash`.
- Đảm bảo prompt đưa ra format chuẩn JSON bao gồm tiêu chí chấm chi tiết (Code, thuật toán, logic...).
- **Data Collection (Lưu trữ Dữ liệu)**: Thêm khối logic chạy ngầm để append các cuộc hội thoại giữa code của sinh viên và đánh giá của AI vào file `data/ai_training_dataset.jsonl`. Rất hữu ích cho mục đích Fine-Tuning LLM nội bộ sau này.
- Load biến môi trường `GEMINI_API_KEY` an toàn.

### 5. `templates/admin/missions.html`
- **UI Form Cập nhật**: Bổ sung bộ chọn Loại bài (Thi hoặc Kiểm tra). Sử dụng Javascript gắn event tự động gán 90 phút nếu là bài "Thi" và 45 phút nếu là "Kiểm tra".
- Bổ sung `datetime-local` input cho mục **Thời gian Bắt đầu** và **Thời gian Kết thúc**.
- Thêm một Textarea cho phép Admin điền **Mô tả đề thi** (Hỗ trợ Markdown syntax).
- **Table Danh sách Bài thi**: Dựng DOM table ở phía dưới giao diện để `fetch` và liệt kê toàn bộ bài thi đã tạo thay vì để trống như trước. Cột Hành Động (Action) chứa nút "Xuất Excel" gắn liên kết tải trực tiếp đến file của API `export`.

### 6. `.env` và Môi trường
- Đã cài đặt thêm các pip dependency: `python-dotenv`, `google-genai`, `pandas`, `openpyxl`.
- Đã điền sẵn `GEMINI_API_KEY` tại thiết lập server hiện hành của anh.

---
**Kết luận:** Hệ thống đã được mở rộng thành công sang quản lý thi cử và đánh giá tự động bằng Generative AI, song song với việc nâng cao bảo mật mã định danh chung và tối ưu lượng băng thông gọi API thông qua Refactoring thư viện. Cấu trúc hiện tại rất vững chắc để scale thêm học viên hoặc mô hình bài tập nặng hơn.
