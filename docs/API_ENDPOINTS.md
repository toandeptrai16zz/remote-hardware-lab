# Tài liệu API Endpoints
*Dự án: EPU IoT Lab Platform*

Tài liệu thiết kế danh sách các luồng Web API (REST) cốt lõi của máy chủ.

## 1. Authentication (`/auth`)
Phụ trách tiếp nhận Session thông qua giao thức Kerberos và Session Token.

- `GET /auth/login`: Trả về giao diện đăng nhập.
- `POST /auth/login`: Payload `FormData {username, password}`. Trả về Session cookie.
- `GET /auth/logout`: Xóa session, kích hoạt sự kiện dọn dẹp Container rác.

## 2. Dịch vụ Lập Trình Viên (`/user`)
Dịch vụ Web IDE và quản lý lớp học.

- `GET /user/IDE`: Routing vào giao diện Workspace hiển thị Cây thư mục và Socket.IO terminal.
- `GET /user/api/my-missions`: API trả về mảng `JSON` chứa các bài thi (`missions`) sinh viên đang được giao.
- `POST /user/api/submit`: Nộp file code. Kích hoạt Backend AI Grader chấm điểm.
- `GET /user/api/poll_grade`: Endpoint lấy điểm sau khi Background Job (AI) thực thi xong.

## 3. Dịch vụ Quản Trị Hệ Thống (`/admin`)
*Yêu cầu Auth Token có `role="admin"`*.

- `GET /admin/dashboard`: View chính quản lý thiết bị và Hardware.
- `POST /admin/api/missions/create`: Tạo bài tập mới. 
- `PUT /admin/api/missions/edit`: Chỉnh sửa luật thi.
- `DELETE /admin/api/missions/<id>`: Xóa bài thi (Cascade DB).
- `GET /admin/api/export`: Gọi service Pandas xuất file `.xlsx`.

## 4. Giao tiếp Thời gian thực Socket.IO (Hardware & Terminal)
Sử dụng giao thức WebSocket `ws://` tích hợp vào Flask.

- `Event: terminal_input`: Frontend gửi mã ASCII phím bấm -> Backend đẩy mã phím vào Standard Input (stdin) của Docker Sandbox Container.
- `Event: compile_sketch`: Frontend gửi Payload gọi `arduino-cli compile` chạy ngầm.
- `Event: upload_sketch`: Backend gửi tín hiệu Upload file HEX xuống USB (do C-Backend `udev_listener` giám sát ở `/dev/ttyUSB*`). Trả về Log Upload theo thời gian thực.
