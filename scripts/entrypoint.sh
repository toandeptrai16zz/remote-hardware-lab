#!/bin/bash
set -e

# Tạo host keys nếu chưa có
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
  ssh-keygen -A
fi

USERNAME="${USERNAME:-devuser}"
PASSWORD="${PASSWORD:-password123}"

# 1. Tạo user nếu chưa tồn tại
if ! id -u "$USERNAME" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$USERNAME"
  echo "${USERNAME}:${PASSWORD}" | chpasswd
  usermod -aG sudo "$USERNAME" || true
  usermod -aG dialout "$USERNAME" || true
  echo "Created user: $USERNAME"
fi

# 2. Tắt thông báo login của hệ thống (System MOTD)
touch /home/"$USERNAME"/.hushlogin
chown "$USERNAME":"$USERNAME" /home/"$USERNAME"/.hushlogin

# 3. Cấu hình đường dẫn
if ! grep -q "export PATH=\"/usr/local/bin:\$PATH\"" /home/"$USERNAME"/.bashrc; then
    echo 'export PATH="/usr/local/bin:$PATH"' >> /home/"$USERNAME"/.bashrc
fi

# 4. Tạo nội dung file Welcome (Ghi đè để cập nhật nội dung mới nhất)
# cat > /home/"$USERNAME"/WELCOME.txt << EOF
# ================================================================
# HE THONG THUC HANH LAP TRINH NHUNG TU XA - EPU
# ================================================================
# [+] TRANG THAI: DA SAN SANG (READY)

# 1. PHAN CUNG HO TRO: Arduino AVR, ESP8266, ESP32
# 2. THU VIEN: NeoPixel, DHT, PubSubClient...

# [i] Go 'arduino-cli board list' de xem thiet bi.
# ================================================================
# EOF
# chown "$USERNAME":"$USERNAME" /home/"$USERNAME"/WELCOME.txt

# =========================================================
# 5. FIX LỖI 2 WELCOME (QUAN TRỌNG)
# Logic: Xóa dòng lệnh cũ đi trước khi thêm mới
# =========================================================
sed -i '/cat ~\/WELCOME.txt/d' /home/"$USERNAME"/.bashrc
sed -i '/^clear$/d' /home/"$USERNAME"/.bashrc

# Thêm lại (Chỉ 1 lần duy nhất)
echo "clear" >> /home/"$USERNAME"/.bashrc
echo "cat ~/WELCOME.txt" >> /home/"$USERNAME"/.bashrc

# Khởi động SSH
exec /usr/sbin/sshd -D