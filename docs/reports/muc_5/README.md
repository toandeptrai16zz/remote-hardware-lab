# Mục 5: Báo cáo Kiểm thử và Giám sát Hệ thống

## 1. Phương pháp Kiểm thử Toàn diện
Hệ thống tận dụng thư viện `pytest` và `pytest-flask` để bao phủ những chức năng trọng yếu nhất của ứng dụng.
- **Unit Tests**: Kiểm định các API HTTP Response gốc, chặn đường dẫn xấu. 
- Mọi sửa đổi trước khi merge code đều cần vượt qua thư mục `tests/`.

## 2. Hệ thống Giám Sát Metrics (Prometheus)
Backend Flask đã được chèn Hook/Middleware là `prometheus_client` nhằm mở thêm điểm cuối `/metrics`. Cục Service Prometheus nằm gọn trong mạng Kubernetes sẽ định kỳ bắt luồng dữ liệu RAM, xử lý Requests này.

## 3. UI Dashboard Giám Sát (Grafana)
Thay vì xây dựng dashboard biểu đồ thủ công rườm rà, đồ thị từ Prometheus được đưa qua Grafana (cổng `30000`). Admin/Giảng viên có thể nhìn trực quan Server CPU hiện hành để cấp tải thêm Container cho sinh viên hợp lý.
