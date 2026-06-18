# Benchmark Smart Routing 300 Requests

Nguon so lieu: benchmark mo phong theo dung thuat toan Smart Routing hien co trong `services/arduino.py`.

- `get_user_assigned_device(username, reserve=True)` chon cong co `queue_counts` nho nhat.
- Neu nhieu cong cung nho nhat, he thong random trong nhom ung vien de chia deu tai.
- Endpoint benchmark `/api/flash` trong `routes/flash.py` gia lap thoi gian nap 3.8-4.3 giay/request va giai phong queue sau khi xong.
- Benchmark nay khong cham Docker, DB that, AI API that hoac board that; seed mo phong: `19`.

## Bang so lieu dua vao slide

| Cong USB | Requests | Ty le | TB hoan thanh |
|---|---:|---:|---:|
| `/dev/ttyUSB0` | 76 | 25.3% | 4.05s |
| `/dev/ttyUSB1` | 75 | 25.0% | 4.06s |
| `/dev/ttyUSB2` | 74 | 24.7% | 4.04s |
| `/dev/ttyUSB3` | 75 | 25.0% | 4.05s |
| Tong cong | 300 | 100% | 19.12s |

## Cau chu nen ghi tren slide

**Benchmark Smart Routing: 300 Requests**

Mo phong kiem thu 300 request tren 4 cong ESP32 `/dev/ttyUSB0..3` theo thuat toan Smart Routing cua he thong.

Nhan xet: phan phoi tai gan deu tu 24.7% den 25.3%, khong phat sinh HTTP 500 trong kich ban mo phong, va khong co hai request duoc chu dong xep cung mot cong khi cong khac co queue thap hon.

## Luu y de khong bi hoi xoay

Khong nen ghi "kiem thu thuc te tren 4 bo mach ESP32" neu thoi diem demo chi cam 1 board. Cach ghi an toan la:

> Benchmark mo phong Smart Routing 4 cong, dung de danh gia thuat toan dieu phoi tai. Kiem thu nap that tren 4 bo mach se duoc thuc hien khi co du phan cung.

Neu sau nay cam du 4 board, co the chay benchmark thu cong tu `scripts/benchmarks/heavy_load_test.py` va cap nhat lai bang nay bang so lieu that.

## File bieu do

Dung file SVG nay de chen vao slide:

`docs/reports/smart_routing_benchmark_300.svg`
