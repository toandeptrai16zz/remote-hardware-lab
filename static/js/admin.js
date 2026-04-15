(function() {
  'use strict';

  // Configuration
  const CONFIG = {
    AUTO_REFRESH_INTERVAL: 30000, // 30 seconds
    TIME_UPDATE_INTERVAL: 1000,   // 1 second
    API_ENDPOINTS: {
      LOGS: '/admin/api/logs'
    },
    LOCALE: 'vi-VN'
  };

  // DOM elements cache
  const elements = {
    currentTime: document.getElementById('currentTime'),
    refreshBtn: document.getElementById('refreshLogsBtn'),
    logsTableBody: document.getElementById('logsTableBody'),
    refreshIcon: null // Will be set after DOM is ready
  };

  // State management
  const state = {
    isRefreshing: false,
    autoRefreshTimer: null,
    timeUpdateTimer: null
  };

  /**
   * Update current time display
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
   * Get action badge class based on action type
   */
  function getActionBadgeClass(action) {
    const actionType = action.split(':')[0].toLowerCase();
    
    if (actionType.includes('login')) return 'login';
    if (actionType.includes('logout')) return 'logout';
    if (actionType.includes('register')) return 'register';
    return 'admin';
  }

  /**
   * Create table row element for log entry
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
   * Update logs table with new data
   */
  function updateLogsTable(logs) {
    if (!elements.logsTableBody) return;

    // Clear existing content
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
    
    // Create document fragment for better performance
    const fragment = document.createDocumentFragment();
    logs.forEach(log => {
      fragment.appendChild(createLogRow(log));
    });
    
    elements.logsTableBody.appendChild(fragment);
  }

  /**
   * Set refresh button loading state
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
   * Refresh logs from API
   */
  async function refreshLogs() {
    if (state.isRefreshing) return;
    
    state.isRefreshing = true;
    setRefreshButtonState(true);
    
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
      
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
      
      // Show user-friendly error message
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
   * Start auto refresh timer
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
   * Start time update timer
   */
  function startTimeUpdate() {
    if (state.timeUpdateTimer) {
      clearInterval(state.timeUpdateTimer);
    }
    
    updateTime(); // Initial update
    state.timeUpdateTimer = setInterval(updateTime, CONFIG.TIME_UPDATE_INTERVAL);
  }

  /**
   * Handle visibility change (pause/resume auto refresh)
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
   * Escape HTML to prevent XSS
   */
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Initialize application
   */
  function init() {
    // Cache DOM elements
    elements.refreshIcon = elements.refreshBtn?.querySelector('i');
    
    // Set up event listeners
    if (elements.refreshBtn) {
      elements.refreshBtn.addEventListener('click', refreshLogs);
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Start timers
    startTimeUpdate();
    startAutoRefresh();
    
    // Handle page unload
    window.addEventListener('beforeunload', () => {
      if (state.autoRefreshTimer) clearInterval(state.autoRefreshTimer);
      if (state.timeUpdateTimer) clearInterval(state.timeUpdateTimer);
    });
  }

  // Make refreshLogs available globally for onclick handler
  window.refreshLogs = refreshLogs;

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

})();

