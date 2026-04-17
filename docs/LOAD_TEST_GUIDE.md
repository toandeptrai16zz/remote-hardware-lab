# HƯỚNG DẪN KIỂM THỬ TẢI & GIÁM SÁT HỆ THỐNG (NCKH EPU TECH) 🚀📊

Tài liệu này hướng dẫn cách vận hành hệ thống giám sát Prometheus/Grafana và thực hiện kịch bản kiểm thử tải (Load Test) thực tế 300 sinh viên để lấy số liệu cho Chương III của báo cáo.

## 1. Hệ thống Giám sát (Monitoring Stack) 📈

Hệ thống sử dụng bộ đôi Prometheus & Grafana để theo dõi sức khỏe và tải lượng của IoT Lab.

- **Prometheus**: Thu thập các chỉ số (metrics) từ Backend Flask.
- **Grafana**: Trực quan hóa dữ liệu qua Dashboard "EPU Tech IoT Lab Monitoring".

### Các chỉ số quan trọng:
- **Active Containers**: Tổng số sinh viên thực tế đang mở IDE (được quét tự động từ Docker Daemon mỗi 10 giây).
- **Flash Queue Depth**: Độ sâu hàng đợi nạp code trên từng cổng USB vật lý.
- **USB Device Status**: Trạng thái cổng (Xanh = Sẵn sàng, Cam = Đang nạp code).
- **Phân bổ tải**: Biểu đồ Bar Gauge thể hiện sự công bằng của thuật toán Smart Routing.

---

## 2. Kịch bản Kiểm thử Tải (The "Zerg Rush" 300 Test) 💣

Đây là kịch bản dội bom 300 requests đồng thời để chứng minh hệ thống không bị nghẽn (bottleneck).

### Cơ chế hoạt động:
1. Script `tests/heavy_load_test.py` khởi tạo 300 luồng (threads) sinh viên.
2. Mỗi luồng gửi 1 HTTP POST đến `/api/flash`.
3. Backend gọi thuật toán **Smart Routing** để chọn cổng USB vắng nhất (dựa trên `queue_counts`).
4. Backend giả lập thời gian nạp code vật lý (~4 giây) và giữ khóa (Lock) cổng đó.

### Cách thực hiện:
Mở Terminal và chạy lệnh:
```bash
python3 tests/heavy_load_test.py
```

---

## 3. Thuật toán Smart Routing (Linh hồn của Đề tài) 🧠

Thuật toán đảm nhận việc phân phối yêu cầu nạp code vào cổng USB rảnh nhất. 

- **Logic**: Khi có request, hệ thống quét bảng `device_assignments` của User đó, tìm các cổng đang có `queue_counts` thấp nhất và thực hiện gán (Reserve).
- **Kết quả**: 300 requests được chia đều 75/75/75/75 cho 4 cổng USB, đảm bảo thời gian chờ của mỗi sinh viên là thấp nhất.

---

## 4. Reset & Dọn dẹp Dữ liệu 🧹

Sau khi kết thúc demo, các chỉ số sẽ tự động về 0 khi các requests hoàn tất. Nếu muốn reset thủ công để Dashboard "phẳng lặng" cho lần demo tiếp theo, đại ca có thể khởi động lại Server:

```bash
pkill -f app.py
nohup ./venv/bin/python3 app.py > logs/app_boot.log 2>&1 &
```

---
**Hệ thống được thiết kế và vận hành bởi Chương - EPU Tech 2026**
