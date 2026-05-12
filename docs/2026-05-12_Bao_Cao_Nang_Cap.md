# 🚀 Đề Xuất Nâng Cấp Hệ Thống Remote Hardware Lab

Dựa trên việc rà soát kiến trúc mã nguồn hiện tại của dự án, hệ thống của bạn đã thực hiện rất tốt vai trò lõi (Core) là ảo hóa môi trường lập trình và phân luồng phần cứng. Tuy nhiên, để hệ thống thực sự vươn tầm thành một sản phẩm thương mại hoặc phục vụ cho hàng trăm sinh viên cùng lúc mà không bị sập, dưới đây là các đề xuất nâng cấp được phân loại theo từng mảng:

---

## 1. Kiến trúc & Hiệu năng (Độ ổn định khi chịu tải cao)

*   [ ] **Chuyển đổi sang Task Queue chuyên dụng (Celery + Redis)**
    *   **Hiện trạng:** Chức năng Nạp Code (Flash) và Chấm điểm AI đang sử dụng `threading.Thread` của Python.
    *   **Vấn đề:** Nếu 50 sinh viên nộp bài cùng lúc, Server sẽ tạo ra 50 luồng chạy ngầm để gọi API ChatGPT, rất dễ làm sập bộ nhớ hoặc bị OpenAI khóa API do quá giới hạn (Rate Limit).
    *   **Nâng cấp:** Sử dụng `Celery` + `Redis` để xếp hàng các tác vụ nặng. Tác vụ nào đến trước làm trước, kiểm soát được tối đa bao nhiêu tác vụ chạy song song.
*   [ ] **Cơ chế dọn dẹp Container tự động (Garbage Collection)**
    *   **Hiện trạng:** Container của sinh viên (`haquangchuong-dev`) được tạo ra và duy trì trạng thái "Running" liên tục.
    *   **Nâng cấp:** Cần viết một script chạy ngầm kiểm tra: Nếu sinh viên không có hoạt động (IDE mất kết nối) quá 2 giờ, tự động tắt (Stop) Container đó để giải phóng RAM cho Server. Khi sinh viên vào lại thì Start lại.
*   [ ] **Database Connection Pooling (Hồ bơi kết nối DB)**
    *   **Nâng cấp:** Chuyển sang sử dụng `SQLAlchemy` hoặc cấu hình Pool cho `mysql-connector` để tránh lỗi *"MySQL server has gone away"* khi ứng dụng chạy lâu ngày hoặc khi có hàng ngàn truy vấn đồng thời.

## 2. Bảo mật & An toàn Hệ thống

*   [ ] **Cấm Spam API (Rate Limiting)**
    *   **Vấn đề:** Mỗi lần ấn "Biên dịch", Server phải tạo một tiến trình gọi Docker khá tốn CPU. Nếu sinh viên dùng Auto-Click ấn liên tục, Server sẽ nghẽn CPU 100%.
    *   **Nâng cấp:** Áp dụng `Flask-Limiter`. Ví dụ: 1 user chỉ được Biên dịch tối đa 1 lần mỗi 5 giây.
*   [ ] **Xóa bỏ các khối `except: pass` tiềm ẩn rủi ro**
    *   **Vấn đề:** Vẫn còn một số đoạn code xử lý lỗi bằng cách bỏ qua (`pass`), khiến lỗi bị nuốt (Silent Error). Khi có sự cố, hệ thống không ghi log khiến việc truy vết cực kỳ khó khăn.
    *   **Nâng cấp:** Đưa `logger.error(traceback)` vào toàn bộ các khối except để lưu lịch sử lỗi vào file `.log`.

## 3. Trải nghiệm người dùng (UX/UI) & Web IDE

*   [ ] **Auto-Completion (Gợi ý code thông minh)**
    *   **Nâng cấp:** Tích hợp `Language Server Protocol (LSP)` hoặc cấu hình sâu bộ thư viện gợi ý của ACE Editor để sinh viên khi gõ `Serial.` sẽ tự xổ ra `begin()`, `println()`. Hiện tại sinh viên đang phải tự nhớ hàm 100%.
*   [ ] **Quản lý thư viện tự do (Library Manager)**
    *   **Vấn đề:** Sinh viên chỉ dùng được các thư viện mà bạn đã cài sẵn vào Docker Image.
    *   **Nâng cấp:** Tạo một giao diện UI cho phép sinh viên tìm kiếm và tự động tải các thư viện từ `arduino-cli lib install` vào môi trường riêng của họ.
*   [ ] **Live Web Server Preview (Cho ESP32/ESP8266)**
    *   **Nâng cấp:** Nếu sinh viên code một bài Web Server trên ESP32, cho phép hệ thống NAT (Forward) port 80 của ESP32 lên một đường dẫn public để sinh viên có thể xem trực tiếp giao diện Web họ vừa code ra (Ví dụ: `http://esp.domain.com/user_a`).

## 4. Bảng điều khiển Quản trị (Admin Dashboard)

*   [ ] **Giám sát Sức khỏe Phần cứng Real-time**
    *   **Nâng cấp:** Vẽ biểu đồ theo dõi Tình trạng các cổng `/dev/ttyUSB*` (đang rảnh hay đang kẹt), Hiệu suất CPU/RAM của Server hệ thống.
*   [ ] **Xuất báo cáo tự động (Export)**
    *   **Nâng cấp:** Nút tải file Excel bảng điểm toàn bộ sinh viên, có tích hợp AI tóm tắt đánh giá chung về lớp học.

---

> [!NOTE]
> **Bạn đánh giá sao về các ý tưởng trên?**
> Theo mình, ưu tiên số 1 hiện tại để hệ thống chạy ổn định khi bảo vệ đồ án là **Rate Limiting (Chống Spam Biên dịch/Nạp)** và **Auto-stop Container**. Bạn muốn mình tập trung vào tính năng nào trước?
# Báo Cáo Hoàn Tất Nâng Cấp Hệ Thống

Dựa trên sự đồng ý của bạn, mình đã triển khai xong 2 tính năng đặc biệt quan trọng giúp duy trì sự sống còn của Server khi có đông người truy cập:

## 1. 🛡️ Chống Spam API (Rate Limiting)
- **Vấn đề đã giải quyết:** Sinh viên click nút "Biên dịch" hoặc "Nạp" liên tục nhiều lần trong 1 giây sẽ khiến Server quá tải CPU vì phải sinh ra hàng chục tiến trình biên dịch song song.
- **Cách hoạt động mới:** 
  - Đã thêm bộ lọc `Rate Limiter` ngay tại Backend (`routes/user.py` & `utils/decorators.py`).
  - Nút **Biên dịch** giờ đây có thời gian chờ (Cooldown) là **10 giây** giữa các lần ấn.
  - Nút **Nạp Code (Flash)** có thời gian chờ là **15 giây**.
  - Nếu sinh viên cố tình dùng tool Auto-click để spam, API sẽ lập tức chặn lại và báo lỗi *"Hệ thống: Bạn thao tác quá nhanh..."* mà không hề làm tăng tải cho Server.

## 2. 🧹 Dọn rác Container Tự Động (Garbage Collection)
- **Vấn đề đã giải quyết:** Docker Container của sinh viên trước đây cứ chạy mãi mãi (Running 24/7), dẫn đến hiện tượng rò rỉ RAM (Memory Leak) nếu có 100 sinh viên từng đăng nhập vào hệ thống.
- **Cách hoạt động mới:**
  - Mình đã viết một luồng chạy ngầm (`GC Worker`) bên trong `services/docker_manager.py`.
  - Bất cứ khi nào sinh viên thao tác trên Web IDE (Lưu bài, gõ phím, mở file), bộ đếm thời gian sẽ được reset.
  - Cứ mỗi 10 phút, luồng ngầm này sẽ quét toàn bộ các user. Nếu phát hiện user nào "bất động" hoặc đã tắt trình duyệt quá **2 tiếng (7200 giây)**, hệ thống sẽ **tự động Stop Container** của người đó để trả lại hàng chục MB RAM cho máy chủ.
  - Lần tới khi sinh viên đó đăng nhập lại, Container sẽ tự động Start lại chỉ mất 1-2 giây.

---
> [!TIP]
> **Cách kiểm tra:**
> 1. Bạn hãy vào IDE, nhấn nút **Biên dịch** liên tiếp 2-3 lần thật nhanh. Bạn sẽ thấy thông báo cấm spam màu đỏ hiện lên ở góc phải màn hình!
> 2. Tính năng tự động tắt Container thì nó sẽ tự chạy ngầm, bạn có thể kiểm tra Log của Server sau 2 tiếng để thấy dòng chữ `[GC] Auto-stopped inactive container...` hiện lên nhé.
