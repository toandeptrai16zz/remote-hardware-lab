TRƯỜNG ĐẠI HỌC ĐIỆN LỰC
Khoa Điện Tử - Viễn Thông

---

**BẢN HƯỚNG DẪN SỬ DỤNG CHI TIẾT**

**TÊN ĐỀ TÀI:**
NGHIÊN CỨU XÂY DỰNG VÀ THỬ NGHIỆM MÔ HÌNH HỆ THỐNG QUẢN LÝ CHIA SẺ THIẾT BỊ PHẦN CỨNG TỪ XA 
Mã số: ĐTNH. 112/2025

**Chủ nhiệm đề tài:** Trịnh Hoàng Tùng
**Người hướng dẫn:** TS. Trần Vũ Kiên
**Thời gian thực hiện:** từ 11/2025 đến 05/2026.

HÀ NỘI, 2026

---

## MỤC LỤC
1. [CHƯƠNG 1: TỔNG QUAN VỀ HỆ THỐNG](#chuong-1)
2. [CHƯƠNG 2: HƯỚNG DẪN CÀI ĐẶT VÀ TRIỂN KHAI CHO QUẢN TRỊ VIÊN](#chuong-2)
3. [CHƯƠNG 3: HƯỚNG DẪN SỬ DỤNG DÀNH CHO SINH VIÊN](#chuong-3)
4. [CHƯƠNG 4: HƯỚNG DẪN QUẢN TRỊ DÀNH CHO GIẢNG VIÊN](#chuong-4)
5. [CHƯƠNG 5: KIẾN TRÚC BẢO MẬT VÀ AN TOÀN HỆ THỐNG](#chuong-5)
6. [CHƯƠNG 6: XỬ LÝ SỰ CỐ VÀ CÂU HỎI THƯỜNG GẶP](#chuong-6)

---

<a name="chuong-1"></a>
## CHƯƠNG 1: TỔNG QUAN VỀ HỆ THỐNG

### 1.1. Giới thiệu chung về đề tài
Tài liệu này là bản hướng dẫn sử dụng toàn diện cho "Hệ thống Quản lý Chia sẻ Thiết bị Phần cứng Từ xa" (Remote Hardware Lab). Đây là nền tảng thực hành lập trình nhúng và IoT trực tuyến (PaaS - Platform as a Service) tiên tiến được xây dựng dựa trên kiến trúc phân tán Microservices.

### 1.2. Mục tiêu và đối tượng sử dụng
* **Mục tiêu:** Xóa bỏ rào cản về cơ sở vật chất, cho phép sinh viên thực hành lập trình vi điều khiển mọi lúc, mọi nơi mà không cần mua thiết bị vật lý hoặc cài đặt các phần mềm nặng như Arduino IDE.
* **Đối tượng:** 
  * Sinh viên, học viên tham gia các khóa học về Vi xử lý, Vi điều khiển, IoT.
  * Giảng viên, quản trị viên cần quản lý hàng loạt thiết bị thực hành và đánh giá tự động bài làm của sinh viên.

### 1.3. Kiến trúc tổng thể của hệ thống
Hệ thống là sự kết hợp của các công nghệ hiện đại nhất (AI-Native Virtual Lab):
* **Docker Sandboxing:** Tạo ra các môi trường thực hành độc lập (Container) cho từng sinh viên, đảm bảo sự an toàn tuyệt đối, ngăn chặn việc can thiệp hoặc truy cập chéo dữ liệu.
* **Multi-LLM Grader:** Động cơ AI tự động chấm bài với sự dự phòng (Fallback) linh hoạt giữa các mô hình lớn như Google Gemini 1.5 Pro, Anthropic Claude 3.5 Sonnet và LLaMA 3. Điều này giúp phân tích độ chính xác của logic lập trình và cung cấp phản hồi chi tiết thay vì chỉ kiểm tra testcase tĩnh tĩnh.
* **Socket.IO:** Giao tiếp thời gian thực, truyền tải log biên dịch, đầu ra của Serial Monitor và Terminal điều khiển với độ trễ siêu thấp.
* **Microservices:** Hệ thống chia thành các module độc lập như Backend (Flask), Database (MySQL), Realtime Broker, Hardware Compiler (Arduino CLI).

### 1.4. Đặc tả phần cứng hỗ trợ
Hệ thống hiện tại hỗ trợ 3 dòng vi điều khiển phổ biến nhất trong đào tạo:
* **Arduino Uno:** Nền tảng học tập cơ bản với chip ATmega328P.
* **ESP8266 (NodeMCU):** Nền tảng cho các bài thực hành IoT cơ bản có kết nối Wi-Fi.
* **ESP32 (DevKit):** Vi điều khiển mạnh mẽ cho các dự án IoT phức tạp, tích hợp Bluetooth và Wi-Fi băng tần rộng.

---

<a name="chuong-2"></a>
## CHƯƠNG 2: HƯỚNG DẪN CÀI ĐẶT VÀ TRIỂN KHAI CHO QUẢN TRỊ VIÊN

Chương này hướng dẫn chi tiết cách thiết lập môi trường cho hệ thống Lab trên một máy chủ (Server).

### 2.1. Yêu cầu hệ thống
Để hệ thống hoạt động trơn tru với số lượng sinh viên lớn:
* **Hệ điều hành:** Khuyến nghị dùng Linux (Ubuntu 22.04 / 24.04 LTS), Debian, hoặc WSL2 trên Windows. (Bắt buộc dùng nhân Linux để tương thích tốt nhất với Docker và /dev/ttyUSB).
* **CPU:** Tối thiểu 4 Cores (Khuyến nghị 8 Cores nếu số lượng sinh viên > 50).
* **RAM:** Tối thiểu 4 GB (Khuyến nghị 8 GB - 16 GB để duy trì hàng chục Docker Containers đồng thời).
* **Ổ cứng:** Tối thiểu 50 GB dung lượng trống để lưu trữ Image Docker và dữ liệu Workspace của sinh viên.

### 2.2. Chuẩn bị phần mềm nền tảng
Các gói ứng dụng bắt buộc phải được cấu hình trên Server:
1. **Python 3.10+**: Làm môi trường chạy Backend (Flask).
2. **Docker & Docker Compose v2**: Khởi tạo Container cho sinh viên.
3. **MySQL 8.0**: Hệ quản trị cơ sở dữ liệu lưu trữ thông tin sinh viên và lịch sử biên dịch.
4. **Arduino CLI**: Dành cho quá trình biên dịch firmware.

### 2.3. Lấy mã nguồn và Cấu hình môi trường
**Bước 1:** Clone mã nguồn từ kho lưu trữ về máy chủ.
```bash
cd ~/Desktop
git clone <url_repository> remote-hardware-lab
cd remote-hardware-lab
```

**Bước 2:** Cài đặt môi trường Python ảo.
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Bước 3:** Khai báo cấu hình hệ thống bằng tệp `.env`.
Copy tệp mẫu `.env.example` và đặt tên thành `.env`. Điền đầy đủ các thông số:
* `FLASK_SECRET_KEY`: Khóa ngẫu nhiên (Ví dụ: `openssl rand -hex 32`) dùng để ký mã hóa phiên đăng nhập.
* Thông số MySQL: `MYSQL_HOST=localhost`, `MYSQL_USER=root`, `MYSQL_PASSWORD=MatKhauBaoMat`, `MYSQL_DATABASE=remote_lab`.
* Tham số AI: Bổ sung `GEMINI_API_KEY` (Lấy từ Google AI Studio) và `GROQ_API_KEY` (Lấy từ Groq Console).

### 2.4. Build và khởi chạy hệ thống
**Cách 1: Khởi chạy bằng Docker Compose (Khuyên dùng cho Production)**
Hệ thống đã được đóng gói sẵn để tự động liên kết các thành phần:
```bash
docker compose up -d --build
```
Lệnh này sẽ khởi động Nginx (Cổng 80), Backend (Cổng 5000), MySQL (Cổng 3306), Frontend (Cổng 3000), Hardware Broker (Cổng 8000) và Compiler (Cổng 9000).

**Cách 2: Khởi chạy thủ công ở chế độ Phát triển (Dev Mode)**
Đảm bảo dịch vụ MySQL đang chạy.
```bash
source venv/bin/activate
python app.py
```
Server Flask cùng eventlet (hỗ trợ Socket) sẽ bắt đầu lắng nghe tại cổng `5000`.

### 2.5. Xử lý phần cứng và cổng nối tiếp (COM Port)
Khi cắm bo mạch ESP32 / Arduino vào cổng USB trên máy chủ, Linux thường gán chúng vào `/dev/ttyUSB0` hoặc `/dev/ttyACM0`. Để ứng dụng đọc/ghi xuống phần cứng:
```bash
sudo usermod -a -G dialout $USER
sudo chmod 666 /dev/ttyUSB0
```
*(Nếu dùng máy ảo VirtualBox, hãy chắc chắn đã bật USB Passthrough từ máy Host).*

---

<a name="chuong-3"></a>
## CHƯƠNG 3: HƯỚNG DẪN SỬ DỤNG DÀNH CHO SINH VIÊN

Đây là hướng dẫn chi tiết dành cho đối tượng người học khi sử dụng hệ thống để lập trình vi điều khiển.

### 3.1. Đăng nhập hệ thống
1. Mở trình duyệt Web (Chrome / Firefox / Edge).
2. Nhập đường dẫn được giảng viên cung cấp (Ví dụ: `http://lab.epu.edu.vn` hoặc địa chỉ IP).
3. Tại giao diện Đăng nhập, nhập `Tên tài khoản` và `Mật khẩu`. Hệ thống hỗ trợ phân quyền tự động, nếu bạn là sinh viên, bạn sẽ được chuyển đến Bảng điều khiển (User Dashboard).

### 3.2. Quản lý dự án (Workspace)
Ngay khi truy cập, hệ thống sẽ cấp cho bạn một "Không gian làm việc" (Workspace). Thực chất đằng sau đó, hệ thống đang cấp phát cho bạn một Sandbox (Docker Container) có đầy đủ hệ điều hành và thư viện C/C++ cần thiết.
* **Tạo File mới:** Nhấn vào biểu tượng dấu cộng (Add file) tại cây thư mục bên trái, nhập tên tập tin ví dụ: `main.ino`.
* **Cấu trúc thư mục:** Bạn có thể tự tạo các thư mục để chứa thư viện riêng.

### 3.3. Soạn thảo mã nguồn trên Cloud IDE
* Giao diện IDE tích hợp sẵn công nghệ của Monaco Editor (Cùng nền tảng với VS Code), hỗ trợ tô sáng cú pháp (Syntax highlighting), tự động thụt lề và tự động đóng ngoặc.
* Bạn có thể sử dụng các hàm phổ biến của Arduino như `setup()`, `loop()`, hay chèn thêm `#include <WiFi.h>`.
* **Lưu bài:** Bấm tổ hợp phím `Ctrl + S`. Trạng thái lưu sẽ báo xanh ở góc phải.

### 3.4. Biên dịch Firmware (Compile)
Sau khi hoàn thành đoạn code:
1. Bạn nhấn nút **Biên dịch** (Compile) màu xanh lam.
2. Trình biên dịch (Compiler Service) trên Server sẽ được gọi.
3. Cửa sổ Log (Output) bên dưới sẽ nhảy theo thời gian thực để báo cáo tiến trình. 
4. Nếu có lỗi (Ví dụ thiếu dấu `;`), Log sẽ báo lỗi màu đỏ kèm theo vị trí dòng bị lỗi để bạn sửa lại. Nếu thành công, mã nhị phân `.bin` sẽ được lưu trữ tự động.

### 3.5. Chấm điểm thông minh bằng AI
Thay vì phải gặp giảng viên để kiểm tra bài:
1. Nhấn nút **Chấm bằng AI** (Evaluate by AI Grader).
2. Hệ thống sẽ kết nối với các mô hình Trí tuệ Nhân tạo mạnh nhất thế giới để đọc hiểu đoạn code của bạn.
3. AI sẽ trả về:
   * **Điểm số đánh giá (0-10):** Dựa trên yêu cầu của bài thực hành.
   * **Phân tích chi tiết:** Giải thích đoạn code của bạn hoạt động thế nào, tìm ra những điểm yếu (Memory leak, code thừa).
   * **Gợi ý sửa lỗi:** Đưa ra đoạn code chuẩn xác hơn để sinh viên tham khảo.

### 3.6. Nạp Firmware (Flash) và Tương tác thiết bị (Serial)
Nếu Server được cắm sẵn thiết bị thực:
1. Bấm nút **Nạp (Flash)**.
2. Một hộp thoại hiện ra, bạn cần chọn loại Vi điều khiển (ESP32/Arduino) tương ứng với bài tập.
3. Bấm xác nhận. Thanh tiến trình sẽ chạy từ 0% đến 100% khi hệ thống đang đẩy mã nhị phân xuống phần cứng từ xa qua hàng đợi (Queue FIFO).
4. Ngay khi nạp xong, cửa sổ **Serial Monitor** mở ra. Bạn có thể xem log `Serial.print()` của thiết bị in ra, và có ô nhập lệnh để gửi ngược lại `Serial.read()` cho thiết bị (Ví dụ gửi chữ '1' để bật đèn). Độ trễ của quá trình này chỉ khoảng vài chục milliseconds nhờ công nghệ WebSockets.

---

<a name="chuong-4"></a>
## CHƯƠNG 4: HƯỚNG DẪN QUẢN TRỊ DÀNH CHO GIẢNG VIÊN

Chương này dành cho Quản trị viên (Admin) / Giảng viên có quyền cao nhất để vận hành hệ thống thực hành.

### 4.1. Bảng điều khiển quản trị (Admin Dashboard)
Khi đăng nhập bằng tài khoản Admin, bạn sẽ thấy trang tổng quan chứa:
* **Thống kê tổng quát:** Số lượng Sinh viên, Tổng số Code đã được biên dịch, Trạng thái hoạt động của Server.
* **Theo dõi Container:** Danh sách các vùng chứa Docker (Sandbox) đang hoạt động, lượng RAM và CPU mà chúng chiếm dụng.

### 4.2. Cơ chế giải phóng tài nguyên (Garbage Collection)
Hệ thống sử dụng tài nguyên giới hạn, nên không thể mở vô hạn Sandbox.
* Tính năng **Container Garbage Collector** được viết để tự động chạy ngầm.
* Quét toàn bộ hệ thống định kỳ (Ví dụ mỗi 10 phút). Nếu phát hiện một sinh viên không có thao tác lưu file hoặc tương tác nào trong vòng **2 tiếng**, hệ thống sẽ đóng gói Workspace và xóa (Kill) Container đó để thu hồi RAM. Lần sau sinh viên đăng nhập, một Container mới sẽ được cấp và khôi phục dữ liệu mã nguồn cũ.
* Admin có nút bấm tắt Container thủ công tại giao diện nếu phát hiện sinh viên có dấu hiệu lợi dụng vòng lặp vô hạn làm đầy CPU.

### 4.3. Quản lý AI Grader
* **Định cấu hình LLM (Language Model):** Tại trang cấu hình, Admin có quyền thiết lập mặc định sử dụng `Gemini 1.5 Pro` (Mạnh nhất nhưng chậm) hoặc `Groq LLaMA 3` (Siêu tốc độ nhưng phân tích ngắn hơn) cho toàn bộ sinh viên.
* **AI Fallback:** Hệ thống tự động xử lý khi có lỗi mạng từ Google, nó sẽ chuyển sang engine dự phòng Anthropic Claude một cách vô hình đối với người học. Admin có thể xem lịch sử Fallback này tại file Log.

### 4.4. Giám sát hệ thống với Prometheus / Grafana
1. Ứng dụng Flask tự động cung cấp lộ trình `/metrics`.
2. Admin cài đặt Grafana và nhập dữ liệu từ hệ thống.
3. Bảng đồ thị của Grafana sẽ thể hiện trực quan: Tần suất gọi API của toàn trường, biểu đồ tải CPU theo giờ, tỷ lệ Biên dịch thành công/Thất bại, và thời gian phản hồi (Latency) trung bình.

---

<a name="chuong-5"></a>
## CHƯƠNG 5: KIẾN TRÚC BẢO MẬT VÀ AN TOÀN HỆ THỐNG

Vì hệ thống Lab trực tuyến cho phép sinh viên chạy code C/C++ trên Server, vấn đề bảo mật được thiết kế vô cùng nghiêm ngặt (Defense in Depth).

### 5.1. Chống Spam và Giới hạn truy cập (Rate Limiting)
* Tích hợp bộ đếm giới hạn (Rate limit decorators). Sinh viên không thể dùng các tool spam click nút "Biên dịch". Giới hạn được đặt là 1 lần Biên dịch / 10 giây.
* Tính năng này giúp các hàng đợi (Queue) không bị nghẽn, và bảo vệ CPU Server không bị treo do chạy Arduino CLI hàng loạt.

### 5.2. Chống lướt thư mục (Anti-Path Traversal)
* Hàm bảo mật `safe_join()` và bộ lọc API kiểm soát hoàn toàn việc ghi file. Bất kỳ nỗ lực nào gõ đường dẫn như `../../../etc/passwd` để thoát khỏi thư mục Workspace và tấn công hệ điều hành của máy chủ đều bị vô hiệu hóa và trả về lỗi `403 Forbidden`.

### 5.3. Cách ly môi trường (Zero-Interference) và File Lockdown
* Các Container không có quyền kết nối mạng lẫn nhau.
* Các tệp tin cấu hình nhạy cảm bên trong Sandbox (như thư mục cấu hình hệ điều hành ảo) được chạy script khóa quyền (`chmod 400` / Root Owned), sinh viên chỉ có quyền tương tác trong đúng thư mục bài tập của mình.

### 5.4. Bảo vệ phiên xác thực
* Sử dụng chuẩn Cookie bảo mật cao nhất: `HttpOnly=True` (Chống đánh cắp cookie bằng Javascript - XSS) và `SameSite=Lax` (Chống tấn công giả mạo yêu cầu chéo trang - CSRF).

---

<a name="chuong-6"></a>
## CHƯƠNG 6: XỬ LÝ SỰ CỐ VÀ CÂU HỎI THƯỜNG GẶP

### 6.1. Khắc phục sự cố Server
* **Lỗi "Address already in use" khi chạy app.py:** 
  Có một tiến trình cũ đang bị treo. Khắc phục: 
  `sudo fuser -k 5000/tcp` để ép tắt cổng 5000 và khởi động lại.
* **Docker không thể phân bổ Sandbox:** 
  Ổ cứng đầy hoặc cạn kiệt RAM. Chạy lệnh: `docker system prune -a` để dọn dẹp các Image thừa mứa. Hoặc vào Admin Dashboard ấn "Dọn dẹp Container".

### 6.2. Lỗi biên dịch và phần cứng
* **Báo lỗi `avr-g++: command not found`:**
  Do chưa cấu hình thư viện bảng mạch cho Arduino CLI. Hãy chạy lệnh thiết lập môi trường: `arduino-cli core install arduino:avr`.
* **Không thấy thiết bị khi Flash:**
  Nếu nút Flash báo không có thiết bị, kiểm tra lại dây cáp vật lý. Nếu vẫn cắm, chạy quyền admin lại `sudo chmod 666 /dev/ttyUSB0` và khởi động lại Hardware Manager Service.

### 6.3. Câu hỏi thường gặp từ Sinh Viên (FAQ)
* **Q: Tại sao tôi không lưu được file .cpp?**
  A: Hệ thống định cấu hình an toàn cho phép các định dạng `.ino`, `.c`, `.cpp`, `.h`. Tên file không được chứa ký tự đặc biệt hoặc khoảng trắng. Đảm bảo tên file chỉ gồm chữ, số và dấu gạch dưới.
* **Q: Chấm bằng AI cứ báo lỗi Rate Limit?**
  A: Do khóa API miễn phí bị quá tải từ nhà cung cấp. Hãy chờ khoảng 30 giây rồi thử lại, hệ thống sẽ tự động điều hướng sang AI dự phòng.

---
*(Hết tài liệu Hướng dẫn sử dụng)*
