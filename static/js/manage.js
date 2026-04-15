// --- HÀM THÔNG BÁO TOAST ---
function showToast(message, type = 'success') {
    const container = document.getElementById('js-flash-container');
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} shadow`;
    notification.style.marginBottom = '10px';
    notification.style.minWidth = '250px';
    notification.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i> ${message}`;
    
    container.appendChild(notification);

    setTimeout(() => {
        notification.style.transition = "opacity 0.5s ease";
        notification.style.opacity = "0";
        setTimeout(() => notification.remove(), 500);
    }, 3000);
}

// --- XỬ LÝ MODAL ---
function showActionModal(actionUrl, title, body, btnClass, btnText) {
    const modalEl = document.getElementById('actionConfirmModal');
    const modal = new bootstrap.Modal(modalEl);
    
    document.getElementById('actionModalTitle').innerHTML = `<i class="fa-solid fa-exclamation-triangle"></i> ${title}`;
    document.getElementById('actionModalBody').innerHTML = body;
    
    const confirmBtn = document.getElementById('actionModalConfirmBtn');
    confirmBtn.innerHTML = `<i class="fa-solid fa-check me-1"></i> ${btnText}`;
    confirmBtn.className = `btn ${btnClass}`;
    
    document.getElementById('actionForm').setAttribute('action', actionUrl);
    
    modal.show();
}

function showDeleteModal(actionUrl, username) {
    const modalEl = document.getElementById('confirmDeleteModal');
    const modal = new bootstrap.Modal(modalEl);
    
    document.getElementById('deleteModalBody').innerHTML = `
        Bạn có chắc chắn muốn xóa vĩnh viễn người dùng <strong>${username}</strong> không? 
        <br><br>
        <span class="text-danger">⚠️ Hành động này sẽ xóa cả container và toàn bộ file của họ.</span>
    `;
    document.getElementById('deleteUserForm').setAttribute('action', actionUrl);
    
    modal.show();
}

// Form validation
document.addEventListener('DOMContentLoaded', function () {
    const addUserForm = document.getElementById('addUserForm');
    if (addUserForm) {
        addUserForm.addEventListener('submit', function(e) {
            const username = this.querySelector('[name="username"]').value;
            const password = this.querySelector('[name="password"]').value;
            
            if (username.length < 3) {
                e.preventDefault();
                showToast('Username phải có ít nhất 3 ký tự', 'danger'); // Thay alert
                return false;
            }
            
            if (password.length < 8) {
                e.preventDefault();
                showToast('Password phải có ít nhất 8 ký tự', 'danger'); // Thay alert
                return false;
            }
        });
    }
});

