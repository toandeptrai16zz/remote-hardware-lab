(function () {
  'use strict';

  // Cấu hình
  const CONFIG = {
    AUTO_REFRESH_INTERVAL: 30000, // 30 giây
    TIME_UPDATE_INTERVAL: 1000,   // 1 giây
    API_ENDPOINTS: {
      LOGS: '/admin/api/logs'
    },
    LOCALE: 'vi-VN'
  };

  // Cache các phần tử DOM
  const elements = {
    currentTime: document.getElementById('currentTime'),
    refreshBtn: document.getElementById('refreshLogsBtn'),
    logsTableBody: document.getElementById('logsTableBody'),
    refreshIcon: null // Sẽ được thiết lập sau khi DOM sẵn sàng
  };

  // Quản lý trạng thái
  const state = {
    isRefreshing: false,
    autoRefreshTimer: null,
    timeUpdateTimer: null
  };

  /**
   * Cập nhật hiển thị thời gian hiện tại
   */
  function updateTime() {
    if (!elements.currentTime) return;

    const now = new Date();
    const timeString = now.toLocaleString(CONFIG.LOCALE);
    const isoString = now.toISOString();

    elements.currentTime.textContent = timeString;
    elements.currentTime.setAttribute('datetime', isoString);
  }

  /**
   * Lấy class badge dựa trên loại hành động
   */
  function getActionBadgeClass(action) {
    const actionType = action.split(':')[0].toLowerCase();

    if (actionType.includes('login')) return 'login';
    if (actionType.includes('logout')) return 'logout';
    if (actionType.includes('register')) return 'register';
    return 'admin';
  }

  /**
   * Tạo phần tử hàng trong bảng cho một mục log
   */
  function createLogRow(log) {
    const row = document.createElement('tr');
    const badgeClass = getActionBadgeClass(log.action);
    const timestamp = new Date(log.timestamp);

    row.className = 'log-row';
    row.innerHTML = `
      <td><strong>${escapeHtml(log.username)}</strong></td>
      <td>
        <span class="action-badge action-${badgeClass}" 
              role="status" 
              aria-label="Action: ${escapeHtml(log.action)}">
          ${escapeHtml(log.action)}
        </span>
      </td>
      <td>
        <span class="text-muted">
          <i class="fa-solid fa-globe me-1" aria-hidden="true"></i>
          ${escapeHtml(log.ip_address || 'N/A')}
        </span>
      </td>
      <td>
        <time class="text-muted" 
              datetime="${timestamp.toISOString()}" 
              title="${timestamp.toLocaleString(CONFIG.LOCALE)}">
          ${timestamp.toLocaleTimeString(CONFIG.LOCALE)}
        </time>
      </td>
    `;

    return row;
  }

  /**
   * Cập nhật bảng log với dữ liệu mới
   */
  function updateLogsTable(logs) {
    if (!elements.logsTableBody) return;

    // Xóa nội dung hiện có
    elements.logsTableBody.innerHTML = '';

    if (!logs || logs.length === 0) {
      elements.logsTableBody.innerHTML = `
        <tr>
          <td colspan="4" class="text-center text-muted py-4">
            <i class="fa-solid fa-inbox fa-2x mb-2 d-block" aria-hidden="true"></i>
            Chưa có log nào
          </td>
        </tr>
      `;
      return;
    }

    // Sử dụng document fragment để cải thiện hiệu suất
    const fragment = document.createDocumentFragment();
    logs.forEach(log => {
      fragment.appendChild(createLogRow(log));
    });

    elements.logsTableBody.appendChild(fragment);
  }

  /**
   * Thiết lập trạng thái đang tải (loading) cho nút làm mới
   */
  function setRefreshButtonState(isLoading) {
    if (!elements.refreshBtn || !elements.refreshIcon) return;

    elements.refreshBtn.disabled = isLoading;
    elements.refreshIcon.classList.toggle('fa-spin', isLoading);

    if (isLoading) {
      elements.refreshBtn.classList.add('loading');
    } else {
      elements.refreshBtn.classList.remove('loading');
    }
  }

  /**
   * Làm mới danh sách log từ API
   */
  async function refreshLogs() {
    if (state.isRefreshing) return;

    state.isRefreshing = true;
    setRefreshButtonState(true);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // Hết hạn sau 10 giây

      const response = await fetch(CONFIG.API_ENDPOINTS.LOGS, {
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

      if (data.success && Array.isArray(data.logs)) {
        updateLogsTable(data.logs);
      } else {
        console.error('Invalid API response:', data);
        throw new Error(data.error || 'Invalid response format');
      }

    } catch (error) {
      console.error('Failed to refresh logs:', error);

      // Hiển thị thông báo lỗi thân thiện với người dùng
      if (elements.logsTableBody) {
        elements.logsTableBody.innerHTML = `
          <tr>
            <td colspan="4" class="text-center text-danger py-4">
              <i class="fa-solid fa-exclamation-triangle fa-2x mb-2 d-block" aria-hidden="true"></i>
              Không thể tải dữ liệu. Vui lòng thử lại.
            </td>
          </tr>
        `;
      }
    } finally {
      state.isRefreshing = false;
      setRefreshButtonState(false);
    }
  }

  /**
   * Bắt đầu bộ hẹn giờ tự động làm mới
   */
  function startAutoRefresh() {
    if (state.autoRefreshTimer) {
      clearInterval(state.autoRefreshTimer);
    }

    state.autoRefreshTimer = setInterval(() => {
      if (!state.isRefreshing && document.visibilityState === 'visible') {
        refreshLogs();
      }
    }, CONFIG.AUTO_REFRESH_INTERVAL);
  }

  /**
   * Bắt đầu bộ hẹn giờ cập nhật thời gian
   */
  function startTimeUpdate() {
    if (state.timeUpdateTimer) {
      clearInterval(state.timeUpdateTimer);
    }

    updateTime(); // Initial update
    state.timeUpdateTimer = setInterval(updateTime, CONFIG.TIME_UPDATE_INTERVAL);
  }

  /**
   * Xử lý khi trạng thái hiển thị của trang thay đổi (tạm dừng/khôi phục tự động làm mới)
   */
  function handleVisibilityChange() {
    if (document.visibilityState === 'hidden') {
      if (state.autoRefreshTimer) {
        clearInterval(state.autoRefreshTimer);
      }
    } else {
      startAutoRefresh();
    }
  }

  /**
   * Thoát các ký tự HTML để ngăn chặn tấn công XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Khởi tạo ứng dụng
   */
  function init() {
    // Cache các phần tử DOM
    elements.refreshIcon = elements.refreshBtn?.querySelector('i');

    // Thiết lập các trình lắng nghe sự kiện
    if (elements.refreshBtn) {
      elements.refreshBtn.addEventListener('click', refreshLogs);
    }

    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Bắt đầu các bộ hẹn giờ
    startTimeUpdate();
    startAutoRefresh();

    // Xử lý khi trang được đóng/tải lại
    window.addEventListener('beforeunload', () => {
      if (state.autoRefreshTimer) clearInterval(state.autoRefreshTimer);
      if (state.timeUpdateTimer) clearInterval(state.timeUpdateTimer);
    });
  }

  // Chuyển refreshLogs thành biến toàn cục cho trình xử lý sự kiện onclick
  window.refreshLogs = refreshLogs;

  // Khởi tạo khi DOM đã sẵn sàng
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();

