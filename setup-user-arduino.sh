#!/bin/bash
# Script này sẽ được chạy bên trong container để cấu hình Arduino CLI cho user mới

set -e

USERNAME=$1

echo "--- Bat dau cau hinh Arduino cho user: $USERNAME ---"

# Chạy các lệnh với quyền của user được tạo ra
sudo -u $USERNAME arduino-cli config init
sudo -u $USERNAME arduino-cli core update-index
sudo -u $USERNAME arduino-cli core install arduino:avr
sudo -u $USERNAME arduino-cli core install esp8266:esp8266
sudo -u $USERNAME arduino-cli core install esp32:esp32

echo "--- Cau hinh Arduino cho user $USERNAME hoan tat! ---"
