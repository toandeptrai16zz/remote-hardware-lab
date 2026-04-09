# Mục 1: Báo cáo Phân tích Yêu cầu và Thiết kế Kiến trúc

## 1. Tính cấp thiết của đề tài
Các học phần thực hành lập trình nhúng đối mặt với khó khăn khi sinh viên phải cài đặt các Toolchain phức tạp, thiếu tính đồng nhất. Mặc dù bắt đầu với mô hình nạp code thẳng xuống mạch phần cứng, đồ án đã tiến hóa thành nền tảng Nền tảng Đánh giá Kỹ năng Nhúng Ảo hóa Cloud-Native bằng AI.

## 2. Biện luận lựa chọn Kiến trúc (Lý do chuyển đổi mô hình)
Trong giai đoạn phát triển, nhóm nhận thấy một "Lỗ hổng thắt cổ chai" (Bottleneck) mang tính hệ thống nếu ép buộc giao tiếp phần cứng vật lý qua luồng đám mây phân tán:
- **Xung đột IO phân tán trên Kubernetes (Distributed Data Race):** Nếu thiết kế server đơn giản, ta có thể dùng biến `threading.Lock` để bắt các yêu cầu nạp code vào xếp hàng đợi cắm vào `/dev/ttyUSB0`. Tuy nhiên, cờ Lock này chỉ tồn tại cục bộ trên 1 tiến trình. Bức tranh ở Kubernetes là hệ thống nhân bản đa Pod (Multiple Nodes). Khi hai Pod A và Pod B nạp song song, hai Lock xếp hàng của chúng độc lập không thể chặn nhau, dãn đến tình trạng xung đột tài nguyên vật lý, làm sụp đổ hoàn toàn cổng Serial.
- **Rủi ro rò rỉ (Isolation Risk):** Ánh xạ (Mount) một thiết bị vật lý xuống tất cả các Sandbox Docker của người dùng làm vỡ tính cô lập đặc thù.
- **Đặc trưng ngành Điện tử Viễn Thông (ĐTVT):** Điểm A+ của sinh viên ĐTVT nằm ở việc am hiểu tư duy viễn thông (xử lý ngắt Interrupt, memory leak, chuỗi bit truyền thông, tiết kiệm năng lượng). Một cái mạch thật không giúp chỉ ra lỗi tràn RAM, nhưng một cỗ máy Expert System (AI) được Prompt chuẩn kỹ sư phần cứng thì có thể!

**=> Quyết định chuyển hướng (Pivot):** Đề tài quyết định chuyển hướng sang "Kiểm soát Ảo hóa và AI Grader ĐTVT". Cắt đứt luồng Serial vật lý, tập trung gánh tải bằng Cỗ máy đánh giá Testbench AI.

## 3. Kiến trúc Tổng thể
- **Frontend**: Web IDE không cần chọn cổng COM.
- **Backend Lõi**: Flask (Python).
- **Hệ chấm (Evaluation)**: AI Grader sử dụng tư duy Kiến trúc sư Viễn Thông (Telecom Architect).
- **Orchestration & Hardware Limits**: Kubernetes + Prometehus.
