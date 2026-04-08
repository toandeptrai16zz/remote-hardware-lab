# Tính năng Vượt trội (Không có trong Thuyết minh): AI Grader và Data Thu thập

Dù đã hoàn thành 100% 5 khối mục tiêu kỹ thuật, dự án còn đi xa hơn bằng việc xây dựng một hệ sinh thái AI hỗ trợ giảng dạy tự động chấm điểm và thu thập dữ liệu (AI & Data Pipeline).

## 1. Hệ thống AI Grader Tự động (Gemini & Claude)
Thay vì giáo viên chấm bài thủ công, hệ thống móc nối trực tiếp với 2 mô hình LLM hàng đầu thế giới:
- **Google Gemini 2.5 Flash** (Xử lý tốc độ cao, dùng làm chấm điểm chính).
- **Anthropic Claude 3.5 Sonnet** (Dùng làm Fallback dự phòng khi Gemini hết Quota API hoặc lỗi).

**Luồng hoạt động:** 
Mỗi khi sinh viên ấn Submit, mã nguồn C/C++ (hoặc ino) lập tức được đẩy qua AI. AI sẽ phân tích dựa trên 5 tiêu chí khắt khe (Cú pháp, Tư duy vòng lặp, Điều khiển chân phần cứng, Tối ưu hóa bộ nhớ RAM vi điều khiển...) và trả về điểm chuẩn kèm lời nhận xét vào Frontend qua cơ chế Polling 8 giây.

## 2. Đường ống Thu thập Dữ liệu (Data Collection Pipeline)
Đây là chiến lược dài hạn chứng minh tầm nhìn của sinh viên: Hệ thống thiết kế một máy thu thập Data tự động cho các nghiên cứu Fine-tune AI sau này.
- **Vị trí lưu trữ**: File `data/ai_training_dataset.jsonl` được append ngầm liên tục khi có submission.
- **Tại sao nó đắt giá?**: Việc thu thập `[Đề bài] -> [Mã nguồn thực tế của sinh viên] -> [Đánh giá đúng/sai]` tạo ra bộ dữ liệu chuẩn (Ground Truth). Qua nhiều học kỳ, khoa Điển tử Viễn thông có thể dùng bộ JSONL này để tự huấn luyện (Train/Fine-tune) một mô hình AI Local chạy offiline hoàn toàn trong tương lai, độc lập với Google hay Anthropic.
