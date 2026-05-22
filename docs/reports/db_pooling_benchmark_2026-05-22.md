# Benchmark Database Connection Pooling

Ngay chay: 2026-05-22  
Script: `scripts/benchmarks/test_db_pooling.py`  
Truy van: `SELECT 1`  
So phien dong thoi: 30  
Pool size production: 15

Benchmark chi doc `SELECT 1`, khong sua schema va khong ghi du lieu.

## Ket qua do that

| Chi so | Khong Pool | Co Pool | Cai thien |
|---|---:|---:|---:|
| Request trung binh | 22.1ms | 10.2ms | Nhanh gap 2.2 lan |
| Request P95 | 34.9ms | 14.1ms | Giam 59.6% do tre |
| Error Rate | 0.0% | 0.0% | On dinh |
| Mau thanh cong | 30/30 | 30/30 | 30 phien dong thoi |

## Cau chu nen ghi tren slide

**Benchmark Database Connection Pooling**

So sanh tao ket noi moi va su dung MySQL Connection Pool `pool_size=15` voi 30 phien giao dich dong thoi.

Nhan xet: Connection Pooling giup giam overhead tao ket noi MySQL. Trong lan do thuc te nay, latency trung binh giam tu **22.1ms xuong 10.2ms**, P95 giam tu **34.9ms xuong 14.1ms**, va khong phat sinh loi ket noi.

## Luu y de khong bi hoi xoay

Khong nen dung bang cu `34.7ms -> 0.7ms` neu noi la **30 phien dong thoi**. Bang cu co kha nang la do theo kieu tuan tu/acquisition-only. So moi nay do request day du hon: lay connection, chay `SELECT 1`, fetch ket qua va dong connection.

## File bieu do

`docs/reports/db_pooling_benchmark_2026-05-22.svg`
