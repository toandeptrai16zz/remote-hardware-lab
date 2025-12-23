    #!/bin/bash
    
    # Chuyển tất cả output (stdout và stderr) của script Python vào file log
    # Điều này sẽ bắt được cả lỗi cú pháp như IndentationError
    (
        echo "--- UDEV EVENT at $(date) ---"
        # In các biến môi trường mà udev cung cấp
        env
        echo "--- Running Python Script ---"
        # Chạy script python
        /usr/bin/python3 /home/toan/flask-kerberos-demo/udev_listener.py
    ) >> /tmp/udev_wrapper.log 2>&1 &
    
