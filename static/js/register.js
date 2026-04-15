const form = document.querySelector('form');
    const passwordInput = document.querySelector('input[name="password"]');
    const confirmInput = document.querySelector('input[name="confirm_password"]');
    const errorDiv = document.getElementById('passwordError');

    form.addEventListener('submit', function(event) {
        // Nếu hai mật khẩu không khớp
        if (passwordInput.value !== confirmInput.value) {
            // Ngăn form gửi đi
            event.preventDefault(); 
            
            // Hiển thị thông báo lỗi trong thẻ div
            errorDiv.textContent = 'Mật khẩu và xác nhận mật khẩu không khớp!';
            errorDiv.style.display = 'block';
        } else {
            // Nếu khớp thì ẩn thông báo đi
            errorDiv.style.display = 'none';
        }
    });

