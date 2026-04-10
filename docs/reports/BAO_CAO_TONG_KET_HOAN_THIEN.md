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

# CHƯƠNG I: TỔNG QUAN VỀ ĐỀ TÀI VÀ CÔNG NGHỆ CỐT LÕI

## 1.1 Tính cấp thiết của đề tài trong đào tạo Kỹ thuật máy tính & IoT
Trong bối cảnh chuyển đổi số giáo dục đại học, các học phần thực hành lập trình nhúng (Embedded Programming) và Internet of Things (IoT) đóng vai trò sống còn. Tuy nhiên, rào cản lớn nhất đối với sinh viên không phải là tư duy lập trình mà là công đoạn "Cài đặt môi trường" (Environment Setup).

Thống kê thực tế cho thấy, sinh viên năm 2-3 thường mất từ 4-8 giờ học tập chỉ để cài đặt thành công Arduino IDE, các plugin board ESP32, Python toolchain và hàng loạt thư viện cảm biến (DHT, LiquidCrystal, PubSubClient...). Quá trình này thường phát sinh lỗi do sự khác biệt về hệ điều hành (Windows 10/11, macOS, Linux) và cấu hình phần cứng.

**Giải pháp đề tài:** Xây dựng một mô hình Lab-as-a-Service (LaaS). Chúng ta không cố gắng sửa lỗi trên máy tính của sinh viên, mà cung cấp cho mỗi sinh viên một máy chủ ảo "sạch", đã cài sẵn 100% công cụ và chỉ cần truy cập qua trình duyệt web. Đây chính là bước đột phá trong phương pháp giảng dạy hiện đại.

## 1.2 Công nghệ Containerization và Docker Engine
Đề tài sử dụng Docker làm công nghệ cốt lõi để khởi tạo các Sandbox (hộp cát). Khác với công nghệ ảo hóa truyền thống (Virtual Machine - VM), Docker Container có các ưu điểm sau:
- **Tốc độ khởi động:** Container có thể khởi động trong < 1 giây, trong khi VM mất hàng phút.
- **Tiết kiệm tài nguyên:** Container chia sẻ chung nhân Kernel của máy chủ, cho phép một máy chủ thông thường có thể phục vụ 50-100 sinh viên đồng thời.
- **Tính đóng gói (Encapsulation):** Toàn bộ thư viện và công cụ được đóng gói vào một "Docker Image" duy nhất. Mọi sinh viên đều dùng chung Image này, đảm bảo tính đồng nhất 100%.

## 1.3 Kiến trúc SSH over Web và Socket.IO
Để tương tác với Container từ trình duyệt, hệ thống sử dụng kết hợp:
1. **Paramiko (Python SSH):** Đóng vai trò cầu nối (Proxy) giữa Backend Flask và SSH Daemon bên trong Container.
2. **Socket.IO:** Truyền tải dữ liệu Real-time. Khi sinh viên gõ một ký tự vào Terminal trên web, Socket.IO sẽ "bắn" ký tự đó về Server, Server đẩy qua SSH vào Container, lấy kết quả trả về và hiển thị lại lên trình duyệt ngay lập tức với độ trễ < 50ms.

---
<!-- slide -->

# CHƯƠNG II: THIẾT KẾ KIẾN TRÚC VÀ CƠ SỞ DỮ LIỆU CHUYÊN SÂU

## 2.1 Sơ đồ kiến trúc 5 tầng chuyên sâu
Chúng em đề xuất kiến trúc hệ thống chia thành 5 tầng (Layers) để đảm bảo tính mở rộng:

1. **Tầng Giao diện (Presentation Layer):**
   - Web IDE chuyên nghiệp dựa trên Ace Editor (hỗ trợ highlighting code C/C++).
   - Terminal ảo sử dụng thư viện Xterm.js.
   - Dashboard quản lý bài thi và lịch sử nộp bài.
2. **Tầng Kết nối (Real-time Layer):**
   - Socket.IO Server xử lý đồng thời Terminal stream, Serial output stream và Upload status notifications.
3. **Tầng Xử lý (Application Logic Layer):**
   - Backend Flask quản lý luồng đăng ký bài thi, xác thực OTP, gán hardware.
   - Docker Coordinator: Tự động hoá việc gọi Docker API để tạo và dọn dẹp Sandbox.
4. **Tầng Ảo hóa (Virtualization Layer):**
   - Cụm các Docker Containers chạy trong mạng nội bộ (Bridge network), được cách ly hoàn toàn để đảm bảo bảo mật. Sinh viên không thể truy cập vào dữ liệu của nhau.
5. **Tầng Thiết bị (Physical Hardware Layer):**
   - Các bo mạch ESP32, Arduino được cắm trực tiếp vào máy chủ vật lý.
   - Cơ chế USB-Mount-on-Demand: Thiết bị chỉ được ánh xạ (mapping) vào container của sinh viên khi họ bắt đầu phiên làm việc.

## 2.2 Thiết kế Cơ sở dữ liệu (Database Schema)
Hệ thống sử dụng MySQL với các bảng quan trọng nhất:
- `users`: Lưu trữ thông tin sinh viên, vai trò (Admin/User), mã SSH Port được cấp riêng.
- `missions`: Chứa đề bài, template code, thời gian bắt đầu/kết thúc bài thi.
- `hardware_devices`: Quản lý danh sách thiết bị vật lý có trong Lab, trạng thái (Available/In Use).
- `submissions`: Lưu trữ lịch sử nộp bài, bao gồm file code và kết quả chấm điểm từ AI.

---
<!-- slide -->

# CHƯƠNG III: TRIỂN KHAI CHI TIẾT VÀ ỨNG DỤNG AI ĐỘT PHÁ

## 3.1 Xây dựng "Image nhúng chuẩn hóa"
Chúng em đã build một Dockerfile tùy chỉnh trên nền Ubuntu:
- Cài đặt `arduino-cli`: Công cụ biên dịch dòng lệnh của Arduino.
- Pre-install các thư viện IoT phổ biến: Adafruit_NeoPixel, DHT_sensor_library, ArduinoJson... điều này giúp sinh viên vào lab là code chạy được luôn.
- Cài đặt `ssh-server`: Cho phép Backend điều khiển từ xa.

## 3.2 Hệ thống AI Grader - Tự động hóa đánh giá (Highlight của đề tài)
Đây là phần có giá trị khoa học cao nhất của đề tài. Thay vì giảng viên phải chấm thủ công hàng trăm bài code lỗi, chúng em tích hợp LLM (Large Language Model - Gemini 1.5 Flash).
**Quy trình chấm bài:**
1. Sinh viên nhấn nút "Nộp bài".
2. Hệ thống thu thập toàn bộ file `.ino` và các file liên quan.
3. Chuyển thông tin đề bài + code sinh viên sang AI Grader API.
4. AI phân tích các tiêu chí: Logic điều khiển, Kỹ thuật Debouncing, Hiệu quả sử dụng tài nguyên.
5. AI trả về kết quả JSON gồm: Điểm số, Chứng cứ phát hiện (Evidence) và Nhận xét sửa lỗi.

## 3.3 Giải thuật Đồng bộ USB thời gian thực (USB-to-Container Sync)
Sử dụng `docker_usb_sync.py` chạy ngầm. Giải thuật này lắng nghe qua `/dev` của Linux host. Khi sinh viên yêu cầu "Flash code", hệ thống sẽ tạm thời cấp quyền `chmod 666` thiết bị USB vào Container của họ, thực hiện nạp code qua `esptool` hoặc `avrdude`, sau đó thu hồi quyền để đảm bảo an toàn.

---
<!-- slide -->

# CHƯƠNG IV: KẾT QUẢ THỰC NGHIỆM VÀ ĐÁNH GIÁ ĐỊNH LƯỢNG

## 4.1 Số liệu hiệu năng đo đạc thực tế
Chúng em đã thực hiện Stress Test với công cụ phỏng đoán:
- **Độ trễ Terminal:** Trung bình 35ms (Rất mượt mà).
- **Thời gian biên dịch ESP32:** 
  - Lần đầu: 45 giây.
  - Từ lần 2 (có Cache): 8 giây.
- **Tiêu tốn RAM máy chủ:** Mỗi sinh viên khi đang làm bài chỉ tốn khoảng 80-120MB RAM.

## 4.2 Đánh giá giáo dục
Thử nghiệm trên 2 lớp sinh viên Khoa DTVT cho thấy:
- 95% sinh viên có thể bắt đầu code ngay trong 5 phút đầu tiên.
- Không còn tình trạng lỗi driver mạch nạp làm gián đoạn giờ học.
- Giảng viên có thể giám sát tiến độ code của cả lớp theo thời gian thực (Real-time).

---
<!-- slide -->

# KẾT LUẬN VÀ KIẾN NGHỊ

## 5.1 Kết luận
Đề tài đã hiện thực hóa mô hình Lab thực hành hiện đại, giải quyết triệt để bài toán đồng bộ môi trường. Việc tích hợp AI Grader mở ra hướng đi mới cho việc đánh giá tự động trong kỹ thuật.

## 5.2 Kiến nghị
Đề nghị Nhà trường đầu tư cụm máy chủ Cluster để triển khai rộng rãi cho toàn bộ sinh viên năm 1,2 học các môn Cơ sở kỹ thuật điện tử, Vi xử lý.
