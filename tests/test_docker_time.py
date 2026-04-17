#!/usr/bin/env python3
import sys
import os
sys.path.append(os.getcwd())

import subprocess
import time
import os

# Cấu hình - by Chương
IMAGE_NAME = "my-dev-env:v2"
TEST_CONTAINER = "test_time_benchmark"
PULL_IMAGE = "alpine:latest" # Dùng image nhẹ để test KB4 cho an toàn

def run_cmd(cmd):
    start = time.time()
    subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return time.time() - start

print("="*70)
print("⏳ HỆ THỐNG ĐO LƯỜNG HIỆU NĂNG CONTAINER REAL-TIME (EPU TECH)")
print("="*70)

# Dọn dẹp trước khi test
subprocess.run(f"docker rm -f {TEST_CONTAINER}", shell=True, stderr=subprocess.DEVNULL)

# 1. Đo Kịch bản 1: Đã tồn tại & Đang chạy (Chỉ lấy info)
print("\n[KB1] Container đang chạy (docker inspect)...")
subprocess.run(f"docker run -d --name {TEST_CONTAINER} {IMAGE_NAME} sleep 3600", shell=True, stdout=subprocess.DEVNULL)
time_kb1 = run_cmd(f"docker inspect {TEST_CONTAINER}")
print(f"👉 Kết quả KB1: {time_kb1:.3f} giây")

# 2. Đo Kịch bản 2: Container đã dừng (Cold-start)
print("\n[KB2] Khởi động container đã dừng (docker start)...")
subprocess.run(f"docker stop {TEST_CONTAINER}", shell=True, stdout=subprocess.DEVNULL) 
time_kb2 = run_cmd(f"docker start {TEST_CONTAINER}")
print(f"👉 Kết quả KB2: {time_kb2:.3f} giây")

# 3. Đo Kịch bản 3: Tạo mới container từ Local Cache (docker run)
print("\n[KB3] Tạo mới container từ Local Cache (docker run)...")
subprocess.run(f"docker rm -f {TEST_CONTAINER}", shell=True, stderr=subprocess.DEVNULL)
time_kb3 = run_cmd(f"docker run -d --name {TEST_CONTAINER} {IMAGE_NAME} sleep 3600")
print(f"👉 Kết quả KB3: {time_kb3:.3f} giây")

# 4. Đo Kịch bản 4: Pull Image từ Internet (Lần đầu)
print("\n[KB4] Pull Image mới hoàn toàn từ Internet (docker pull)...")
# Xóa image pull cũ nếu có
subprocess.run(f"docker rmi {PULL_IMAGE}", shell=True, stderr=subprocess.DEVNULL)
time_kb4 = run_cmd(f"docker pull {PULL_IMAGE}")
print(f"👉 Kết quả KB4: {time_kb4:.3f} giây")

# Dọn dẹp cuối cùng
subprocess.run(f"docker rm -f {TEST_CONTAINER}", shell=True, stderr=subprocess.DEVNULL)

print("\n" + "="*70)
print("📊 TỔNG HỢP SỐ LIỆU CHO BẢNG 3.4")
print("="*70)
print(f"| Tình huống                          | Thời gian (s) | Ghi chú                    |")
print(f"|--------------------------------------|---------------|---------------------------|")
print(f"| [KB1] Đang chạy (Inspect)            | {time_kb1:13.3f} | Lấy thông tin kết nối     |")
print(f"| [KB2] Cold-start (Start)             | {time_kb2:13.3f} | Container đã tồn tại      |")
print(f"| [KB3] Cấp phát mới (Local Cache)     | {time_kb3:13.3f} | Pull từ cache + Startup   |")
print(f"| [KB4] Pull từ Internet               | {time_kb4:13.3f} | Chỉ xảy ra lần đầu        |")
print("="*70)
print("✅ HOÀN TẤT! ĐẠI CA CHƯƠNG LẤY SỐ NÀY ĐIỀN VÀO BÁO CÁO NHÉ!")
