# BÁO CÁO TỔNG KẾT NÂNG CẤP HỆ THỐNG REMOTE HARDWARE LAB
**Ngày thực hiện:** 12/05/2026

Dựa trên yêu cầu tối ưu hóa hệ thống chuẩn bị cho đợt bảo vệ NCKH/Đồ án tốt nghiệp, toàn bộ các hạng mục cốt lõi liên quan đến **Kiến trúc mã nguồn**, **Hiệu năng (Performance)** và **Bảo mật (Security)** đã được nâng cấp thành công. Dưới đây là chi tiết các hạng mục đã hoàn thiện:

---

## 1. Nâng Cấp Bảo Mật & Chống Quá Tải (Rate Limiting & Lockdown)
*   **Vấn đề cũ:** Hệ thống dễ bị tê liệt CPU nếu sinh viên click liên tục vào nút "Biên dịch" hoặc cố tình sửa đổi các file hệ thống (như `.bashrc`).
*   **Giải pháp đã triển khai:**
    *   **Rate Limiter:** Viết thêm `Decorator` chuyên dụng để giới hạn tần suất gọi API. Cụ thể: Nút "Biên dịch" có thời gian chờ (cooldown) là **10 giây**, nút "Nạp Code" là **15 giây**. Hệ thống theo dõi theo `username` thay vì IP để tránh lỗi mạng nội bộ trường học.
    *   **File Lockdown:** Khóa hoàn toàn quyền đổi tên, xóa đối với các file nhạy cảm (`WELCOME.txt`, `.bashrc`). API `/rename-item` sẽ trả về lỗi `403 Forbidden` nếu phát hiện hành vi này.

## 2. Quản Lý Tài Nguyên Tự Động (Garbage Collection Worker)
*   **Vấn đề cũ:** Docker Container của sinh viên chạy liên tục 24/7 gây lãng phí RAM máy chủ.
*   **Giải pháp đã triển khai:**
    *   Xây dựng một luồng chạy ngầm (Background Thread) liên tục giám sát hoạt động của sinh viên.
    *   Bất cứ user nào không tương tác với Web IDE quá **2 giờ**, Container tương ứng sẽ tự động bị tắt (`docker stop`).
    *   Cơ chế này giúp Server có thể phục vụ hàng trăm sinh viên mà không lo tràn RAM (Memory Leak).

## 3. Tái Cấu Trúc Mã Nguồn (Refactoring & DRY)
*   **Vấn đề cũ:** Logic thu thập file bài thi bị viết lặp lại nhiều lần ở các API khác nhau, dễ gây lỗi khi có thay đổi.
*   **Giải pháp đã triển khai:**
    *   Chuyển toàn bộ logic đệ quy quét file sang Service tập trung: `services/workspace_manager.py` (hàm `collect_mission_files`).
    *   Tối ưu hóa: Loại bỏ các thư mục rác như `node_modules` và giới hạn dung lượng nội dung đọc ở mức **50KB** mỗi file để tránh đứng máy ảo.

## 4. Kiểm Thử Chuyên Sâu & CI Pipeline (Deep Testing)
*   **Vấn đề cũ:** Hệ thống CI trên Github Actions chạy rất bề mặt, thiếu database và không test được các góc khuất bảo mật.
*   **Giải pháp đã triển khai:**
    *   **Unit Tests:** Phủ test cho các hàm lõi (Ví dụ: `is_safe_path` đã chặn thành công đường dẫn leo thang thư mục `../../../etc/passwd`).
    *   **Integration Tests:** Bắn request giả lập API để chứng minh tính năng Rate Limiting và File Lockdown thực sự hoạt động và trả về HTTP 429/403.
    *   **Github Actions CI:** Tích hợp thành công **MySQL 8.0 Service Container** vào luồng chạy tự động. Hệ thống giờ đây có khả năng tự động dựng Database ảo trên mây và chạy test thực tế mỗi khi có code mới được Push lên.

---

**Kết luận:** Hệ thống hiện tại đã đạt đủ độ trưởng thành (Maturity) của một sản phẩm phần mềm thực tế, đảm bảo tính ổn định tuyệt đối, chống lỗi chủ quan từ người dùng và sẵn sàng chịu tải cho các luồng truy cập đồng thời lớn. Đã đủ điều kiện đóng gói báo cáo NCKH.
