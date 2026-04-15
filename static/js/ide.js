let editor, terminal, fitAddon, webLinksAddon, socket;
let currentFile = null;
const openFiles = new Map();
let uploadPath = '.';     // Thieu Dinh Nghia Ham (DA FIX - by CHUONG)
let selectedTreeItem = null;
let selectedPort = null;
let availablePorts = [];
const username = window.currentUsername;

// File creation modal state
let currentFileCreationType = 'file';
let currentFileCreationPath = '.';

// Bien cuc bo cho Queue
let socketUpload = null;
let currentSid = null;

// Unsaved changes modal state
let pendingCloseFile = null;
let pendingDeleteItemPath = null;

// Serial monitor variables
let socketSerial = null;

document.addEventListener('DOMContentLoaded', () => {
    setupEditor();
    setupTerminal();
    setupResizer();
    setupHorizontalResizer();
    setupEventListeners();
    setupFileCreationModal();
    refreshRootFiles();
    loadIDEState();
    connectTerminalSocket();
    connectUploadSocket();
    setupRealTimeNotifications();
});

function setupRealTimeNotifications() {
    const mainSocket = io.connect(location.protocol + '//' + document.domain + ':' + location.port + '/');
    mainSocket.on('new_mission', function (data) {
        showNotification(` BÀI TẬP MỚI: ${data.mission_name}. Hãy truy cập tab Bài tập/Thi để bắt đầu làm bài!`, 'info');
        if (typeof checkIDEActiveMission === 'function') checkIDEActiveMission();
    });
}

// =================================================================
// FILE CREATION MODAL
// =================================================================
function setupFileCreationModal() {
    // Close modal on escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && DOM.fileCreationModal.style.display !== 'none') {
            closeFileCreationModal();
        }
    });

    // Close modal on backdrop click
    DOM.fileCreationModal.addEventListener('click', (e) => {
        if (e.target === DOM.fileCreationModal) {
            closeFileCreationModal();
        }
    });

    // Handle enter key in input
    DOM.fileNameInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            confirmFileCreation();
        }
    });

    // Auto-focus input when modal opens
    DOM.fileCreationModal.addEventListener('animationend', () => {
        if (DOM.fileCreationModal.style.display !== 'none') {
            DOM.fileNameInput.focus();
            DOM.fileNameInput.select();
        }
    });
}
function connectUploadSocket() {
    socketUpload = io('/upload_status');

    socketUpload.on('connect', () => {
        currentSid = socketUpload.id;
        console.log('Connected to upload status namespace with SID:', currentSid);
    });

    socketUpload.on('upload_status', (data) => {
        console.log('Upload status update:', data);
        const color = data.status === 'success' ? '\x1b[1;32m' :
            data.status === 'error' ? '\x1b[1;31m' : '\x1b[1;33m';

        terminal.write(`\r\n${color}[UPLOAD STATUS]\x1b[0m ${data.message}\r\n`);

        if (data.output) {
            terminal.write(`\x1b[90m${data.output}\x1b[0m\r\n`);
        }

        if (data.status === 'success' || data.status === 'error') {
            terminal.write(`\r\n$ `);
        }
        terminal.scrollToBottom();
    });
}

function showFileCreationModal(type, path = '.') {
    currentFileCreationType = type;
    currentFileCreationPath = path;

    // Update modal content based on type
    if (type === 'file') {
        DOM.fileCreationTitle.innerHTML = '<i class="fa-solid fa-file-plus"></i> Tạo file mới';
        DOM.fileCreationSubtitle.textContent = 'Nhập tên file và chọn vị trí lưu trữ';
        DOM.fileNameInput.placeholder = 'Nhập tên file (ví dụ: main.cpp)';
    } else {
        DOM.fileCreationTitle.innerHTML = '<i class="fa-solid fa-folder-plus"></i> Tạo thư mục mới';
        DOM.fileCreationSubtitle.textContent = 'Nhập tên thư mục và chọn vị trí lưu trữ';
        DOM.fileNameInput.placeholder = 'Nhập tên thư mục (ví dụ: src)';
    }

    // Clear input and show modal
    DOM.fileNameInput.value = '';
    DOM.fileCreationModal.style.display = 'flex';

    // Focus input after animation
    setTimeout(() => {
        DOM.fileNameInput.focus();
        DOM.fileNameInput.select();
    }, 100);
}

function closeFileCreationModal() {
    DOM.fileCreationModal.style.display = 'none';
    DOM.fileNameInput.value = '';
}

async function confirmFileCreation() {
    const fileName = DOM.fileNameInput.value.trim();
    if (!fileName) {
        showNotification('Vui lòng nhập tên file/thư mục', 'error');
        return;
    }

    // Validate filename
    if (!/^[^<>:"/\\|?*]+$/.test(fileName)) {
        showNotification('Tên file/thư mục chứa ký tự không hợp lệ', 'error');
        return;
    }

    // Disable button and show loading
    DOM.createFileBtn.disabled = true;
    DOM.createFileBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang tạo...';

    try {
        await createNewItem(currentFileCreationType, currentFileCreationPath, fileName);
        closeFileCreationModal();
    } catch (error) {
        showNotification('Có lỗi xảy ra khi tạo file/thư mục', 'error');
    } finally {
        DOM.createFileBtn.disabled = false;
        DOM.createFileBtn.innerHTML = '<i class="fa-solid fa-plus"></i> Tạo';
    }
}

// =================================================================
// IDE State Management
// =================================================================
function saveIDEState() {
    try {
        const openFileKeys = Array.from(openFiles.keys()).filter(key => key !== 'Welcome');
        const state = {
            openFileKeys: openFileKeys,
            currentFileKey: (currentFile !== 'Welcome' ? currentFile : null)
        };
        localStorage.setItem(`codeSpaceState_${username}`, JSON.stringify(state));
    } catch (e) {
        console.warn("Could not save IDE state:", e);
    }
}

async function loadIDEState() {
    try {
        const savedStateJSON = localStorage.getItem(`codeSpaceState_${username}`);
        if (!savedStateJSON) {
            openWelcomeTab();
            return;
        }

        const savedState = JSON.parse(savedStateJSON);
        const filesToOpen = savedState.openFileKeys || [];

        if (filesToOpen.length > 0) {
            for (const key of filesToOpen) {
                const shortName = key.split('/').pop();
                await openFile(key, shortName, false);
            }

            const activeFile = savedState.currentFileKey && openFiles.has(savedState.currentFileKey)
                ? savedState.currentFileKey
                : filesToOpen[filesToOpen.length - 1];

            if (activeFile) switchToFile(activeFile);
            else openWelcomeTab();
        } else {
            openWelcomeTab();
        }
    } catch (e) {
        console.error("Failed to load IDE state:", e);
        localStorage.removeItem(`codeSpaceState_${username}`);
        openWelcomeTab();
    }
}

function setupEditor() {
    editor = ace.edit("editor");
    ace.require("ace/ext/language_tools");
    editor.setTheme("ace/theme/tomorrow_night_eighties");
    editor.session.setMode("ace/mode/javascript");
    editor.setFontSize(14);
    editor.setOptions({
        fontFamily: 'JetBrains Mono, monospace',
        enableLiveAutocompletion: true,
        enableBasicAutocompletion: true,
        showPrintMargin: false,
        wrap: true,
    });
let isSystemChange = false;

    editor.on("change", () => {
        if (isSystemChange) return;
        if (currentFile && openFiles.has(currentFile)) {
            const fileData = openFiles.get(currentFile);
            if (fileData.saved) {
                fileData.saved = false;
                updateTabAppearance(currentFile);
                DOM.saveButton.textContent = 'Save*';
            }
        }
    });
}

function setupTerminal() {
    terminal = new Terminal({
        cursorBlink: true,
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 13,
        lineHeight: 1.3,
        theme: {
            background: '#0d1117',
            foreground: '#d4d4d4',
            cursor: '#d4d4d4',
            selection: 'rgba(88, 166, 255, 0.3)'
        },
        scrollback: 10000,
        rightClickSelectsWord: true,
        allowTransparency: false,
        convertEol: true,
        macOptionIsMeta: true,
        disableStdin: false,
        scrollOnUserInput: true,
        fastScrollModifier: 'alt',
        fastScrollSensitivity: 5,
        minimumContrastRatio: 1
    });

    fitAddon = new FitAddon.FitAddon();
    webLinksAddon = new WebLinksAddon.WebLinksAddon();

    terminal.loadAddon(fitAddon);
    terminal.loadAddon(webLinksAddon);
    terminal.open(document.getElementById('terminal'));

    // Enhanced scrolling configuration
    const viewport = terminal.element.querySelector('.xterm-viewport');
    if (viewport) {
        viewport.style.overflowY = 'auto';
        viewport.style.scrollBehavior = 'smooth';
        viewport.style.scrollbarWidth = 'thin';
    }

    // Enhanced mouse wheel scrolling with better sensitivity
    const screen = terminal.element.querySelector('.xterm-screen');
    if (screen) {
        screen.addEventListener('wheel', (e) => {
            e.preventDefault();
            const delta = e.deltaY > 0 ? 1 : -1;
            terminal.scrollLines(delta);
        }, { passive: false });
    }

    // Better terminal interaction
    terminal.onSelectionChange(() => {
        const selection = terminal.getSelection();
        if (selection) {
            terminal.element.style.cursor = 'text';
        } else {
            terminal.element.style.cursor = 'default';
        }
    });

    // Auto-fit when terminal is resized
    terminal.onResize(() => {
        if (fitAddon) {
            fitAddon.fit();
        }
    });

    fitAddon.fit();
    setupTerminalEventListeners();
}

function setupTerminalEventListeners() {
    terminal.attachCustomKeyEventHandler((e) => {
        if (e.ctrlKey && e.shiftKey) {
            if (e.code === 'KeyC' && e.type === 'keydown') {
                e.preventDefault();
                copyFromTerminal();
                return false;
            }
            if (e.code === 'KeyV' && e.type === 'keydown') {
                e.preventDefault();
                pasteToTerminal();
                return false;
            }
        }
        return true;
    });

    const terminalElement = document.getElementById('terminal');
    terminalElement.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        showTerminalContextMenu(e);
    });
}

function showTerminalContextMenu(e) {
    DOM.contextMenu.innerHTML = '';

    const createMenuItem = (text, icon, action) => {
        const button = document.createElement('button');
        button.className = 'context-menu-item';
        button.innerHTML = `<i class="context-menu-icon fa-solid ${icon}"></i> ${text}`;
        button.onclick = (event) => {
            event.stopPropagation();
            DOM.contextMenu.style.display = 'none';
            action();
        };
        return button;
    };

    const menuItems = [];
    menuItems.push(createMenuItem('Copy', 'fa-copy', copyFromTerminal));
    menuItems.push(createMenuItem('Paste', 'fa-paste', pasteToTerminal));

    const separator = document.createElement('div');
    separator.className = 'context-menu-separator';
    menuItems.push(separator);

    menuItems.push(createMenuItem('Clear', 'fa-ban', clearTerminal));
    menuItems.push(createMenuItem('Scroll to Top', 'fa-arrow-up', scrollToTop));
    menuItems.push(createMenuItem('Scroll to Bottom', 'fa-arrow-down', scrollToBottom));

    DOM.contextMenu.append(...menuItems);
    DOM.contextMenu.style.left = `${e.clientX}px`;
    DOM.contextMenu.style.top = `${e.clientY}px`;
    DOM.contextMenu.style.display = 'block';
}

function connectTerminalSocket() {
    socket = io('/terminal');
    socket.on('connect', () => {
        terminal.write('\r\n\x1b[32m✔\x1b[0m Terminal connected.\r\n$ ');
    });
    socket.on('output', (data) => {
        terminal.write(data);
    });
    terminal.onData((data) => {
        if (socket && socket.connected) {
            socket.emit('input', data);
        }
    });
    socket.on('disconnect', () => {
        terminal.write('\r\n\x1b[31m✖\x1b[0m Terminal disconnected.\r\n');
    });
}

function setupResizer() {
    const handleMouseMove = (e) => {
        const newWidth = Math.max(200, Math.min(window.innerWidth * 0.4, e.clientX));
        DOM.filePanel.style.width = `${newWidth}px`;
    };
    const handleMouseUp = () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        editor.resize();
        if (fitAddon) fitAddon.fit();
    };
    DOM.resizer.addEventListener('mousedown', (e) => {
        e.preventDefault();
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    });
}

function setupHorizontalResizer() {
    const resizer = DOM.resizerHorizontal;
    const handleMouseMove = (e) => {
        const mainPanelRect = DOM.mainPanel.getBoundingClientRect();
        const newTerminalHeight = mainPanelRect.bottom - e.clientY;
        const minHeight = 40;
        const maxHeight = mainPanelRect.height - 100;
        const clampedHeight = Math.max(minHeight, Math.min(newTerminalHeight, maxHeight));
        DOM.terminalContainer.style.height = `${clampedHeight}px`;
    };
    const handleMouseUp = () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
        // Use requestAnimationFrame for better timing
        requestAnimationFrame(() => {
            editor.resize();
            if (fitAddon) {
                fitAddon.fit();
            }
        });
    };
    resizer.addEventListener('mousedown', (e) => {
        e.preventDefault();
        document.addEventListener('mousemove', handleMouseMove);
        document.addEventListener('mouseup', handleMouseUp);
    });
}

function setupEventListeners() {
    document.addEventListener('click', (e) => {
        if (!DOM.contextMenu.contains(e.target)) {
            DOM.contextMenu.style.display = 'none';
        }
    });

    DOM.filePanel.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        const targetItem = e.target.closest('.tree-item');
        showContextMenu(e, targetItem);
    });

    document.addEventListener('keydown', e => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            saveCurrentFile();
        }
    });

    window.addEventListener('resize', () => {
        editor.resize();
        if (fitAddon) fitAddon.fit();
    });
}

function toggleTerminal() {
    const isHidden = DOM.mainPanel.classList.contains('terminal-hidden');
    DOM.mainPanel.classList.toggle('terminal-hidden');

    // Use requestAnimationFrame for better timing
    requestAnimationFrame(() => {
        editor.resize();
        if (fitAddon) {
            fitAddon.fit();
        }
        // Force terminal to recalculate its size
        if (!isHidden) {
            terminal.refresh(0, terminal.rows - 1);
        }
    });
}

function toggleSerialMonitor() {
    const serialWindow = document.getElementById('serial-monitor-window');

    // Nếu đang ẩn -> Hiện lên
    if (serialWindow.style.display === 'none') {
        serialWindow.style.display = 'flex';

        // Set vị trí mặc định nếu chưa có
        if (!serialWindow.style.top || !serialWindow.style.left) {
            serialWindow.style.top = '100px';
            serialWindow.style.right = '20px';
            serialWindow.style.left = 'auto'; // Reset left để dùng right
        }

        // ▼▼▼ THÊM ĐOẠN NÀY ĐỂ KÍCH HOẠT KÉO THẢ ▼▼▼
        makeDraggable(serialWindow);
        // ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        const portSelect = document.getElementById('serial-port-select');
        if (portSelect.options.length <= 1) {
            refreshSerialPorts();
        }
    }
    // Nếu đang hiện -> Ẩn đi
    else {
        serialWindow.style.display = 'none';
    }
}
function openSerialWindow() {
    const serialWindow = document.getElementById('serial-monitor-window');
    serialWindow.style.display = 'flex';

    // Load ports when opening
    refreshSerialPorts();

    // Make window draggable if not already done
    if (!serialWindow.hasAttribute('data-draggable')) {
        makeDraggable(serialWindow);
        serialWindow.setAttribute('data-draggable', 'true');
    }
}

function closeSerialWindow() {
    const serialWindow = document.getElementById('serial-monitor-window');

    // 1. Ẩn giao diện
    serialWindow.style.display = 'none';

    // 2. Ngắt kết nối socket (Để giải phóng tài nguyên server)
    if (socketSerial && socketSerial.connected) {
        socketSerial.disconnect();

        // Reset giao diện về trạng thái "Chưa kết nối" để lần sau mở lại
        const connectSerialBtn = document.getElementById('connect-serial-btn');
        const serialStatus = document.getElementById('serial-status');
        if (connectSerialBtn) {
            connectSerialBtn.textContent = '▶️ Connect';
            connectSerialBtn.disabled = false;
        }
        if (serialStatus) serialStatus.textContent = 'Disconnected';
    }
}

function minimizeSerialWindow() {
    const serialWindow = document.getElementById('serial-monitor-window');
    serialWindow.style.display = 'none';
}
function makeDraggable(element) {
    const header = element.querySelector('.floating-window-header');
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

    header.onmousedown = dragMouseDown;

    function dragMouseDown(e) {
        e = e || window.event;
        e.preventDefault();

        // --- [FIX CHÍNH XÁC] ---
        // 1. Lấy vị trí thực tế hiện tại của cửa sổ trên màn hình
        const rect = element.getBoundingClientRect();

        // 2. Gỡ bỏ thuộc tính 'right' đang ghim cửa sổ vào lề phải
        element.style.right = 'auto';

        // 3. Gán cứng vị trí hiện tại vào 'left' và 'top' để JS điều khiển
        element.style.left = rect.left + 'px';
        element.style.top = rect.top + 'px';
        // -----------------------

        // Lấy tọa độ chuột bắt đầu
        pos3 = e.clientX;
        pos4 = e.clientY;

        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
        e = e || window.event;
        e.preventDefault();

        // Tính toán khoảng cách di chuyển
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;

        // Cập nhật vị trí mới
        element.style.top = (element.offsetTop - pos2) + "px";
        element.style.left = (element.offsetLeft - pos1) + "px";
    }

    function closeDragElement() {
        // Dừng kéo thả
        document.onmouseup = null;
        document.onmousemove = null;
    }
}

function clearTerminal() {
    if (terminal) {
        terminal.clear();
        showNotification('Terminal cleared', 'success');
    }
}

function copyFromTerminal() {
    if (!terminal) return;

    const selection = terminal.hasSelection() ? terminal.getSelection() : null;
    if (!selection) {
        showNotification('Please select text first', 'info');
        return;
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(selection)
            .then(() => showNotification('Copied to clipboard!', 'success'))
            .catch(err => {
                console.error('Copy failed: ', err);
                showNotification('Copy failed. Please use Ctrl+Shift+C', 'error');
            });
    } else {
        // fallback if browser doesn't support navigator.clipboard
        try {
            const textarea = document.createElement('textarea');
            textarea.value = selection;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            showNotification('Copied to clipboard!', 'success');
        } catch (err) {
            console.error('Fallback copy failed: ', err);
            showNotification('Copy failed. Please use Ctrl+Shift+C', 'error');
        }
    }
}

function pasteToTerminal() {
    if (!terminal) return;

    navigator.clipboard.readText().then(text => {
        if (text && socket && socket.connected) {
            socket.emit('input', text);
        }
    }).catch(err => {
        console.error('Paste failed: ', err);
        showNotification('Paste failed. Permission might be denied.', 'error');
    });
}

function scrollToTop() {
    if (terminal) {
        terminal.scrollToTop();
    }
}

function scrollToBottom() {
    if (terminal) {
        terminal.scrollToBottom();
    }
}

// New function for copying from Serial Monitor
function copyFromSerialOutput() {
    const serialOutput = document.getElementById('serial-output');
    if (!serialOutput) return;

    const selection = window.getSelection();
    let textToCopy = '';

    if (selection.toString()) {
        textToCopy = selection.toString();
    } else {
        // If nothing selected, copy all text
        textToCopy = serialOutput.textContent;
    }

    if (!textToCopy.trim()) {
        showNotification('No text to copy', 'info');
        return;
    }

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(textToCopy)
            .then(() => showNotification('Serial output copied to clipboard!', 'success'))
            .catch(err => {
                console.error('Copy failed: ', err);
                fallbackCopy(textToCopy);
            });
    } else {
        fallbackCopy(textToCopy);
    }
}

function fallbackCopy(text) {
    try {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showNotification('Serial output copied to clipboard!', 'success');
    } catch (err) {
        console.error('Fallback copy failed: ', err);
        showNotification('Copy failed. Please select text manually and use Ctrl+C', 'error');
    }
}

async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(endpoint, options);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        if (data.error) throw new Error(data.error);
        return data;
    } catch (error) {
        showNotification(`API Error: ${error.message}`, 'error');
        throw error;
    }
}

function showNotification(message, type = 'success') {
    const alertType = type === 'error' ? 'danger' : (type === 'info' ? 'primary' : 'success');
    const toast = document.createElement('div');
    toast.className = `toast show align-items-center text-bg-${alertType} border-0`;
    toast.innerHTML = `
                <div class="d-flex">
                    <div class="toast-body">${message}</div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.parentElement.parentElement.remove()"></button>
                </div>
            `;
    DOM.toastContainer.appendChild(toast);
    setTimeout(() => {
        if (toast.parentNode) {
            toast.remove();
        }
    }, 4000);
}

function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();

    // Map định nghĩa full class để phân biệt Brand và Solid
    const map = {
        // --- Nhóm Brands (Logo) ---
        js: 'fa-brands fa-js',
        html: 'fa-brands fa-html5',
        css: 'fa-brands fa-css3-alt',
        py: 'fa-brands fa-python',
        md: 'fa-brands fa-markdown',
        dockerfile: 'fa-brands fa-docker',

        // --- Nhóm Solid (Hệ thống) ---
        sh: 'fa-solid fa-terminal',       // <--- Đã fix cho file .sh
        ino: 'fa-solid fa-microchip',     // <--- Đã fix cho file .ino
        json: 'fa-solid fa-file-code',
        cpp: 'fa-solid fa-file-code',
        c: 'fa-solid fa-file-code',
        h: 'fa-solid fa-file-code',
        txt: 'fa-solid fa-file-lines'
    };

    // Lấy class tương ứng, nếu không có thì dùng icon file mặc định
    const iconClass = map[ext] || 'fa-solid fa-file';

    return { icon: iconClass, color: '' };
}

async function refreshRootFiles() {
    DOM.fileTreeRoot.innerHTML = '<div style="padding: 8px; color: #888;"><i>Loading...</i></div>';
    DOM.refreshIcon.classList.add('fa-spin');
    try {
        await loadFolderContents('.', DOM.fileTreeRoot);
    } finally {
        DOM.refreshIcon.classList.remove('fa-spin');
    }
}

async function loadFolderContents(path, parentElement) {
    try {
        const data = await apiCall(`/user/${username}/files`, {
            method: "POST", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ path: path })
        });
        parentElement.innerHTML = '';
        if (data.files?.length > 0) {
            data.files.forEach(item => parentElement.appendChild(createTreeItem(item, path)));
        } else if (path !== '.') {
            parentElement.innerHTML = '<li style="padding-left: 20px; color: #888; font-style: italic;">(empty)</li>';
        }
    } catch (e) {
        parentElement.innerHTML = `<div style="padding: 8px; color: #f85149;"><i>Failed to load files.</i></div>`;
    }
}

function createTreeItem(item, parentPath) {
    const li = document.createElement('li');
    const fullPath = parentPath === '.' ? item.name : `${parentPath}/${item.name}`;
    const itemDiv = document.createElement('div');
    itemDiv.className = `tree-item ${item.is_dir ? 'is-folder' : 'is-file'}`;
    itemDiv.dataset.path = fullPath;
    const iconData = item.is_dir ? { icon: 'fa-solid fa-folder', color: '#58a6ff' } : getFileIcon(item.name);
    itemDiv.innerHTML = `<div class="tree-chevron"><i class="fa-solid fa-chevron-right fa-xs"></i></div><div class="tree-icon"><i class="${iconData.icon}" style="color: ${iconData.color || 'inherit'}"></i></div><span class="tree-name">${item.name}</span>`;
    if (!item.is_dir) itemDiv.querySelector('.tree-chevron').style.visibility = 'hidden';
    li.appendChild(itemDiv);
    itemDiv.addEventListener('click', () => {
        if (selectedTreeItem) selectedTreeItem.classList.remove('is-selected');
        selectedTreeItem = itemDiv;
        itemDiv.classList.add('is-selected');
        item.is_dir ? toggleFolder(li) : openFile(fullPath, item.name);
    });
    return li;
}

function toggleFolder(liElement) {
    const isOpen = liElement.classList.toggle('is-open');
    const itemDiv = liElement.querySelector('.tree-item');
    itemDiv.classList.toggle('is-open');
    if (isOpen) {
        let childUl = liElement.querySelector('ul');
        if (!childUl) {
            childUl = document.createElement('ul');
            liElement.appendChild(childUl);
        }
        loadFolderContents(itemDiv.dataset.path, childUl);
    }
}

async function createNewItem(type, parentPath = '.', name = '') {
    if (!name) {
        // Sử dụng modal đẹp thay vì prompt mặc định
        showFileCreationModal(type, parentPath);
        return;
    }
    const url = type === 'folder' ? `/user/${username}/create-folder` : `/user/${username}/editor/save`;
    const body = type === 'folder' ? { folder_name: name, path: parentPath } : { filename: name, path: parentPath, content: '' };
    try {
        await apiCall(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
        showNotification(`'${name}' created successfully.`, 'success');
        if (parentPath === '.') {
            refreshRootFiles();
        } else {
            const parentFolderLi = document.querySelector(`.tree-item[data-path="${parentPath}"]`)?.parentElement;
            if (parentFolderLi && parentFolderLi.classList.contains('is-open')) {
                const childUl = parentFolderLi.querySelector('ul');
                if (childUl) loadFolderContents(parentPath, childUl);
            } else { refreshRootFiles(); }
        }
    } catch (error) { }
}

function showContextMenu(e, targetItem) {
    DOM.contextMenu.innerHTML = '';
    const path = targetItem?.dataset.path;
    const isFolder = targetItem?.classList.contains('is-folder');
    const createMenuItem = (text, icon, action, isDanger = false) => {
        const button = document.createElement('button');
        button.className = `context-menu-item ${isDanger ? 'danger' : ''}`;
        button.innerHTML = `<i class="context-menu-icon fa-solid ${icon}"></i> ${text}`;
        button.onclick = (event) => {
            event.stopPropagation();
            DOM.contextMenu.style.display = 'none';
            action();
        };
        return button;
    };
    const menuItems = [];
    if (isFolder) {
        menuItems.push(createMenuItem('New File', 'fa-file-plus', () => createNewItem('file', path)));
        menuItems.push(createMenuItem('New Folder', 'fa-folder-plus', () => createNewItem('folder', path)));
        menuItems.push(createMenuItem('Upload Files', 'fa-upload', () => handleUploadClick(path)));
    } else if (!targetItem) {
        menuItems.push(createMenuItem('New File', 'fa-file-plus', () => createNewItem('file')));
        menuItems.push(createMenuItem('New Folder', 'fa-folder-plus', () => createNewItem('folder')));
        menuItems.push(createMenuItem('Upload Files', 'fa-upload', () => handleUploadClick('.')));
    }
    if (targetItem) {
        const separator = document.createElement('div');
        separator.className = 'context-menu-separator';
        menuItems.push(separator);
        menuItems.push(createMenuItem('Rename', 'fa-i-cursor', () => handleRenameItem(path)));
        menuItems.push(createMenuItem('Delete', 'fa-trash', () => handleDeleteItem(path), true));
    }
    DOM.contextMenu.append(...menuItems);
    DOM.contextMenu.style.left = `${e.clientX}px`;
    DOM.contextMenu.style.top = `${e.clientY}px`;
    DOM.contextMenu.style.display = 'block';
}

// 1. Mở Modal (Thay thế prompt)
function handleRenameItem(oldPath) {
    currentRenamePath = oldPath;
    const oldName = oldPath.split('/').pop();

    // Reset và điền tên cũ
    DOM.renameInput.value = oldName;
    DOM.renameModal.style.display = 'flex';

    // Focus vào ô nhập
    setTimeout(() => {
        DOM.renameInput.focus();
        DOM.renameInput.select();
    }, 100);

    // Bắt sự kiện Enter trong ô nhập
    DOM.renameInput.onkeydown = (e) => {
        if (e.key === 'Enter') performRename();
        if (e.key === 'Escape') closeRenameModal();
    };
}

// 2. Đóng Modal
function closeRenameModal() {
    DOM.renameModal.style.display = 'none';
    currentRenamePath = null;
    DOM.renameInput.value = '';
}
// Them Ham handleUpLoadClick bi thieu 
function handleUpLoadClick(path) {
    uploadPath = path || '.'
    DOM.fileUploadInput.click();
}
// 3. Xử lý đổi tên (Gọi API)
async function performRename() {
    const newName = DOM.renameInput.value.trim();
    const oldPath = currentRenamePath;

    if (!newName || !oldPath) return;

    const oldName = oldPath.split('/').pop();
    if (newName === oldName) {
        closeRenameModal();
        return;
    }

    // Khóa nút để tránh bấm liên tục
    DOM.confirmRenameBtn.disabled = true;
    DOM.confirmRenameBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> ...';

    try {
        await apiCall(`/user/${username}/rename-item`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ old_path: oldPath, new_name: newName })
        });

        showNotification('Đổi tên thành công!', 'success');

        // Nếu file đang mở bị đổi tên -> đóng tab cũ
        if (openFiles.has(oldPath)) {
            // Tìm tab trên giao diện và đóng nó (giả lập click nút X)
            const tabElement = Array.from(DOM.editorTabs.children).find(t => t.title === oldPath);
            if (tabElement && tabElement.querySelector('.close-icon')) {
                // Đóng tab cũ
                closeTab({ stopPropagation: () => { } }, oldPath, true);
            }
        }

        refreshRootFiles();
        closeRenameModal();
    } catch (error) {
        // Lỗi đã được apiCall xử lý hiển thị
    } finally {
        DOM.confirmRenameBtn.disabled = false;
        DOM.confirmRenameBtn.innerHTML = 'Lưu';
    }
}

function handleDeleteItem(path) {
    showDeleteConfirmationModal(path);
}
function showDeleteConfirmationModal(path) {
    pendingDeleteItemPath = path;
    // Cập nhật nội dung thông báo cho cụ thể hơn
    DOM.deleteConfirmationMessage.innerHTML = `Bạn có chắc chắn muốn xóa "<strong>${path}</strong>"?<br>Hành động này không thể hoàn tác.`;
    DOM.deleteConfirmationModal.style.display = 'flex';
}

function cancelDelete() {
    DOM.deleteConfirmationModal.style.display = 'none';
    pendingDeleteItemPath = null;
}

async function confirmDelete() {
    if (!pendingDeleteItemPath) return;

    const pathToDelete = pendingDeleteItemPath;

    // Đóng modal và reset trạng thái trước khi gọi API
    DOM.deleteConfirmationModal.style.display = 'none';
    pendingDeleteItemPath = null;

    try {
        await apiCall(`/user/${username}/delete-item`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path: pathToDelete })
        });

        // Nếu file đang xóa được mở, hãy đóng tab của nó
        if (openFiles.has(pathToDelete)) {
            // Tham số 'true' để buộc đóng tab mà không hỏi lại
            closeTab({ stopPropagation: () => { } }, pathToDelete, true);
        }

        showNotification(`'${pathToDelete}' đã được xóa.`, 'success');
        refreshRootFiles(); // Làm mới cây thư mục
    } catch (error) {
        // Lỗi đã được xử lý trong hàm apiCall
    }
}
async function handleFileUpload(files) {
    if (files.length === 0) return;
    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }
    formData.append('path', uploadPath);
    showNotification(`Uploading ${files.length} file(s)...`, 'info');
    try {
        await apiCall(`/user/${username}/upload-files`, { method: 'POST', body: formData });
        showNotification('Upload complete!', 'success');
        const parentFolderLi = document.querySelector(`.tree-item[data-path="${uploadPath}"]`)?.parentElement;
        if (uploadPath === '.' || !parentFolderLi) {
            refreshRootFiles();
        } else if (parentFolderLi.classList.contains('is-open')) {
            const childUl = parentFolderLi.querySelector('ul');
            if (childUl) loadFolderContents(uploadPath, childUl);
        }
    } catch (error) { }
    DOM.fileUploadInput.value = '';
}

function openWelcomeTab() {
    const content = `// Welcome to CodeSpace IDE!\n// Features:\n// - Full terminal support with copy/paste\n// - Scrollable terminal with mouse wheel\n// - Context menus\n// - File management\n// - Arduino/ESP compilation\n\nconsole.log("Happy Coding!");`;
    if (!openFiles.has('Welcome')) {
        openFiles.set('Welcome', { content, saved: true, shortName: 'Welcome', path: '.' });
    }
    switchToFile('Welcome');
}

async function openFile(fullPath, shortName, autoSwitch = true) {
    if (openFiles.has(fullPath)) {
        if (autoSwitch) switchToFile(fullPath);
        return;
    }
    const parentPath = fullPath.includes('/') ? fullPath.split('/').slice(0, -1).join('/') : '.';
    try {
        const data = await apiCall(`/user/${username}/editor/load`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: shortName, path: parentPath })
        });
        openFiles.set(fullPath, {
            content: data.content,
            saved: true,
            shortName,
            path: parentPath
        });
        if (autoSwitch) switchToFile(fullPath);
        else renderTabs();
    } catch (error) { /* Error handled by apiCall */ }
}

function switchToFile(fullPathKey) {
    if (!openFiles.has(fullPathKey)) return;
    currentFile = fullPathKey;
    const fileData = openFiles.get(fullPathKey);
    
    isSystemChange = true;
    editor.setValue(fileData.content, -1);
    isSystemChange = false;
    
    const modelist = ace.require("ace/ext/modelist");
    editor.session.setMode(modelist.getModeForPath(fileData.shortName).mode);
    editor.focus();
    renderTabs();
    saveIDEState();
}

function renderTabs() {
    DOM.editorTabs.innerHTML = '';
    for (const [key, data] of openFiles.entries()) {
        const tab = document.createElement('button');
        tab.className = `editor-tab ${key === currentFile ? 'active' : ''}`;
        tab.title = key;
        tab.innerHTML = `<span>${data.shortName}${data.saved ? '' : ' •'}</span>`;
        tab.onclick = () => switchToFile(key);
        if (key !== 'Welcome') {
            const closeIcon = document.createElement('i');
            closeIcon.className = 'fa-solid fa-times close-icon';
            closeIcon.onclick = (e) => closeTab(e, key);
            tab.appendChild(closeIcon);
        }
        DOM.editorTabs.appendChild(tab);
    }
    DOM.saveButton.textContent = (currentFile && openFiles.get(currentFile)?.saved === false) ? 'Save*' : 'Save';
}

function updateTabAppearance(fullPathKey) {
    const tabEl = Array.from(DOM.editorTabs.children).find(t => t.title === fullPathKey);
    if (tabEl && openFiles.has(fullPathKey)) {
        const fileData = openFiles.get(fullPathKey);
        tabEl.querySelector('span').textContent = fileData.shortName + (fileData.saved ? '' : ' •');
    }
}

function closeTab(e, fullPathKey, force = false) {
    e.stopPropagation();
    const fileData = openFiles.get(fullPathKey);
    if (!force && fileData && !fileData.saved) {
        // Show custom modal instead of confirm()
        showUnsavedChangesModal(fullPathKey);
        return;
    }
    performCloseTab(fullPathKey);
}

function showUnsavedChangesModal(fullPathKey) {
    pendingCloseFile = fullPathKey;
    const fileData = openFiles.get(fullPathKey);
    const fileName = fileData ? fileData.shortName : fullPathKey.split('/').pop();
    DOM.unsavedChangesMessage.textContent = `File "${fileName}" có thay đổi chưa lưu. Đóng file này?`;
    DOM.unsavedChangesModal.style.display = 'flex';
}

function cancelCloseFile() {
    DOM.unsavedChangesModal.style.display = 'none';
    pendingCloseFile = null;
}

function confirmCloseFile() {
    if (pendingCloseFile) {
        performCloseTab(pendingCloseFile);
        DOM.unsavedChangesModal.style.display = 'none';
        pendingCloseFile = null;
    }
}

function performCloseTab(fullPathKey) {
    openFiles.delete(fullPathKey);
    if (currentFile === fullPathKey) {
        const keys = Array.from(openFiles.keys());
        const newCurrentFile = keys.length > 0 ? keys[keys.length - 1] : null;
        if (newCurrentFile) {
            switchToFile(newCurrentFile);
        } else {
            openWelcomeTab();
        }
    } else {
        renderTabs();
        saveIDEState();
    }
}

async function saveCurrentFile() {
    if (!currentFile || currentFile === 'Welcome') return;
    const fileData = openFiles.get(currentFile);
    if (!fileData || fileData.saved) return;
    const content = editor.getValue();
    try {
        await apiCall(`/user/${username}/editor/save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: fileData.shortName,
                content: content,
                path: fileData.path
            })
        });
        fileData.content = content;
        fileData.saved = true;
        updateTabAppearance(currentFile);
        DOM.saveButton.textContent = 'Save';
        showNotification(`Saved ${fileData.shortName}`, 'success');
    } catch (error) {
        showNotification(`Lỗi lưu bài: ${error.message}`, 'error');
    }
}

async function compileCode(event) {
    const compileBtn = event ? (event.currentTarget || event.target) : null;
    const originalBtnHTML = compileBtn ? compileBtn.innerHTML : "Biên dịch";
    
    if (compileBtn) {
        compileBtn.disabled = true;
        compileBtn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Đang xử lý...`;
    }

    if (!currentFile || currentFile === 'Welcome') {
        showNotification('Vui lòng mở một file .ino để biên dịch!', 'error');
        if (compileBtn) {
            compileBtn.disabled = false;
            compileBtn.innerHTML = originalBtnHTML;
        }
        return;
    }
    if (!currentFile.toLowerCase().endsWith('.ino')) {
        showNotification('Chỉ có thể biên dịch file .ino (Arduino sketch)!', 'error');
        if (compileBtn) {
            compileBtn.disabled = false;
            compileBtn.innerHTML = originalBtnHTML;
        }
        return;
    }
    //Logic auto save before compile or loaded
    if (openFiles.has(currentFile) && !openFiles.get(currentFile).saved) {
        terminal.write('\r\n\x1b[90m[IDE]\x1b[0m File chưa được lưu. Tự động lưu...\r\n');
        await saveCurrentFile() // save and continue
    }

    const boardSelector = document.getElementById('boardSelector');
    // Tự động phân tích mã nguồn để chọn kiến trúc phù hợp
    let boardFqbn = boardSelector ? boardSelector.value : 'arduino:avr:uno';
    if (editor && editor.getValue) {
        const codeContent = editor.getValue();
        const esp32Keywords = ['freertos', 'WiFi.h', 'ESP32', 'xTaskCreate', 'xQueue', 'TaskHandle_t', 'QueueHandle_t', 'vTaskDelay', 'portMAX_DELAY'];
        if (esp32Keywords.some(kw => codeContent.includes(kw))) {
            boardFqbn = 'esp32:esp32:esp32';
        }
    }
    const sketchPath = currentFile;

    terminal.write(`\r\n\x1b[1;33m[COMPILE]\x1b[0m Đang biên dịch '${sketchPath}' cho ${boardFqbn}...\r\n`);

    try {
        const response = await fetch(`/user/${username}/compile`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sketch_path: sketchPath, board_fqbn: boardFqbn })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || `Server responded with status ${response.status}`);
        }
        if (data.success) {
            terminal.write(`\x1b[1;32m✓ Biên dịch thành công!\x1b[0m\r\n`);
            if (data.memory_analysis) {
                writeMemoryUsageToTerminal(data.memory_analysis);
            }
            showNotification('Biên dịch thành công!', 'success');
        } else {
            terminal.write(`\x1b[1;31m✗ Biên dịch thất bại!\x1b[0m\r\n`);
            if (data.error_analysis) {
                writeErrorAnalysisToTerminal(data.error_analysis);
            } else {
                // Lọc chỉ giữ lại dòng lỗi/cảnh báo có ý nghĩa
                const rawOutput = data.output || '';
                const filteredLines = rawOutput.split('\n').filter(line => {
                    const l = line.trim();
                    if (!l) return false;
                    // Chỉ giữ dòng error/warning/note từ file .ino hoặc thông báo lỗi chung
                    if (l.includes(': error:') || l.includes(': warning:') || l.includes(': note:')) return true;
                    if (l.startsWith('Error during build')) return true;
                    if (l.startsWith('exit status')) return true;
                    return false;
                });
                if (filteredLines.length > 0) {
                    terminal.write(`\r\n\x1b[90m--- Chi tiết lỗi ---\x1b[0m\r\n`);
                    filteredLines.forEach(line => {
                        if (line.includes(': error:')) {
                            terminal.write(`  \x1b[1;31m❌ ${line}\x1b[0m\r\n`);
                        } else if (line.includes(': warning:')) {
                            terminal.write(`  \x1b[1;33m⚠ ${line}\x1b[0m\r\n`);
                        } else if (line.includes(': note:')) {
                            terminal.write(`  \x1b[36m💡 ${line}\x1b[0m\r\n`);
                        } else {
                            terminal.write(`  \x1b[90m${line}\x1b[0m\r\n`);
                        }
                    });
                } else {
                    terminal.write(`\x1b[90m${rawOutput.substring(0, 500)}\x1b[0m\r\n`);
                }
            }
            const errorCount = data.error_analysis ? data.error_analysis.error_count : 0;
            const warningCount = data.error_analysis ? data.error_analysis.warning_count : 0;
            showNotification(`Biên dịch thất bại! ${errorCount} lỗi, ${warningCount} cảnh báo`, 'error');
        }
    } catch (error) {
        const errorMessage = error.message.includes('not valid JSON')
            ? 'Phản hồi từ server không hợp lệ. Vui lòng đăng nhập lại.'
            : error.message;
        terminal.write(`\r\n\x1b[1;31m✗ Lỗi hệ thống: ${errorMessage}\x1b[0m\r\n`);
        showNotification(`Lỗi hệ thống: ${errorMessage}`, 'error');
        console.error("Compile API call failed:", error);
    } finally {
        compileBtn.disabled = false;
        compileBtn.innerHTML = originalBtnHTML;
        terminal.write(`\r\n$ `); // Show new prompt
        terminal.scrollToBottom();
    }
}

function writeMemoryUsageToTerminal(analysis) {
    const formatBytes = (bytes) => bytes.toLocaleString('en-US');
    const createProgressBar = (percent) => {
        const totalBars = 20;
        const filledBars = Math.round((percent / 100) * totalBars);
        const emptyBars = totalBars - filledBars;
        return `\x1b[90m[\x1b[0m` + `\x1b[32m█\x1b[0m`.repeat(filledBars) + `\x1b[90m-\x1b[0m`.repeat(emptyBars) + `\x1b[90m]\x1b[0m`;
    };

    terminal.write(`\r\n\x1b[1;34m📊 Thống kê bộ nhớ:\x1b[0m\r\n`);
    if (analysis.flash) {
        const f = analysis.flash;
        terminal.write(`   \x1b[36mFlash:\x1b[0m ${createProgressBar(f.percent)} ${f.percent}% (${formatBytes(f.used)} / ${formatBytes(f.total)} bytes)\r\n`);
    }
    if (analysis.ram) {
        const r = analysis.ram;
        terminal.write(`   \x1b[35mRAM:  \x1b[0m ${createProgressBar(r.percent)} ${r.percent}% (${formatBytes(r.used)} / ${formatBytes(r.total)} bytes)\r\n`);
    }
}

function writeErrorAnalysisToTerminal(analysis) {
    if (analysis.errors && analysis.errors.length > 0) {
        terminal.write(`\r\n\x1b[1;31m━━━ ${analysis.error_count} LỖI CẦN SỬA ━━━\x1b[0m\r\n`);
        analysis.errors.forEach((error, index) => {
            terminal.write(` \x1b[90m${index + 1}.\x1b[0m \x1b[33m${error.file}:${error.line}:${error.column}\x1b[0m\r\n`);
            terminal.write(`    \x1b[31merror:\x1b[0m ${error.message}\r\n\r\n`);
        });
    }
    if (analysis.warnings && analysis.warnings.length > 0) {
        terminal.write(`\r\n\x1b[1;33m━━━ ${analysis.warning_count} CẢNH BÁO ━━━\x1b[0m\r\n`);
        analysis.warnings.forEach((warning, index) => {
            terminal.write(` \x1b[90m${index + 1}.\x1b[0m \x1b[33m${warning.file}:${warning.line}:${warning.column}\x1b[0m\r\n`);
            terminal.write(`    \x1b[33mwarning:\x1b[0m ${warning.message}\r\n\r\n`);
        });
    }
}

// Logic Upload & Serial Monitor rác đã được dọn sạch để chuyển Server sang Full AI-Native

function escapeHtml(text) {
    if (typeof text !== 'string') return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
function toggleMissionsModal() {
    const wrapper = document.getElementById('missions-modal-wrapper');
    const iframe = document.getElementById('missions-iframe');
    const loader = document.getElementById('missions-iframe-loader');

    if (wrapper.style.display === 'none' || wrapper.style.display === '') {
        wrapper.style.display = 'flex';
        if (!iframe.src || iframe.src.includes('about:blank')) {
            iframe.src = window.userMissionsUrl;
        }
    } else {
        wrapper.style.display = 'none';
    }
}

// ── MISSIONS SYNC: Badge + Countdown + Submit từ IDE ──
let _ideMissionTimer = null;
let _ideActiveMission = null;

async function syncMissionsToIDE() {
    try {
        const res = await fetch('/user/api/my-missions');
        const missions = await res.json();
        const now = Date.now();
        const active = missions.filter(m => {
            const s = new Date(m.start_time).getTime();
            const e = new Date(m.end_time).getTime();
            return !m.submitted && now >= s && now <= e;
        });
        const total = missions.filter(m => {
            const s = new Date(m.start_time).getTime();
            const e = new Date(m.end_time).getTime();
            return !m.submitted && now <= e;
        });

        // Badge trên nút Missions
        const badge = document.getElementById('missionsBadge');
        if (badge) {
            if (total.length > 0) {
                badge.textContent = total.length;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }

        // Countdown mini + nút submit
        const bar = document.getElementById('miniExamBar');
        const btnSubmit = document.getElementById('btnSubmitMission');
        if (active.length > 0) {
            _ideActiveMission = active[0];
            document.getElementById('miniExamName').textContent = active[0].name;
            bar.style.display = 'inline-flex';
            btnSubmit.style.display = '';
            if (!_ideMissionTimer) {
                _ideMissionTimer = setInterval(tickIDECountdown, 1000);
                tickIDECountdown();
            }
        } else {
            _ideActiveMission = null;
            if (bar) bar.style.display = 'none';
            if (btnSubmit) btnSubmit.style.display = 'none';
            if (_ideMissionTimer) { clearInterval(_ideMissionTimer); _ideMissionTimer = null; }
        }
    } catch (e) { /* im lặng */ }
}

function tickIDECountdown() {
    if (!_ideActiveMission) return;
    const end = new Date(_ideActiveMission.end_time).getTime();
    const remaining = end - Date.now();
    const el = document.getElementById('miniExamCountdown');
    if (remaining <= 0) {
        if (el) el.textContent = '00:00:00';
        clearInterval(_ideMissionTimer);
        _ideMissionTimer = null;
        return;
    }
    const h = Math.floor(remaining / 3600000);
    const m = Math.floor((remaining % 3600000) / 60000);
    const s = Math.floor((remaining % 60000) / 1000);
    const pad = n => String(n).padStart(2, '0');
    if (el) {
        el.textContent = `${pad(h)}:${pad(m)}:${pad(s)}`;
        el.style.color = remaining < 300000 ? '#ef4444' : remaining < 900000 ? '#f59e0b' : '#7c6af7';
    }
}

async function submitActiveMission() {
    if (!_ideActiveMission) {
        showNotification('Không có bài thi nào đang diễn ra!', 'warning');
        return;
    }
    const missionId = _ideActiveMission.id;
    const missionName = _ideActiveMission.name;

    const result = await Swal.fire({
        title: 'Nộp bài thi?',
        text: `Bạn muốn nộp bài "${missionName}"? Sau khi nộp, không thể chỉnh sửa nữa.`,
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#7c6af7',
        cancelButtonText: 'Chưa, tiếp tục làm',
        confirmButtonText: 'Nộp bài ngay!'
    });
    if (!result.isConfirmed) return;

    try {
        const res = await fetch(`/user/api/missions/${missionId}/submit`, { method: 'POST' });
        const data = await res.json();
        if (data.success || (data.error && data.error.includes('already submitted'))) {
            // Hiện popup loading chờ AI chấm điểm
            Swal.fire({
                title: '⏳ Đang chấm điểm...',
                html: '<p style="color:#999;font-size:0.9rem;">Vui lòng chờ trong giây lát.</p><div style="margin-top:12px"><i class="fa-solid fa-circle-notch fa-spin fa-2x" style="color:#7c6af7"></i></div>',
                allowOutsideClick: false,
                showConfirmButton: false,
                background: '#1a1a2e',
                color: '#e0e0e0',
                backdrop: `rgba(10,10,30,0.6) blur(4px)`,
                customClass: { popup: 'swal-no-scroll' }
            });

            // Poll chờ kết quả AI
            let pollCount = 0;
            const pollInterval = setInterval(async () => {
                pollCount++;
                try {
                    const mRes = await fetch('/user/api/my-missions');
                    const missions = await mRes.json();
                    const m = missions.find(x => x.id === missionId);

                    if ((m && m.submission && m.submission.score !== null) || pollCount >= 12) {
                        clearInterval(pollInterval);
                        if (m && m.submission && m.submission.score !== null) {
                            const score = m.submission.score;
                            const feedback = m.submission.ai_feedback || m.submission.feedback || 'Không có nhận xét.';
                            const scoreColor = score >= 7 ? '#22c55e' : score >= 5 ? '#f59e0b' : '#ef4444';
                            Swal.fire({
                                title: `<span style="font-size:3rem;font-weight:900;color:${scoreColor}">${score.toFixed(1)}</span><span style="color:#888;font-size:1.2rem"> / 10</span>`,
                                html: `<h3 style="margin:8px 0;color:#ccc;">${escapeHtml(missionName)}</h3>
                                               <div style="text-align:left;padding:14px 18px;background:rgba(255,255,255,0.03);border-radius:12px;border:1px solid rgba(124,106,247,0.3);box-shadow:inset 0 0 10px rgba(124,106,247,0.1);margin-top:15px;font-size:0.85rem;color:#ccc;line-height:1.7;max-height:180px;overflow-y:auto;">💬 <b>AI Nhận xét:</b><br><span style="color:#aaa;">${escapeHtml(feedback).replace(/\n/g, '<br>')}</span></div>`,
                                icon: score >= 5 ? 'success' : 'warning',
                                confirmButtonColor: '#7c6af7',
                                confirmButtonText: 'Đóng',
                                background: '#1a1a2e',
                                color: '#e0e0e0',
                                backdrop: `rgba(10,10,30,0.6) blur(4px)`,
                                customClass: { popup: 'swal-no-scroll' }
                            });
                        } else {
                            Swal.fire({
                                icon: 'info',
                                title: 'Đã gửi bài thành công!',
                                text: 'AI xử lý chậm hơn dự kiến. Bấm Missions để xem điểm sau.',
                                confirmButtonColor: '#7c6af7',
                                background: '#1a1a2e',
                                color: '#e0e0e0',
                                backdrop: `rgba(10,10,30,0.6) blur(4px)`,
                                customClass: { popup: 'swal-no-scroll' }
                            });
                        }
                        syncMissionsToIDE();
                        const iframe = document.getElementById('missions-iframe');
                        if (iframe && iframe.src) iframe.src = iframe.src;
                    }
                } catch (e) { /* tiếp tục poll */ }
            }, 4000);
        } else {
            Swal.fire({ icon: 'error', title: 'Lỗi', text: data.error || 'Không thể nộp bài' });
        }
    } catch (e) {
        Swal.fire({ icon: 'error', title: 'Lỗi kết nối', text: 'Không thể liên hệ server' });
    }
}

// Khởi chạy sync khi IDE load xong
syncMissionsToIDE();
setInterval(syncMissionsToIDE, 15000);