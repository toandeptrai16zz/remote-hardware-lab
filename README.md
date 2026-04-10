# Remote Hardware Lab - Hệ Thống Thực Hành Nhúng AI-Native

## 🚀 Giới thiệu
Đây là nền tảng lập trình nhúng (PaaS) thế hệ mới, cho phép thực hành lập trình Arduino/ESP32 ngay trên trình duyệt. 

**Đặc biệt:** Hệ thống đã chuyển dịch từ mô hình nạp phần cứng vật lý sang mô hình **AI-Native Virtual Lab**. Chúng tôi sử dụng trí tuệ nhân tạo (AI) để chấm điểm và nhận xét bài làm của sinh viên một cách chuyên sâu, giải quyết triệt để bài toán quy mô (Scalability) trên Kubernetes.

## 🤖 Công nghệ AI Grader
Hệ thống tích hợp đa mô hình ngôn ngữ lớn (LLM) để đảm bảo độ tin cậy và tốc độ:
- **Google Gemini 1.5 Flash**: Engine chấm điểm chính.
- **Anthropic Claude 3.5**: Engine dự phòng chất lượng cao.
- **GROQ (LLaMA 3.3 70B)**: Engine siêu tốc chuyên dụng cho phản hồi tức thì.

## ✨ Tính năng chính
- **Cloud IDE**: Soạn thảo code chuyên nghiệp không cần cài đặt.
- **Terminal & Serial ảo**: Tương tác thời gian thực qua WebSockets (Socket.IO).
- **AI-Assisted Assessment**: Chấm điểm tự động dựa trên bằng chứng (Evidence-based).
- **Docker Sandboxing**: Mỗi sinh viên một môi trường cô lập tuyệt đối.
- **Kubernetes Ready**: Sẵn sàng triển khai trên quy mô lớn.

## 📁 Cấu trúc thư mục (Refactored)
- `app.py`: Entry point chính.
- `routes/`: Các API endpoints (Auth, User, Admin).
- `services/ai_grader.py`: "Linh hồn" của hệ thống - xử lý chấm điểm đa mô hình.
- `docs/reports/`: Các báo cáo thuyết minh đề tài chi tiết.

## 🛠️ Cách chạy
```bash
python app.py
```
*(Chi tiết xem tại docs/README_REFACTORED.md)*
