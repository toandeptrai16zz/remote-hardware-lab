# BÁO CÁO TỔNG KẾT ĐỀ TÀI NGHIÊN CỨU KHOA HỌC CỦA NGƯỜI HỌC
Trường: Đại học Điện Lực

**Tên đề tài tiếng Việt:** 
Nghiên cứu và xây dựng hệ thống thực hành lập trình nhúng từ xa (Remote Hardware Lab) tích hợp chấm điểm AI tự động
**Tên tiếng Anh (Đề xuất):** 
Research and development of a remote embedded systems laboratory integrating automated AI-based grading

---

## Tóm tắt kết quả thực hiện đề tài
Đề tài đã nghiên cứu và phát triển thành công Web-based IDE cho phép sinh viên lập trình, biên dịch và tương tác với phần cứng vật lý qua Internet. Đáng chú ý, hệ thống tích hợp công nghệ AI (Google Gemini) để tự động chấm điểm, phân tích cú pháp và tối ưu hóa mã nguồn. Kết quả chính bao gồm: 
1) Nền tảng Cloud IDE hỗ trợ ESP32/Arduino. 
2) Luồng Auto-grader bằng AI cho phép thi và kiểm tra trực tuyến an toàn. 
3) Giao diện Glassmorphism hiện đại, dễ thao tác với Terminal và File Explorer riêng biệt.

---

## MỤC LỤC

### I. ĐẶT VẤN ĐỀ
* **Bối cảnh:** Chi phí trang bị thiết bị phần cứng (vi điều khiển, cảm biến) cho mỗi sinh viên rất đắt đỏ và dễ hỏng hóc trong quá trình thực hành.
* **Thời đại AI:** Việc chấm điểm thủ công các bài tập phần cứng (nhúng) của giảng viên tốn nhiều thời gian và khó phát hiện lỗi thiết kế tối ưu.
* **Hạn chế của hệ thống cũ:** Chưa có sự kết nối thời gian thực giữa Web IDE, phần cứng thật ở phòng Lab, và công cụ chấm điểm AI tại Việt Nam.

### II. MỤC TIÊU CUẢ ĐỀ TÀI
* **Mục tiêu tổng quát:** Xây dựng khung hệ thống nền tảng Giáo dục thông minh phục vụ học tập Lập trình vi điều khiển/IoT từ xa.
* **Mục tiêu cụ thể:** 
  1) Xây dựng giao diện mô phỏng Web IDE trên môi trường web.
  2) Tích hợp luồng biên dịch thời gian thực (Arduino CLI, Docker, Socket.io).
  3) Phát triển module AI Grader chấm thi công bằng và cung cấp feedback hữu ích cho sinh viên.

---

### CHƯƠNG I: TỔNG QUAN TÌNH HÌNH NGHIÊN CỨU TRONG, NGOÀI NƯỚC
**I. TÌNH HÌNH NGHIÊN CỨU NGOÀI NƯỚC**
* Các nền tảng như Tinkercad, Wokwi đã làm tốt việc mô phỏng phần cứng (Simulator), nhưng chủ yếu chạy ảo hóa Frontend, khó kết nối với kit thật.
* Chưa áp dụng sâu AI LLMs vào chấm điểm mạch vật lý.

**II. TÌNH HÌNH NGHIÊN CỨU TRONG NƯỚC**
* Mô hình "Phòng Lab ảo" đang sơ khai, các trường Đại học vẫn phụ thuộc vào bài tập giấy hoặc nộp file zip code.
* Khai thác bài toán chấm tự động (Auto-grader) cho môn lập trình phần mềm (như HackerRank, Leetcode) đã phổ biến, nhưng cho phần cứng (Embedded C/C++) thì rất hiếm do đặc thù Hardware.

---

### CHƯƠNG II: NỘI DUNG VÀ PHƯƠNG PHÁP NGHIÊN CỨU

**2.4 Đối tượng, nội dung và phương pháp nghiên cứu**
* **a. Đối tượng và phạm vi nghiên cứu:** Sinh viên ngành Điện / Điện tử viễn thông / CNTT; Phạm vi hỗ trợ chip ESP32 và Arduino.
* **b. Nội dung nghiên cứu:**
  * Xây dựng kiến trúc hệ thống Client-Server phân tán (Platform).
  * Phát triển giao diện IDE Frontend với HTML/CSS/JS thuần, hiệu ứng Glassmorphism.
  * Cài đặt Backend Python Flask + WebSockets.
  * Tích hợp Docker và Arduino-CLI hỗ trợ Multi-tenant (để code không đụng độ nhau).
  * Áp dụng LLM (Google Gemini) thiết kế Prompt logic chấm điểm chuyên sâu.
* **c. Phương pháp nghiên cứu:**
  * *Thực nghiệm phần mềm:* Xây dựng prototype và tinh chỉnh dựa trên feedback.
  * *So sánh & Đánh giá:* Đối chiếu hiệu suất biên dịch với Arduino IDE truyền thống.

---

### CHƯƠNG III: KẾT QUẢ NGHIÊN CỨU VÀ ĐÁNH GIÁ

**3.1. Thiết kế và triển khai Cấu trúc hệ thống**
* Sơ đồ khối tổng quát (Vẽ sơ đồ luồng từ Trình duyệt -> Flask -> Docker -> Hardware/AI).
* Quản lý Cơ sở dữ liệu (MySQL Database: quản lý user, mission).

**3.2. Kết quả phần mềm (Giao diện và Tính năng)**
* Hiển thị hình ảnh Giao diện User IDE: File Explorer, Terminal giả lập, Cửa sổ gõ mã nguồn.
* Hệ thống popup hiệu ứng hiện đại tương tác thân thiện.

**3.3. Tính năng cốt lõi: Giao tiếp Phần cứng & Biên dịch (Compile)**
* Khả năng auto-detect FQBN (Nhận dạng chip ESP32 vs Arduino dựa trên tập từ khóa mã nguồn: ví dụ `ledcSetup` của ESP32).
* Phản hồi lỗi thời gian thực qua Terminal.

**3.4. Hệ thống Quản trị & Thi cử tích hợp AI (AI Grader)**
* Giao diện tạo bài thi, set thời gian của Admin.
* Cấu trúc Prompt AI (Giải thích cách thiết lập system_prompt bắt AI đóng vai trò giáo sư chấm điểm).
* Thống kê báo cáo điểm tự động.

---

### KẾT LUẬN VÀ KIẾN NGHỊ

**1. Kết luận:**
* Đề tài đã giải quyết được trọn vẹn quy trình: Code -> Biên dịch trên mây -> Trả kết quả kết hợp AI đánh giá.
* Tối ưu hóa được UI/UX mang lại trải nghiệm mượt mà không kém các phần mềm IDE Desktop.

**2. Kiến nghị & Hướng phát triển:**
* Mở rộng thêm nhiều dòng chip (STM32, Raspberry Pi).
* Kết nối trực tiếp stream Camera quan sát phần cứng thật đang chạy.
* Cần triển khai thử nghiệm trên sinh viên để đo lường tải server.

--- 

### CÁC PHỤ LỤC VÀ ẢNH MINH HOẠ
1. Hình ảnh Code Editor.
2. Hình ảnh bảng chấm điểm AI.
3. Hướng dẫn sử dụng hệ thống.
4. Tài liệu mã nguồn.
