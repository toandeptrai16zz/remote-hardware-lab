#!/usr/bin/env python3
import sys
import os
sys.path.append(os.getcwd())

import threading
import requests
import time
import random
from collections import defaultdict

# Cấu hình thống kê - by Chương
results = defaultdict(list)
port_distribution = defaultdict(int)
stats_lock = threading.Lock()

def simulate_real_student(student_id, board_type):
    """Client không biết gì về cổng USB cả, chỉ ném code lên Server"""
    payload = {"board_type": board_type, "code": "void setup(){ Serial.begin(115200); }"}
    try:
        start_time = time.time()
        # Bắn thẳng vào API nạp code thật của Backend
        res = requests.post("http://127.0.0.1:5000/api/flash", json=payload, timeout=60)
        duration = time.time() - start_time
        
        if res.status_code == 200:
            data = res.json()
            port = data.get('port', 'Unknown')
            with stats_lock:
                results[port].append(duration)
                port_distribution[port] += 1
            print(f"[{student_id:03d}] OK -> {port} ({duration:.2f}s)")
        else:
            print(f"[{student_id:03d}] Lỗi: {res.status_code} - {res.text}")
            
    except Exception as e:
        print(f"[{student_id:03d}] Nghẽn mạng: {e}")

print("="*80)
print("🚀 KHỞI CHẠY KỊCH BẢN KIỂM THỬ TẢI THỰC TẾ: 300 SINH VIÊN TRUY CẬP ĐỒNG THỜI")
print("="*80)

start_all = time.time()
threads = []
for i in range(1, 301):
    t = threading.Thread(target=simulate_real_student, args=(i, "ESP32"))
    threads.append(t)
    t.start()
    time.sleep(0.05) # Dãn cách 0.05s để Server 'thở' kịp - by Chương

for t in threads:
    t.join()

total_duration = time.time() - start_all

print("\n" + "="*80)
print("📊 BẢNG 3.2: KẾT QUẢ PHÂN PHỐI TẢI VỚI 300 REQUESTS (REAL BACKEND)")
print("="*80)
print(f"{'Cổng USB':<15} | {'Số requests':<15} | {'Tỷ lệ (%)':<10} | {'Thời gian TB':<15}")
print("-" * 70)

total_reqs = sum(port_distribution.values())
for port in sorted(port_distribution.keys()):
    count = port_distribution[port]
    avg_latency = sum(results[port]) / len(results[port]) if results[port] else 0
    print(f"{port:<15} | {count:<15} | {count/total_reqs*100:>8.1f}% | {avg_latency:>13.2f}s")

print("-" * 70)
print(f"{'Tổng cộng':<15} | {total_reqs:<15} | {'100%':>10} | {total_duration/total_reqs if total_reqs else 0:>13.2f}s")
print(f"\n✅ Hoàn tất kiểm thử trong {total_duration:.2f} giây.")
print("="*80)
