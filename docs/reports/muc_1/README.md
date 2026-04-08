# Mục 1: Báo cáo Phân tích Yêu cầu và Thiết kế Kiến trúc

## 1. Tính cấp thiết của đề tài
Các học phần thực hành lập trình nhúng đối mặt với khó khăn khi sinh viên phải cài đặt các Toolchain phức tạp, thiếu tính đồng nhất. Dự án đề xuất mô hình Lab-as-a-Service (LaaS) đưa toàn bộ môi trường lập trình lên đám mây.

## 2. Phân tích Yêu cầu
- **Yêu cầu chức năng**: Cung cấp Web IDE cho phép viết mã, biên dịch chéo, và nạp thẳng xuống mạch thật. Phát sinh container riêng biệt cho từng người.
- **Yêu cầu phi chức năng (Khả năng mở rộng)**: Triển khai hạ tầng điều phối đảm bảo nhiều lượt thi cùng lúc không sụp đổ server.
- **Yêu cầu hệ thống**: Đồng bộ hóa USB (Udev) giữa Host và Container.

## 3. Kiến trúc Tổng thể
- **Frontend**: HTML5, JS Terminal (xterm.js), WebSocket.
- **Backend Lõi**: Flask (Python), xác thực phiên bằng Kerberos/Session.
- **Orchestration**: Kubernetes + Docker Engine.
- **Giám sát (Monitoring)**: Prometheus + Grafana.
