# Báo cáo phát triển đơn giản: Monitoring Grafana cho EPU Tech IoT Lab

Ngày cập nhật: 2026-05-22

## 1. Mục tiêu

Mục tiêu của phần monitoring là bổ sung khả năng quan sát trạng thái vận hành của hệ thống EPU Tech IoT Lab trong quá trình sinh viên sử dụng Web IDE, Docker container và board phần cứng thật.

Monitoring không thay thế chức năng Admin Dashboard hiện có, mà đóng vai trò lớp quan sát kỹ thuật để admin hoặc người vận hành nắm được hệ thống có đang quá tải, nghẽn hàng đợi nạp code, hoặc mất kết nối thiết bị USB hay không.

## 2. Thành phần đã cấu hình

Hệ thống hiện đã có endpoint `/metrics` trong Flask app thông qua:

- `prometheus_client`
- `prometheus-flask-exporter`
- `make_wsgi_app()` gắn vào route `/metrics`
- File chính liên quan: `utils/metrics.py`, `app.py`

Các container monitoring đã chạy thử local:

- Prometheus: `http://127.0.0.1:9090`
- Grafana: `http://127.0.0.1:3000`
- Dashboard: `EPU Tech IoT Lab Monitoring`
- Dashboard URL: `http://127.0.0.1:3000/d/epu-iot-lab-monitoring/epu-tech-iot-lab-monitoring`

Tài khoản Grafana local demo:

- Username: `admin`
- Password: `Toan2004`

Lưu ý: mật khẩu trên chỉ dùng cho demo cục bộ. Khi đưa lên server thật hoặc public repository cần thay bằng biến môi trường/secret riêng.

## 3. Metric đang có trong codebase

Các metric riêng của hệ thống:

- `active_containers_total`: số lượng container user đang chạy.
- `flash_queue_depth{port=...}`: độ sâu hàng đợi nạp code theo từng cổng USB.
- `usb_device_status{port=...}`: trạng thái cổng USB.

Mã hóa trạng thái USB:

- `0`: Offline
- `1`: Available
- `2`: In Use

Ngoài ra, `prometheus-flask-exporter` tự động bổ sung các metric HTTP cho Flask API, trong đó có thể dùng để tính độ trễ P95.

## 4. Dashboard Grafana

Dashboard hiện có các panel chính:

- Container đang chạy.
- Cổng USB đang nhận.
- Board đang `In Use`.
- Tổng queue flash.
- P95 API hiện tại.
- Độ sâu hàng đợi nạp code theo từng port.
- Bảng trạng thái thiết bị USB.
- Độ trễ API P95 theo thời gian.
- Phân bổ tải giữa các cổng.
- Tổng quan Flask API, board available/offline và nguồn dữ liệu.

Prometheus đang scrape Flask `/metrics` với chu kỳ 10 giây trong cấu hình local demo.

Metric USB đã được chỉnh để dashboard phản ánh trạng thái thực tế hơn:

- Mặc định port là `Offline`.
- Khi admin scan thấy port vật lý, port được chuyển sang `Available`.
- Khi upload code thật, port được chuyển sang `In Use`.
- Khi upload kết thúc, port quay lại `Available`.

## 5. Lợi ích thực tế

Phần monitoring này có ích ở các điểm sau:

- Biết được hiện có bao nhiêu sandbox container đang chạy.
- Quan sát cổng USB nào đang rảnh, đang dùng hoặc offline.
- Phát hiện nghẽn hàng đợi nạp code khi nhiều sinh viên cùng dùng board.
- Kiểm tra thuật toán Smart Routing có phân bổ tải đều giữa các cổng hay không.
- Theo dõi độ trễ API P95 để phát hiện backend chậm hoặc quá tải.
- Hỗ trợ debug khi sinh viên báo lỗi không nạp được code hoặc không thấy board.

## 6. Vì sao chưa tích hợp trực tiếp vào Admin Dashboard

Hiện tại Grafana đang hoạt động như một hệ giám sát độc lập. Admin Dashboard trong Flask chỉ hiển thị thống kê/log cơ bản, còn Grafana chuyên cho biểu đồ thời gian thực và truy vấn metric.

Có ba hướng tích hợp:

1. Thêm nút `Monitoring` trong Admin Dashboard để mở Grafana dashboard ở tab mới.
2. Tạo trang `/admin/monitoring` và nhúng Grafana bằng iframe.
3. Flask gọi Prometheus API rồi tự render chart trong admin.

Hướng khuyến nghị là hướng 1 hoặc 2. Cách này tận dụng Grafana, ít code hơn và dễ mở rộng dashboard.

## 7. Trạng thái hiện tại

Đã chạy thử local:

- Flask app mở được `/metrics`.
- Prometheus target ở trạng thái `up`.
- Grafana load được dashboard đã provision sẵn trong repo.

Chưa phải production deployment:

- Chưa deploy trên server thật.
- Chưa cấu hình domain/HTTPS.
- Chưa cấu hình quyền truy cập production.
- Chưa nhúng chính thức vào Admin Dashboard.

## 8. Hướng phát triển tiếp

Các việc nên làm tiếp:

- Thêm link `Monitoring` trong menu Admin.
- Nếu nhúng iframe, cấu hình Grafana `GF_SECURITY_ALLOW_EMBEDDING=true`.
- Chuyển password Grafana sang biến môi trường hoặc secret.
- Cập nhật Prometheus target theo IP/domain server thật.
- Bổ sung panel theo user/container cụ thể.
- Bổ sung cảnh báo khi queue quá sâu hoặc thiết bị USB offline.

## 9. Kết luận

Monitoring bằng Prometheus và Grafana là phần bổ sung có giá trị cho EPU Tech IoT Lab. Nó giúp hệ thống không chỉ chạy được mà còn quan sát được tình trạng vận hành, đặc biệt trong các kịch bản có nhiều sinh viên dùng container và board thật cùng lúc.

Trong báo cáo NCKH nên trình bày phần này là: đã cấu hình và chạy thử local dashboard monitoring; production monitoring và tích hợp sâu vào Admin Dashboard là hướng phát triển khi có hạ tầng server thật.
