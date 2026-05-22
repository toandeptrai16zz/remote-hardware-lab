# Terminal SSH Tren Web

Nguon doi chieu code:

- `static/js/ide.js::connectTerminalSocket`
- `sockets/terminal.py::register_terminal_handlers`
- `services/ssh_manager.py::get_ssh_client`

## Noi dung slide dung voi code hien tai

**Terminal SSH Tren Web**  
Cau noi xterm.js -> Socket.IO -> Paramiko SSH -> Sandbox Container

- xterm.js nhan ky tu tu trinh duyet va gui qua namespace `/terminal`, event `input`.
- Backend Flask-SocketIO lay session user, mo SSH toi container bang `get_ssh_client(username)`.
- Backend tao PTY bang `invoke_shell(term='xterm-256color', width=120, height=32)`.
- Background task doc lien tuc SSH channel, moi lan `recv(1024)` bytes va emit event `output` ve dung `request.sid`.
- Frontend nhan event `output` va ghi vao xterm.js bang `terminal.write(data)`.
- Khi kich thuoc terminal thay doi, frontend emit event `resize`, backend goi `chan.resize_pty(width=cols, height=rows)`.
- Khi disconnect, backend dong SSH channel va SSH client theo `request.sid`.

## Diem can tranh ghi sai

- Khong ghi event `terminal_input`/`terminal_output`; code hien tai dung `input` va `output`.
- Khong ghi terminal doc chunk 4096 bytes; code terminal hien tai dung `chan.recv(1024)`. Con 4096 bytes nam o Serial Monitor.
- Co the ghi "persistent per-socket session" thay vi "persistent global connection", vi session duoc map theo `request.sid`.

## File hinh

`docs/reports/web_terminal_ssh_flow_2026-05-22.svg`
