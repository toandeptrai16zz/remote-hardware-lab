#!/bin/bash
set -e

# Tạo host keys
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
  ssh-keygen -A
fi

USERNAME="${USERNAME:-devuser}"
PASSWORD="${PASSWORD:-password123}"

# Tạo user
if ! id -u "$USERNAME" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$USERNAME"
  echo "${USERNAME}:${PASSWORD}" | chpasswd
  usermod -aG sudo "$USERNAME" || true
  usermod -aG dialout "$USERNAME" || true
  echo "Created user: $USERNAME"
fi

# Tắt log hệ thống cho user này
touch /home/"$USERNAME"/.hushlogin
chown "$USERNAME":"$USERNAME" /home/"$USERNAME"/.hushlogin

# Thiết lập đường dẫn
echo 'export PATH="/usr/local/bin:$PATH"' >> /home/"$USERNAME"/.bashrc

# Tạo file Welcome
cat > /home/"$USERNAME"/WELCOME.txt << EOF
================================================================
HE THONG THUC HANH LAP TRINH NHUNG TU XA - EPU
================================================================
[+] TRANG THAI: DA SAN SANG (READY)

1. PHAN CUNG HO TRO: Arduino AVR, ESP8266, ESP32
2. THU VIEN: NeoPixel, DHT, PubSubClient...

[i] Go 'arduino-cli board list' de xem thiet bi.
================================================================
EOF
chown "$USERNAME":"$USERNAME" /home/"$USERNAME"/WELCOME.txt

# Tự động clear màn hình và hiện welcome khi login
if ! grep -q "cat ~/WELCOME.txt" /home/"$USERNAME"/.bashrc; then
    echo "clear" >> /home/"$USERNAME"/.bashrc
    echo "cat ~/WELCOME.txt" >> /home/"$USERNAME"/.bashrc
fi

# Setup Arduino (nếu cần)
if [ -f /usr/local/bin/setup-user-arduino.sh ]; then
    /usr/local/bin/setup-user-arduino.sh "$USERNAME"
fi

echo "System Ready!"
exec /usr/sbin/sshd -D