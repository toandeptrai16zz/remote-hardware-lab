#!/bin/bash
set -e

# Tạo host keys nếu chưa có
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
  ssh-keygen -A
fi

USERNAME="${USERNAME:-devuser}"
PASSWORD="${PASSWORD:-password123}"

# Tạo user nếu chưa tồn tại
if ! id -u "$USERNAME" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$USERNAME"
  echo "${USERNAME}:${PASSWORD}" | chpasswd
  usermod -aG sudo "$USERNAME" || true
  usermod -aG dialout "$USERNAME" || true
  
  echo "Created user: $USERNAME"
fi

# ===== THIẾT LẬP PATH CHO USER =====
echo 'export PATH="/usr/local/bin:$PATH"' >> /home/"$USERNAME"/.bashrc
echo 'export PATH="/usr/local/bin:$PATH"' >> /home/"$USERNAME"/.profile

# Tạo symlink arduino-cli
ln -sf /usr/local/bin/arduino-cli /usr/bin/arduino-cli

# ===== SETUP ARDUINO ENVIRONMENT NGAY LẬP TỨC =====
echo "Setting up Arduino environment for $USERNAME..."

# Sử dụng script setup nhanh
/usr/local/bin/setup-user-arduino.sh "$USERNAME"

# Đảm bảo ownership
chown -R "$USERNAME":"$USERNAME" /home/"$USERNAME" || true

# ===== TẠO WELCOME MESSAGE CHO USER =====
cat > /home/"$USERNAME"/WELCOME.txt << EOF
=== Arduino Development Environment - READY TO USE ===

🎉 Your Arduino environment is FULLY CONFIGURED and ready!

✅ Pre-installed Cores:
   - arduino:avr (Arduino Uno, Nano, etc.)
   - esp8266:esp8266 (NodeMCU, Wemos D1, etc.)
   - esp32:esp32 (ESP32 DevKit, etc.) [if installation succeeded]

✅ Pre-installed Libraries:
   - Adafruit NeoPixel
   - DHT sensor library
   - Adafruit Unified Sensor
   - PubSubClient (MQTT)
   - ArduinoJson

🔧 Quick Commands:
   ./check-arduino.sh          - Check installation status
   arduino-cli board list      - List connected boards
   arduino-cli sketch new MyProject - Create new project
   arduino-cli compile --fqbn arduino:avr:uno MyProject
   arduino-cli upload -p /dev/ttyUSB0 --fqbn arduino:avr:uno MyProject

📁 Your workspace is ready at: /home/$USERNAME
🚀 Start coding immediately - no setup required!

Happy coding! 🚀
EOF

chown "$USERNAME":"$USERNAME" /home/"$USERNAME"/WELCOME.txt

# ===== VERIFICATION LOG =====
echo "=== CONTAINER SETUP COMPLETE ==="
echo "User: $USERNAME (ready to use)"
echo "Arduino Cores: $(su - "$USERNAME" -c 'arduino-cli core list | wc -l') installed"
echo "Arduino Libraries: $(su - "$USERNAME" -c 'arduino-cli lib list | wc -l') installed"
echo "SSH: Available on port 22"
echo "Ready for immediate development!"

# Chạy sshd foreground
exec /usr/sbin/sshd -D