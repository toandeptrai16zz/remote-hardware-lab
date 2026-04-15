(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        API_ENDPOINTS: {
            USERS: '/admin/api/users',
            DEVICES: '/admin/api/devices',
            MISSIONS: '/admin/api/missions'
        },
        VALIDATION: {
            MISSION_NAME: {
                MIN_LENGTH: 3,
                MAX_LENGTH: 100,
                PATTERN: /^[a-zA-Z0-9\s\-_\.,:\(\)\[\]\u00C0-\u1EF9]+$/
            }
        },
        NOTIFICATION: {
            DURATION: 5000,
            POSITION: 'top-end'
        },
        SELECT2: {
            THEME: 'bootstrap-5',
            WIDTH: '100%',
            SEARCH_DELAY: 300
        }
    };

    // DOM element cache
    const elements = {
        form: document.getElementById('createMissionForm'),
        missionName: document.getElementById('missionName'),
        usersSelect: document.getElementById('usersSelect'),
        submitBtn: document.getElementById('submitBtn'),
        missionNameIndicator: document.getElementById('missionNameIndicator'),
        missionNameError: document.getElementById('missionNameError'),
        usersSelectError: document.getElementById('usersSelectError')
    };

    // Application state
    const state = {
        isSubmitting: false,
        isInitialized: false,
        usersLoaded: false,
        validation: {
            missionName: false,
            users: false
        }
    };

    /**
     * Display notification message
     */
    function showNotification(message, type = 'success') {
        const toastContainer = document.querySelector('.toast-container');
        
        if (!toastContainer) {
            // Create a minimal toast fallback instead of alert()
            const fallback = document.createElement('div');
            const typeColors = { error: '#ef4444', success: '#22c55e', info: '#7c6af7' };
            fallback.style.cssText = `position:fixed;top:20px;right:20px;z-index:9999;background:#1c1c26;color:#e8e8f0;border-left:4px solid ${typeColors[type]||typeColors.success};padding:14px 20px;border-radius:8px;font-size:14px;font-family:'Inter',sans-serif;box-shadow:0 8px 32px rgba(0,0,0,0.4);max-width:400px;`;
            fallback.textContent = message;
            document.body.appendChild(fallback);
            setTimeout(() => fallback.remove(), 4000);
            return;
        }

        const alertType = type === 'error' ? 'danger' : 
                         type === 'info' ? 'primary' : 
                         'success';
        
        const toastId = `toast-${Date.now()}`;
        const iconClass = type === 'error' ? 'fa-exclamation-circle' : 
                         type === 'info' ? 'fa-info-circle' : 
                         'fa-check-circle';
        
        const toastHTML = `
            <div id="${toastId}" class="toast show align-items-center text-bg-${alertType} border-0" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fa-solid ${iconClass} me-2" aria-hidden="true"></i>
                        ${escapeHtml(message)}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `;
        
        toastContainer.insertAdjacentHTML('beforeend', toastHTML);
        
        const toastElement = document.getElementById(toastId);
        const bsToast = new bootstrap.Toast(toastElement, { 
            delay: CONFIG.NOTIFICATION.DURATION 
        });
        
        bsToast.show();
        
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Fetch data and populate select element
     */
    async function fetchAndPopulate(url, selectElement, valueField, textField) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 10000);

            const response = await fetch(url, {
                signal: controller.signal,
                headers: {
                    'Accept': 'application/json',
                    'Cache-Control': 'no-cache'
                }
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (!Array.isArray(data)) {
                throw new Error('Invalid response format: expected array');
            }

            // Clear existing options
            selectElement.innerHTML = '';

            // Populate options
            data.forEach(item => {
                if (item[valueField] && item[textField]) {
                    const option = new Option(
                        escapeHtml(item[textField]), 
                        item[valueField]
                    );
                    selectElement.appendChild(option);
                }
            });

            // Trigger change to update Select2
            $(selectElement).trigger('change');

            return true;

        } catch (error) {
            console.error(`Failed to fetch data for ${selectElement.id}:`, error);
            
            // Show error option
            selectElement.innerHTML = '<option value="" disabled>Lỗi tải dữ liệu</option>';
            
            showNotification(
                `Không thể tải dữ liệu ${selectElement.id}. Vui lòng thử lại.`,
                'error'
            );
            
            return false;
        }
    }

    /**
     * Initialize Select2 components
     */
    function initializeSelect2() {
        // Users select
        $(elements.usersSelect).select2({
            theme: CONFIG.SELECT2.THEME,
            width: CONFIG.SELECT2.WIDTH,
            placeholder: 'Chọn một hoặc nhiều user',
            allowClear: true,
            closeOnSelect: false,
            language: {
                noResults: () => 'Không tìm thấy user nào',
                searching: () => 'Đang tìm kiếm...',
                loadingMore: () => 'Đang tải thêm...'
            }
        });

        // Event listeners for validation
        $(elements.usersSelect).on('change', validateUsers);
    }

    /**
     * Validate mission name
     */
    function validateMissionName() {
        const value = elements.missionName.value.trim();
        const { MIN_LENGTH, MAX_LENGTH, PATTERN } = CONFIG.VALIDATION.MISSION_NAME;
        
        let isValid = true;
        let errorMessage = '';

        if (!value) {
            isValid = false;
            errorMessage = 'Tên mission là bắt buộc';
        } else if (value.length < MIN_LENGTH) {
            isValid = false;
            errorMessage = `Tên mission phải có ít nhất ${MIN_LENGTH} ký tự`;
        } else if (value.length > MAX_LENGTH) {
            isValid = false;
            errorMessage = `Tên mission không được vượt quá ${MAX_LENGTH} ký tự`;
        } else if (!PATTERN.test(value)) {
            isValid = false;
            errorMessage = 'Tên mission chứa ký tự không hợp lệ';
        }

        state.validation.missionName = isValid;
        updateFieldValidation(elements.missionName, isValid, errorMessage, elements.missionNameError, elements.missionNameIndicator);
        
        return isValid;
    }

    /**
     * Validate users selection
     */
    function validateUsers() {
        const selectedUsers = $(elements.usersSelect).val() || [];
        const isValid = selectedUsers.length > 0;
        const errorMessage = isValid ? '' : 'Phải chọn ít nhất một user';

        state.validation.users = isValid;
        updateFieldValidation(elements.usersSelect, isValid, errorMessage, elements.usersSelectError);
        
        return isValid;
    }

    /**
     * Update field validation UI
     */
    function updateFieldValidation(fieldElement, isValid, errorMessage, errorElement, indicatorElement = null) {
        // Update field styling
        fieldElement.classList.toggle('form-control-error', !isValid);
        fieldElement.classList.toggle('form-control-success', isValid);

        // Update error message
        if (errorElement) {
            if (isValid) {
                errorElement.style.display = 'none';
                errorElement.textContent = '';
            } else {
                errorElement.style.display = 'flex';
                errorElement.innerHTML = `<i class="fa-solid fa-exclamation-triangle" aria-hidden="true"></i> ${escapeHtml(errorMessage)}`;
            }
        }

        // Update validation indicator
        if (indicatorElement) {
            indicatorElement.className = 'validation-indicator';
            if (isValid) {
                indicatorElement.classList.add('valid');
                indicatorElement.innerHTML = '<i class="fa-solid fa-check" aria-hidden="true"></i>';
            } else if (fieldElement.value.trim()) {
                indicatorElement.classList.add('invalid');
                indicatorElement.innerHTML = '<i class="fa-solid fa-times" aria-hidden="true"></i>';
            } else {
                indicatorElement.innerHTML = '';
            }
        }

        // Update submit button state
        updateSubmitButton();
    }

    /**
     * Update submit button state
     */
    function updateSubmitButton() {
        const isFormValid = Object.values(state.validation).every(valid => valid);
        elements.submitBtn.disabled = !isFormValid || state.isSubmitting;
    }

    /**
     * Set form loading state
     */
    function setFormLoading(isLoading) {
        state.isSubmitting = isLoading;
        
        elements.submitBtn.classList.toggle('loading', isLoading);
        elements.submitBtn.disabled = isLoading;
        
        // Disable form inputs
        const inputs = elements.form.querySelectorAll('input, select, button');
        inputs.forEach(input => {
            input.disabled = isLoading;
        });

        if (isLoading) {
            elements.form.classList.add('form-loading');
        } else {
            elements.form.classList.remove('form-loading');
        }
    }

    /**
     * Handle form submission
     */
    async function handleSubmit(event) {
        event.preventDefault();
        
        if (state.isSubmitting) return;

        // Validate all fields
        const isMissionNameValid = validateMissionName();
        const isUsersValid = validateUsers();

        if (!isMissionNameValid || !isUsersValid) {
            showNotification('Vui lòng kiểm tra và sửa các lỗi trong form', 'error');
            return;
        }

        setFormLoading(true);

        try {
            const formData = {
                mission_name: elements.missionName.value.trim(),
                type: document.getElementById('missionType').value,
                duration_minutes: document.getElementById('durationMinutes').value,
                start_time: document.getElementById('startTime').value,
                end_time: document.getElementById('endTime').value,
                description: document.getElementById('missionDescription').value,
                user_ids: ($(elements.usersSelect).val() || []).map(Number)
            };

            // Validate data one more time
            if (!formData.mission_name || formData.user_ids.length === 0 || false) {
                throw new Error('Dữ liệu form không hợp lệ');
            }

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000);

            const isEdit = !!window.editingMissionId;
            const method = isEdit ? 'PUT' : 'POST';
            const url = isEdit ? `${CONFIG.API_ENDPOINTS.MISSIONS}/${window.editingMissionId}` : CONFIG.API_ENDPOINTS.MISSIONS;

            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(formData),
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || `HTTP ${response.status}: ${response.statusText}`);
            }

            // Success
            showNotification(result.message || 'Mission đã được tạo thành công!', 'success');
            
            // Reset form
            resetForm();
            // Tải lại bảng để xem bài mới giao
            if (typeof loadMissionsTable === 'function') {
                loadMissionsTable();
            }
            
        } catch (error) {
            console.error('Mission creation failed:', error);
            
            let errorMessage = 'Đã xảy ra lỗi khi tạo mission';
            
            if (error.name === 'AbortError') {
                errorMessage = 'Yêu cầu bị timeout. Vui lòng thử lại.';
            } else if (error.message) {
                errorMessage = error.message;
            }
            
            showNotification(`Lỗi: ${errorMessage}`, 'error');
            
        } finally {
            setFormLoading(false);
        }
    }

    /**
     * Reset form to initial state
     */
    function resetForm() {
        // Reset form fields
        elements.form.reset();
        
        // Reset form fields
        elements.form.reset();
        window.editingMissionId = null;
        document.getElementById('submitBtn').innerHTML = `<i class="fa-solid fa-paper-plane" aria-hidden="true"></i> Giao Mission`;
        
        // Clear Select2 selections
        $(elements.usersSelect).val(null).trigger('change');
        
        // Reset validation state
        state.validation = {
            missionName: false,
            users: false
        };
        
        // Clear validation UI
        const fields = [
            { element: elements.missionName, error: elements.missionNameError, indicator: elements.missionNameIndicator },
            { element: elements.usersSelect, error: elements.usersSelectError }
        ];
        
        fields.forEach(({ element, error, indicator }) => {
            element.classList.remove('form-control-error', 'form-control-success');
            if (error) {
                error.style.display = 'none';
                error.textContent = '';
            }
            if (indicator) {
                indicator.className = 'validation-indicator';
                indicator.innerHTML = '';
            }
        });
        
        updateSubmitButton();
    }

    /**
     * Load initial data
     */
    async function loadInitialData() {
        const loadingPromises = [
            fetchAndPopulate(CONFIG.API_ENDPOINTS.USERS, elements.usersSelect, 'id', 'username')
        ];

        try {
            const [usersLoaded] = await Promise.all(loadingPromises);
            
            state.usersLoaded = usersLoaded;
            
            if (!usersLoaded) {
                showNotification('Một số dữ liệu không thể tải được. Vui lòng refresh trang.', 'error');
            }
            
        } catch (error) {
            console.error('Failed to load initial data:', error);
            showNotification('Không thể tải dữ liệu ban đầu. Vui lòng refresh trang.', 'error');
        }
    }

    /**
     * Setup event listeners
     */
    function setupEventListeners() {
        // Form submission
        elements.form.addEventListener('submit', handleSubmit);
        
        // Mission name validation
        elements.missionName.addEventListener('input', validateMissionName);
        elements.missionName.addEventListener('blur', validateMissionName);
        
        // Prevent form submission on Enter in text fields
        elements.missionName.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                validateMissionName();
            }
        });

        // Focus management for better UX
        elements.missionName.addEventListener('focus', () => {
            elements.missionName.select();
        });

        // Handle page unload
        window.addEventListener('beforeunload', (event) => {
            if (state.isSubmitting) {
                event.preventDefault();
                event.returnValue = 'Mission đang được tạo. Bạn có chắc muốn rời khỏi trang?';
                return event.returnValue;
            }
        });
    }

    /**
     * Initialize application
     */
    async function initialize() {
        if (state.isInitialized) return;
        
        try {
            // Check if all required elements exist
            const requiredElements = Object.entries(elements);
            const missingElements = requiredElements.filter(([name, element]) => !element);
            
            if (missingElements.length > 0) {
                console.error('Missing required elements:', missingElements.map(([name]) => name));
                showNotification('Lỗi khởi tạo trang. Vui lòng refresh.', 'error');
                return;
            }

            // Initialize Select2
            initializeSelect2();
            
            // Setup event listeners
            setupEventListeners();
            
            // Load initial data
            await loadInitialData();
            
            state.isInitialized = true;
            
            // Focus on first input
            elements.missionName.focus();
            
            console.log('Mission assignment page initialized successfully');
            
        } catch (error) {
            console.error('Failed to initialize mission assignment page:', error);
            showNotification('Lỗi khởi tạo trang. Vui lòng refresh và thử lại.', 'error');
        }
    }

    
    // Mission Type listener for duration defaults
    const startInput = document.getElementById('startTime');
    const endInput = document.getElementById('endTime');
    const durationInput = document.getElementById('durationMinutes');

    function calculateEndTime() {
        if (!startInput.value || !durationInput.value) return;
        const startDate = new Date(startInput.value);
        if (isNaN(startDate.getTime())) return;
        
        const duration = parseInt(durationInput.value) || 0;
        const endDate = new Date(startDate.getTime() + duration * 60000);
        
        const tzOffset = endDate.getTimezoneOffset() * 60000;
        const localISOTime = (new Date(endDate - tzOffset)).toISOString().slice(0, 16);
        endInput.value = localISOTime;
    }

    startInput.addEventListener('change', calculateEndTime);
    durationInput.addEventListener('input', calculateEndTime);

    document.getElementById('missionType')?.addEventListener('change', function(e) {
        if (e.target.value === 'exam') durationInput.value = 90;
        else if (e.target.value === 'test') durationInput.value = 45;
        calculateEndTime();
    });

    // Populate missions table
    async function loadMissionsTable() {
        const tbody = document.querySelector('#missionsTable tbody');
        try {
            const response = await fetch('/admin/api/missions');
            const data = await response.json();
            
            if (!data || data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-4">Chưa có bài thi nào</td></tr>';
                return;
            }
            window.missionsData = data;

            const now = Date.now();

            function getMissionPhase(m) {
                if (!m.start_time) return 'upcoming';
                const start = new Date(m.start_time).getTime();
                const end = new Date(m.end_time).getTime();
                if (now < start) return 'upcoming';
                if (now >= start && now <= end) return 'active';
                return 'ended';
            }

            function isFullySubmitted(m) {
                return m.assigned_count > 0 && m.submitted_count >= m.assigned_count;
            }

            function progressBadge(m) {
                const total = m.assigned_count || 0;
                const done  = m.submitted_count || 0;
                if (total === 0) return `<span class="badge bg-secondary">Chưa giao</span>`;
                const pct = Math.round(done / total * 100);
                const cls = done >= total ? 'bg-success' : done > 0 ? 'bg-warning text-dark' : 'bg-secondary';
                return `<span class="badge ${cls}">${done}/${total} (${pct}%)</span>`;
            }

            function phaseSectionRow(label, color) {
                return `<tr style="background:rgba(255,255,255,0.03);">
                    <td colspan="8" style="padding:0.4rem 0.8rem;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:${color};border-bottom:1px solid rgba(255,255,255,0.07);">
                        ${label}
                    </td>
                </tr>`;
            }

            function missionRow(m) {
                const faded = isFullySubmitted(m) ? 'opacity:0.55;' : '';
                return `<tr style="${faded}">
                    <td>#${m.id}</td>
                    <td><strong>${escapeHtml(m.name)}</strong></td>
                    <td><span class="badge bg-secondary">${m.type.toUpperCase()}</span></td>
                    <td>${m.start_time ? new Date(m.start_time).toLocaleString('vi-VN') : ''}</td>
                    <td>${m.end_time ? new Date(m.end_time).toLocaleString('vi-VN') : ''}</td>
                    <td>${m.duration_minutes}p</td>
                    <td>${progressBadge(m)}</td>
                    <td class="text-end">
                        <button class="btn btn-sm btn-info" onclick="editMission(${m.id})" title="Chỉnh sửa"><i class="fa-solid fa-edit"></i></button>
                        <button class="btn btn-sm btn-danger" onclick="deleteMission(${m.id})" title="Xóa bài thi"><i class="fa-solid fa-trash"></i></button>
                        <button class="btn btn-sm btn-success" onclick="exportMission(${m.id}, '${escapeHtml(m.name)}')">
                            <i class="fa-solid fa-file-excel"></i> Xuất
                        </button>
                    </td>
                </tr>`;
            }

            const activeM   = data.filter(m => getMissionPhase(m) === 'active');
            const upcomingM = data.filter(m => getMissionPhase(m) === 'upcoming');
            const endedM    = data.filter(m => getMissionPhase(m) === 'ended');

            let rows = '';
            if (activeM.length) {
                rows += phaseSectionRow('🟢 Đang diễn ra', '#22c55e');
                rows += activeM.map(missionRow).join('');
            }
            if (upcomingM.length) {
                rows += phaseSectionRow('⏰ Sắp tới', '#f59e0b');
                rows += upcomingM.map(missionRow).join('');
            }
            if (endedM.length) {
                rows += phaseSectionRow('✅ Đã kết thúc', '#888');
                rows += endedM.map(missionRow).join('');
            }

            tbody.innerHTML = rows;
        } catch(e) {
            tbody.innerHTML = '<tr><td colspan="7" class="text-center text-danger py-4">Lỗi tải dữ liệu</td></tr>';
        }
    }

    // Export Excel function
    window.exportMission = function(id, name) {
        showNotification(`Đang chuẩn bị xuất file điểm cho bài thi ${name}...`, 'info');
        window.location.href = `/admin/api/missions/${id}/export`;
    };

    window.editMission = function(id) {
        const m = window.missionsData.find(x => x.id === id);
        if(!m) return;
        window.editingMissionId = id;
        document.getElementById('missionName').value = m.name;
        document.getElementById('duration').value = m.duration_minutes;
        document.getElementById('startTime').value = m.start_time ? m.start_time.slice(0,16) : '';
        document.getElementById('endTime').value = m.end_time ? m.end_time.slice(0,16) : '';
        document.getElementById('missionDescription').value = m.description || '';
        document.getElementById('submitBtn').innerHTML = '<i class="fa-solid fa-save"></i> Cập nhật Mission';
        // Mock valid
        state.validation = { missionName: true, users: true };
        document.getElementById('missionName').classList.add('form-control-success');
        updateSubmitButton();
        window.scrollTo({top: 0, behavior: 'smooth'});
    };

    window.deleteMission = async function(id) {
        const result = await Swal.fire({
            title: 'Cảnh báo!',
            text: 'Bạn có chắc chắn muốn xóa bài thi này? Mọi dữ liệu nộp bài của sinh viên cũng sẽ bị xóa vĩnh viễn!',
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            cancelButtonColor: '#3085d6',
            confirmButtonText: 'Xóa ngay',
            cancelButtonText: 'Hủy bỏ',
            background: '#13131a',
            color: '#e8e8f0',
            backdrop: `rgba(10,10,30,0.6) blur(4px)`
        });
        if (!result.isConfirmed) return;
        try {
            const res = await fetch(`/admin/api/missions/${id}`, {method: 'DELETE'});
            const data = await res.json();
            if(data.success) {
                showNotification(data.message, 'success');
                loadMissionsTable();
            } else showNotification(data.error, 'error');
        } catch(e) {
            showNotification('Lỗi khi xóa bài thi', 'error');
        }
    };

    // Reload table after init + auto-refresh mỗi 15 giây
    const originalInit = initialize;
    initialize = async function() {
        await originalInit();
        loadMissionsTable();
        // TỰ ĐỘNG LÀM MỚI bảng để cập nhật khi sinh viên nộp bài -> bài thi kết thúc sớm
        setInterval(loadMissionsTable, 15000);
    };


    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        initialize();
    }

    // Expose public API for debugging (only in development)
    if (window.location.hostname === 'localhost' || window.location.hostname.includes('dev')) {
        window.MissionAssignment = {
            state,
            validateMissionName,
            validateUsers,
            resetForm,
            loadInitialData
        };
    }

})();