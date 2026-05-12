# File: set_password.py
import mysql.connector
from werkzeug.security import generate_password_hash

# --- BẠN CÓ THỂ THAY ĐỔI MẬT KHẨU MỚI Ở ĐÂY ---
NEW_PASSWORD = "Chuong2004"
TARGET_USERNAME = "admin"
# -----------------------------------------

try:
    print(f"🔄 Đang kết nối đến database...")
    db = mysql.connector.connect(
        host="localhost",
        user="chuongdev_admin",
        password="Chuong2004@", # Thay đổi nếu mật khẩu DB của bạn khác
        database="flask_app"
    )
    cur = db.cursor()

    print(f" Đang mã hóa mật khẩu mới...")
    hashed_password = generate_password_hash(NEW_PASSWORD)

    print(f"🆙 Đang cập nhật mật khẩu cho user '{TARGET_USERNAME}'...")
    cur.execute(
        "UPDATE users SET password = %s WHERE username = %s",
        (hashed_password, TARGET_USERNAME)
    )
    db.commit()

    if cur.rowcount > 0:
        print(f"\n✅ Đã đặt lại mật khẩu cho '{TARGET_USERNAME}' thành công!")
        print(f"   => Mật khẩu mới là: {NEW_PASSWORD}")
    else:
        print(f"\n❌ Không tìm thấy user '{TARGET_USERNAME}' để cập nhật.")

    cur.close()
    db.close()

except Exception as e:
    print(f"\n Gặp lỗi: {e}")
