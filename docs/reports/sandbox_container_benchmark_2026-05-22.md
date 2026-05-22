# Benchmark Sandbox Container

Ngày chạy: 2026-05-22  
Máy chạy: local lab machine  
Script: `scripts/benchmarks/test_docker_time.py`  
Sandbox image: `my-dev-env:v2`  
Số vòng đo local: 20 vòng/tình huống  
Image dùng để đo pull lần đầu: `alpine:3.20`

## Kết quả đo thật

| Tình huống | TB | P95 | Ghi chú |
|---|---:|---:|---|
| Đã tồn tại, đang chạy | 0.092s | 0.103s | `docker inspect` + SSH check |
| Đã tồn tại, đã dừng | 0.122s | 0.133s | `docker start` |
| Cấp phát mới Local Cache | 0.154s | 0.162s | `docker run` từ image local |
| Cấp phát mới chưa có Image | 4.779s | - | `docker pull alpine:3.20` qua Internet |

## Câu chữ nên ghi trên slide

**Benchmark Sandbox Container**  
Đo thời gian vòng đời Docker container theo các tình huống thường gặp của sandbox sinh viên.

Nhận xét: với image sandbox đã có sẵn local, các thao tác vòng đời container đạt khoảng **0.09-0.15s**, thấp hơn mục tiêu thiết kế **< 2s**. Trường hợp chưa có image phụ thuộc tốc độ Internet; lần đo này pull `alpine:3.20` mất **4.779s**.

## Lưu ý để không bị hỏi xoáy

Không nên ghi rằng toàn bộ quá trình sinh viên đăng nhập và sẵn sàng IDE chỉ mất 0.154s. Số liệu trên đo **Docker lifecycle command-level**. Trong code production, `ensure_user_container()` còn có bước mount workspace, sinh mật khẩu container, ghi DB, chạy startup script và `time.sleep(5)` để chờ container ổn định.

Cách ghi an toàn:

> Benchmark đo riêng vòng đời Docker container. Với image sandbox đã cache local, thời gian tạo/chạy container nhỏ hơn 2 giây; phần khởi tạo đầy đủ của Web IDE còn bao gồm các bước cấu hình người dùng và chờ SSH sẵn sàng.

## File biểu đồ

`docs/reports/sandbox_container_benchmark_2026-05-22.svg`
