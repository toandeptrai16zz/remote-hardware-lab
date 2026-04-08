# Mục 2: Xây dựng Các Dịch Vụ Backend Lõi

## 1. Dịch vụ Điều phối Container
Dịch vụ cốt lõi nằm ở nhánh `services/` cho phép máy chủ Flask giao tiếp với Docker Socket. Khi học viên mở tab, một Hộp cát (Sandbox) Container sẽ được cấp quyền root độc lập.

## 2. Hệ thống Xác Thực Cốt Lõi
Hệ thống cấp quyền theo Roles Authentication. Xác thực phiên làm việc được củng cố bằng phương thức Kerberos bảo vệ chặt chẽ kết nối SSH.

## 3. Tài liệu API Endpoints
Do tính chất phức tạp của hệ thống giao tiếp chéo giữa USB C - Docker - Flask, toàn bộ APIs đã được vạch ra tại phân hệ cốt lõi. (Vui lòng xem file `docs/API_ENDPOINTS.md` chi tiết).
