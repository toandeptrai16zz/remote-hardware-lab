# Mục 3: Xây dựng Giao diện Người Dùng (Web IDE)

## 1. Socket.IO & Xterm.js Terminal
Kiến trúc Event-Driven được sử dụng thông qua WebSocket (Socket.IO). Terminal xterm.js chạy ngay trên giao diện sinh viên, kết nối SSH thẳng và an toàn tuyệt đối với Cấu trúc Container kín của Docker.

## 2. Soạn thảo mã nhúng (Editor)
HTML Formats được cải tiến. Nút "Compile & Upload" gửi thẳng mã nhúng C++ (.ino) vào API Backend, trả ngược thông báo (Log) biên dịch C chéo (Cross-compiler) về Web ngay lập tức.

## 3. Trải nghiệm Tương tác thực (UX)
Thiết kế luồng thao tác không cần F5 (Reload). Notification gửi Event từ máy chủ cảnh báo "Đã nhận Bài" hay "Đang cấp Thiết bị USB".
