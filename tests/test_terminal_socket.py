from sockets import terminal as terminal_socket


class FakeChannel:
    def __init__(self):
        self.active = True
        self.sent = []
        self.resized = None
        self.closed = False

    def recv_ready(self):
        return False

    def send(self, data):
        self.sent.append(data)

    def resize_pty(self, width, height):
        self.resized = (width, height)

    def close(self):
        self.active = False
        self.closed = True


class FakeSshClient:
    def __init__(self, channel):
        self.channel = channel
        self.closed = False
        self.invoke_args = None

    def invoke_shell(self, **kwargs):
        self.invoke_args = kwargs
        return self.channel

    def close(self):
        self.closed = True


def test_terminal_socket_connect_input_resize_disconnect(app, client, monkeypatch):
    from app import socketio

    channel = FakeChannel()
    ssh_client = FakeSshClient(channel)

    monkeypatch.setattr(terminal_socket, "get_ssh_client", lambda username: ssh_client)
    monkeypatch.setattr(terminal_socket, "log_action", lambda *args, **kwargs: None)
    terminal_socket.terminal_sessions.clear()

    with client.session_transaction() as sess:
        sess["username"] = "socket_user"
        sess["role"] = "user"

    socket_client = socketio.test_client(app, flask_test_client=client, namespace="/terminal")

    assert socket_client.is_connected("/terminal") is True
    assert ssh_client.invoke_args["term"] == "xterm-256color"
    assert len(terminal_socket.terminal_sessions) == 1

    socket_client.emit("input", "ls\n", namespace="/terminal")
    assert channel.sent == ["ls\n"]

    socket_client.emit("resize", {"cols": 140, "rows": 40}, namespace="/terminal")
    assert channel.resized == (140, 40)

    socket_client.disconnect(namespace="/terminal")
    assert channel.closed is True
    assert ssh_client.closed is True
    assert terminal_socket.terminal_sessions == {}


def test_terminal_socket_rejects_unauthenticated(app):
    from app import socketio

    socket_client = socketio.test_client(app, namespace="/terminal")

    assert socket_client.is_connected("/terminal") is False
