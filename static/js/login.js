document.addEventListener("DOMContentLoaded", () => {
            createParticles();
            fetchAndSetCSRFToken();
            refreshCaptcha();
            document.getElementById("password").addEventListener("input", updatePasswordStrengthUI);
            document.getElementById("loginForm").addEventListener("submit", submitLogin);
            setupOtpInputs();
        });

        // 2. HÀM HIỂN THỊ THÔNG BÁO TOAST (THAY CHO SHOWALERT CŨ)
        function showToast(message, type = 'success') {
            const container = document.getElementById('js-flash-container');
            const notification = document.createElement('div');
            
            // Dùng class bootstrap 'alert' kết hợp style inline
            notification.className = `alert alert-${type} shadow-lg`; 
            notification.style.marginBottom = '10px';
            notification.style.minWidth = '280px';
            notification.style.borderLeft = type === 'success' ? '5px solid #00d4aa' : '5px solid #ff6b6b';
            notification.style.color = '#000'; // Chữ màu đen cho dễ đọc trên nền alert sáng
            notification.style.fontWeight = '500';
            
            // Icon tương ứng
            const icon = type === 'danger' ? 'exclamation-circle' : 'check-circle';
            notification.innerHTML = `<i class="fas fa-${icon} me-2"></i> ${message}`;

            container.appendChild(notification);

            // Tự tắt sau 3 giây
            setTimeout(() => {
                notification.style.transition = "opacity 0.5s ease";
                notification.style.opacity = "0";
                setTimeout(() => {
                    notification.remove();
                }, 500);
            }, 3000);
        }

        // --- CÁC LOGIC KHÁC GIỮ NGUYÊN, CHỈ ĐỔI TÊN HÀM GỌI ---

        function createParticles() {
            const container = document.getElementById("particles");
            for (let i = 0; i < 30; i++) {
                const p = document.createElement("div");
                p.className = "particle";
                p.style.left = `${Math.random() * 100}%`;
                p.style.animationDelay = `${Math.random() * 15}s`;
                p.style.animationDuration = `${Math.random() * 10 + 10}s`;
                container.appendChild(p);
            }
        }

        async function fetchAndSetCSRFToken() {
            try {
                const res = await fetch('/api/generate-csrf');
                if (!res.ok) throw new Error('Network response was not ok');
                const data = await res.json();
                document.getElementById("csrfToken").value = data.csrf_token;
            } catch (error) {
                showToast("Không thể lấy token bảo mật. Vui lòng tải lại trang.", "danger");
            }
        }

        let captchaAnswer = "";
        function refreshCaptcha() {
            const chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghjklmnpqrstuvwxyz23456789";
            let captcha = "";
            for (let i = 0; i < 6; i++) captcha += chars.charAt(Math.floor(Math.random() * chars.length));
            captchaAnswer = captcha;
            document.getElementById("captchaCode").textContent = captcha;
            document.getElementById("captchaToken").value = btoa(captcha + ":" + Date.now());
        }

        function togglePassword() {
            const p = document.getElementById("password"), i = document.getElementById("password-icon");
            p.type = p.type === 'password' ? 'text' : 'password';
            i.classList.toggle('fa-eye'); i.classList.toggle('fa-eye-slash');
        }

        function updatePasswordStrengthUI() {
            const v = this.value, s = document.getElementById("passwordStrength"), str = v.length > 0 ? (v.length > 12 ? 3 : (v.length > 8 ? 2 : 1)) : 0;
            s.className = "password-strength";
            if (str === 1) s.classList.add("strength-weak");
            else if (str === 2) s.classList.add("strength-medium");
            else if (str === 3) s.classList.add("strength-strong");
        }

        async function submitLogin(e) {
            e.preventDefault();
            const btn = document.getElementById('loginBtn'), spinner = document.getElementById('loadingSpinner');
            btn.disabled = true; spinner.style.display = 'inline-block';

            try {
                const res = await fetch('/api/login', { method: 'POST', body: new FormData(this) });
                const result = await res.json();
                if (result.success) {
                    if (result.requireOTP) {
                        document.getElementById('loginContainer').style.display = 'none';
                        document.getElementById('otpContainer').style.display = 'block';
                        startResendTimer();
                        showToast('Vui lòng nhập mã OTP đã gửi về email.', 'success'); // Thêm thông báo
                    } else {
                        showToast('Đăng nhập thành công!', 'success');
                        setTimeout(() => window.location.href = result.redirect || '/', 1000);
                    }
                } else {
                    showToast(result.message || 'Lỗi không xác định.', 'danger');
                    refreshCaptcha();
                }
            } catch (error) {
                showToast('Lỗi kết nối đến server.', 'danger');
                refreshCaptcha();
            } finally {
                btn.disabled = false; spinner.style.display = 'none';
            }
        }

        function setupOtpInputs() {
            const inputs = document.querySelectorAll('.otp-input');
            inputs.forEach((input, index) => {
                input.addEventListener('input', () => { if (input.value && index < inputs.length - 1) inputs[index + 1].focus(); });
                input.addEventListener('keydown', e => { if (e.key === 'Backspace' && !input.value && index > 0) inputs[index - 1].focus(); });
            });
        }

        async function verifyOTP() {
            const otp = Array.from(document.querySelectorAll('.otp-input')).map(input => input.value).join('');
            if (otp.length !== 6) return showToast('Vui lòng nhập đủ 6 số OTP.', 'danger');
            try {
                const res = await fetch('/api/verify-otp', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': document.getElementById('csrfToken').value },
                    body: JSON.stringify({ otp: otp })
                });
                const result = await res.json();
                if (result.success) {
                    showToast('Xác thực thành công!', 'success');
                    setTimeout(() => window.location.href = result.redirect || '/', 1000);
                } else {
                    showToast(result.error || 'Mã OTP không đúng.', 'danger');
                }
            } catch (error) { showToast('Lỗi khi xác thực OTP.', 'danger'); }
        }

        function startResendTimer() {
            let timeLeft = 60;
            const link = document.getElementById('resendLink'), countdown = document.getElementById('countdown');
            link.style.pointerEvents = 'none'; link.style.opacity = '0.5';
            countdown.textContent = `(${timeLeft}s)`;
            const timer = setInterval(() => {
                timeLeft--; countdown.textContent = `(${timeLeft}s)`;
                if (timeLeft <= 0) { clearInterval(timer); link.style.pointerEvents = 'auto'; link.style.opacity = '1'; countdown.textContent = ''; }
            }, 1000);
        }

        async function resendOTP(e) {
            e.preventDefault();
            try {
                const res = await fetch('/api/resend-otp', { method: 'POST', headers: { 'X-CSRF-TOKEN': document.getElementById('csrfToken').value } });
                const result = await res.json();
                if (result.success) { showToast('Mã OTP mới đã được gửi.', 'success'); startResendTimer(); }
                else { showToast(result.error || 'Không thể gửi lại OTP.', 'danger'); }
            } catch (error) { showToast('Lỗi khi gửi lại OTP.', 'danger'); }
        }

