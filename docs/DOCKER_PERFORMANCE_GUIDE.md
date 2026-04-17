# BÁO CÁO HIỆU NĂNG KHỞI TẠO DOCKER CONTAINER (REAL 100%) 🐳⏱️

Tài liệu này cung cấp số liệu thực nghiệm về thời gian khởi tạo không gian làm việc (IDE Sandbox) dành cho sinh viên, chứng minh khả năng phản hồi tức thì của hệ thống.

## 1. Kịch bản Đo lường (Benchmark Scenarios)

Chúng tôi thực hiện đo lường trên chính Image lõi của hệ thống (`my-dev-env:v2`) qua 4 tình huống thực tế:

- **KB1: Container đang chạy (Warm)**: Sinh viên F5 lại IDE hoặc chuyển tab. Hệ thống chỉ cần kiểm tra trạng thái và trả về cấu hình.
- **KB2: Khởi động lại (Cold-start)**: Sinh viên quay lại sau một thời gian (Container đã tồn tại nhưng bị dừng để tiết kiệm tài nguyên).
- **KB3: Cấp phát mới (Local Cache)**: Sinh viên đăng nhập lần đầu tiên. Container được tạo mới hoàn toàn từ Image có sẵn trên Server.
- **KB4: Tải mới (Internet Pull)**: Trường hợp Server chưa có Image (cài đặt mới). Cần tải Image từ internet/registry.

## 2. Kết quả Thực nghiệm (Latest Results) 📊

*Dữ liệu được đo vào ngày 18/04/2026 trên Server vật lý của Lab.*

| Tình huống | Thời gian TB (s) | Đánh giá | Ghi chú |
| :--- | :--- | :--- | :--- |
| **Container đang chạy** | **0.063s** | ⭐⭐⭐⭐⭐ | Phản hồi tức thì |
| **Cold-start (docker start)** | **0.269s** | ⭐⭐⭐⭐⭐ | Rất nhanh (< 0.5s) |
| **Tạo mới từ Local Cache** | **0.425s** | ⭐⭐⭐⭐⭐ | Đạt tiêu chuẩn Công nghiệp |
| **Pull từ Internet** | **19.573s** | ⭐⭐⭐ | Phụ thuộc tốc độ mạng |

> [!TIP]
> **Nhận xét**: Mục tiêu ban đầu của đề tài là thời gian khởi tạo dưới **2.0 giây**. Kết quả thực tế đạt **~0.4 giây**, vượt xa mong đợi và đảm bảo sinh viên không cảm thấy độ trễ khi bắt đầu bài thi.

## 3. Cách tái lập phép đo (Reproduce)

Đại ca có thể chạy lại script sau để lấy số liệu tươi mới nhất trước khi in báo cáo:
```bash
python3 tests/test_docker_time.py
```

---
**Hệ thống được tối ưu hóa bởi Chương - EPU Tech Systems**
