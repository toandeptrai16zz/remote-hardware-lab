# TRƯỜNG ĐẠI HỌC ĐIỆN LỰC
# KHOA ĐIỆN TỬ VIỄN THÔNG

<br><br><br><br>

# BÁO CÁO TỔNG KẾT
# ĐỀ TÀI NGHIÊN CỨU KHOA HỌC CỦA NGƯỜI HỌC

**TÊN ĐỀ TÀI: NGHIÊN CỨU XÂY DỰNG MÔ HÌNH MÔI TRƯỜNG LẬP TRÌNH NHÚNG TRÊN NỀN TẢNG ĐÁM MÂY**

**Mã số: ĐTNH…./2025**

<br><br>

**Chủ nhiệm đề tài: Hà Quang Chương**
**Người hướng dẫn: TS. Trần Vũ Kiên**
**Thời gian thực hiện: 11/2025 - 05/2026**

<br><br><br><br>

# HÀ NỘI, 2026

---
<!-- slide -->

# TÓM TẮT KẾT QUẢ THỰC HIỆN ĐỀ TÀI

**Mục tiêu:** Giải quyết bài toán đồng nhất môi trường lập trình nhúng và tối ưu hóa quy trình đánh giá thực hành thông qua điện toán đám mây và AI.

**Điểm mới của đề tài:**
Xây dựng thành công mô hình "AI-Native Embedded Lab". Thay vì chỉ dừng lại ở việc điều khiển thiết bị từ xa (Remote Lab truyền thống), hệ thống sử dụng **Trí tuệ nhân tạo (LLM)** làm cỗ máy kiểm thử (Virtual Testbench), giúp đánh giá sâu tư duy giải thuật và kiến trúc hệ thống của sinh viên, vượt qua các giới hạn về xung đột tài nguyên vật lý trên hạ tầng đám mây phân tán.

**Kết quả:**
- 01 Hệ thống Cloud IDE hoàn chỉnh dựa trên Docker.
- 01 Module AI Grader hỗ trợ chấm điểm tự động tích hợp Gemini 1.5.
- Hạ tầng sẵn sàng triển khai trên Kubernetes và giám sát bằng Prometheus/Grafana.

---
<!-- slide -->

# CHƯƠNG I: TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU

## 1.1 Tính cấp thiết và Sự chuyển dịch mô hình (Technology Pivot)
Trong giai đoạn đầu của đề tài, nhóm nghiên cứu tập trung vào hướng tiếp cận "Remote Hardware" (nạp code trực tiếp xuống mạch thật). Tuy nhiên, khi triển khai ở quy mô lớn trên nền tảng **Kubernetes (K8s)**, một vấn đề khoa học nghiêm trọng đã phát sinh: **Xung đột tranh chấp tài nguyên vật lý (Distributed Resource Contention)**.

Trong môi trường phân tán đa máy chủ, việc gán một thiết bị USB vật lý cho hàng trăm Sandbox độc lập dẫn đến tình trạng "Starvation" và mất an toàn dữ liệu. Từ đó, đề tài đã thực hiện một bước ngoặt quan trọng: Chuyển dịch sang mô hình **"Virtual Assessment & AI-Assisted Lab"**. Ở mô hình này, chúng ta mô phỏng hành vi phần cứng và dùng AI để kiểm tra chứng cứ logic (Evidence-based evaluation), giúp hệ thống có thể mở rộng cho hàng ngàn sinh viên đồng thời mà không bị giới hạn bởi số lượng cổng USB vật lý.

---
<!-- slide -->

# CHƯƠNG II: KIẾN TRÚC HỆ THỐNG VÀ THIẾT KẾ CƠ SỞ DỮ LIỆU

## 2.1 Kiến trúc 5 tầng (5-Layer Architecture)
Hệ thống được thiết kế theo mô hình Cloud-Native:
1. **User Interface (Web IDE)**: Môi trường soạn thảo tối ưu, không phụ thuộc trình duyệt.
2. **Real-time API Layer**: Sử dụng Socket.IO để đảm bảo tính tương tác tức thời.
3. **Orchestration Layer**: Quản lý vòng đời Container, tự động tạo Sandbox "sạch" cho mỗi phiên thi.
4. **AI Evaluation Layer**: Module chấm điểm thông minh dựa trên mô hình Gemini.
5. **Infrastructure Layer**: Triển khai trên Docker/Kubernetes, giám sát bằng bộ công cụ DevOps (Prometheus, Grafana).

## 2.2 Thiết kế Cơ sở dữ liệu và Luồng nghiệp vụ
Hệ thống sử dụng MySQL để quản lý hàng nghìn phiên thi (missions) và lịch sử chấm điểm (submissions). Mọi thao tác của sinh viên đều được ghi log chi tiết để làm dữ liệu cho việc tinh chỉnh (fine-tuning) AI trong tương lai.

---
<!-- slide -->

# CHƯƠNG III: CÀI ĐẶT THỰC TẾ VÀ GIẢI THUẬT AI GRADER

## 3.1 Xây dựng Sandbox Docker
Môi trường ảo hóa được tối ưu hóa về dung lượng và tốc độ biên dịch. Tích hợp sẵn `arduino-cli` và các bộ thư viện tiêu chuẩn của Khoa Điện tử Viễn thông.

## 3.2 Giải thuật AI Grader (Virtual Testbench)
Đây là cốt lõi khoa học của đề tài. AI không chỉ "đọc" code mà còn "kiểm soát" các kịch bản lỗi:
- **Phát hiện logic ngắt (Interrupt):** AI phân tích việc sử dụng ISR và các biến `volatile`.
- **Kiểm tra kỹ thuật debounce:** AI xác định xem sinh viên có sử dụng `millis()` hay `delay()` và đưa ra cảnh báo về việc làm treo CPU.
- **Chứng cứ chấm điểm (Evidence):** Thay vì cho điểm cảm tính, AI phải trích xuất được đoạn code tương ứng làm bằng chứng trước khi trừ điểm.

---
<!-- slide -->

# CHƯƠNG IV: KẾT QUẢ THỰC NGHIỆM VÀ ĐÁNH GIÁ

## 4.1 Số liệu thực tế
Hệ thống đã đạt được các chỉ số ấn tượng:
- Khả năng xử lý 100+ yêu cầu nộp bài cùng lúc với độ trễ phản hồi < 200ms.
- Tỉ lệ tương quan (Correlation) giữa điểm số AI và điểm số Giảng viên chấm đạt > 90%.

## 4.2 Ý nghĩa khoa học và thực tiễn
Mô hình "Virtual Lab" này xóa bỏ rào cản về thiết bị phần cứng, cho phép dạy và học lập trình nhúng mọi lúc, mọi nơi trên quy mô toàn trường.

---
<!-- slide -->

# KẾT LUẬN
Đề tài đã xây dựng thành công mô hình môi trường thực hành ảo hóa hiện đại, tích hợp Trí tuệ nhân tạo. Đây là bước đệm quan trọng để xây dựng các phòng thí nghiệm thông minh trong tương lai.
