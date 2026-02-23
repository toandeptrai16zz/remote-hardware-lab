#!/usr/bin/python3
import requests
import sys
import os
from datetime import datetime

# THÔNG TIN CẦN KHỚP VỚI app.py
FLASK_API_URL = "http://127.0.0.1:5000/api/hardware/event"
# Secret này PHẢI GIỐNG HỆT với INTERNAL_API_SECRET trong app.py
INTERNAL_API_SECRET = 'yiehfoie9f5feifh' 

def send_event(port, event_type, vendor_id, product_id):
    payload = {
        "port": f"/dev/{port}",
        "event_type": event_type,
        "vendor_id": vendor_id,
        "product_id": product_id
    }
    headers = {
        'Content-Type': 'application/json',
        'X-Internal-Secret': INTERNAL_API_SECRET
    }
    try:
        requests.post(FLASK_API_URL, json=payload, headers=headers, timeout=5)
    except requests.exceptions.RequestException as e:
        # Ghi lỗi vào một file log riêng để debug
        with open("/tmp/udev_listener.log", "a") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"{timestamp} - Failed to send event for {port}: {e}\n")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(1)

    event_type = sys.argv[1]    # 'add' hoặc 'remove'
    device_name = sys.argv[2]   # Ví dụ: 'ttyUSB0'

    # Lấy thông tin ID của thiết bị từ môi trường udev
    vendor_id = os.getenv('ID_VENDOR_ID', 'N/A')
    product_id = os.getenv('ID_MODEL_ID', 'N/A')

    send_event(device_name, event_type, vendor_id, product_id)
