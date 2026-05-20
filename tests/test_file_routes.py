from io import BytesIO

import pytest


class FakeFile:
    def __init__(self, content=b""):
        self.content = content
        self.written = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        return self.content

    def write(self, content):
        self.written = content


class FakeSftp:
    def __init__(self):
        self.renamed = None
        self.mkdir_path = None
        self.uploaded = []
        self.opened = []

    def open(self, path, mode="r"):
        self.opened.append((path, mode))
        if "r" in mode:
            return FakeFile(b"hello")
        return FakeFile()

    def stat(self, path):
        raise FileNotFoundError(path)

    def rename(self, old, new):
        self.renamed = (old, new)

    def mkdir(self, path):
        self.mkdir_path = path

    def putfo(self, file_obj, target_path):
        self.uploaded.append((file_obj.read(), target_path))

    def close(self):
        pass


class FakeSshClient:
    def __init__(self, sftp=None):
        self.sftp = sftp or FakeSftp()
        self.commands = []

    def open_sftp(self):
        return self.sftp

    def exec_command(self, command):
        self.commands.append(command)

        class Channel:
            def recv_exit_status(self):
                return 0

        class Stream:
            channel = Channel()

            def read(self):
                return b""

        return None, Stream(), Stream()

    def close(self):
        pass


@pytest.fixture()
def logged_user(login_user):
    return login_user("route_user", "user")


def test_editor_load_rejects_absolute_path_before_ssh(client, logged_user, monkeypatch):
    import services.ssh_manager as ssh_manager

    monkeypatch.setattr(ssh_manager, "get_ssh_client", lambda username: (_ for _ in ()).throw(AssertionError("SSH should not be opened")))

    response = client.post(f"/user/{logged_user}/editor/load", json={"path": ".", "filename": "/etc/passwd"})

    assert response.status_code == 400
    assert response.json["success"] is False


def test_editor_save_rejects_traversal_before_ssh(client, logged_user, monkeypatch):
    import services.ssh_manager as ssh_manager

    monkeypatch.setattr(ssh_manager, "get_ssh_client", lambda username: (_ for _ in ()).throw(AssertionError("SSH should not be opened")))

    response = client.post(f"/user/{logged_user}/editor/save", json={"path": "..", "filename": "main.ino", "content": "x"})

    assert response.status_code == 400
    assert response.json["success"] is False


def test_editor_save_rejects_protected_file(client, logged_user):
    response = client.post(f"/user/{logged_user}/editor/save", json={"path": ".", "filename": "WELCOME.txt", "content": "x"})

    assert response.status_code == 403
    assert response.json["success"] is False


def test_editor_load_success_uses_workspace_service(client, logged_user, monkeypatch):
    import services.ssh_manager as ssh_manager

    fake_client = FakeSshClient()
    monkeypatch.setattr(ssh_manager, "get_ssh_client", lambda username: fake_client)

    response = client.post(f"/user/{logged_user}/editor/load", json={"path": ".", "filename": "main.ino"})

    assert response.status_code == 200
    assert response.json == {"success": True, "content": "hello"}
    assert fake_client.sftp.opened[0][0] == "/home/route_user/main.ino"


def test_rename_rejects_unsafe_new_name_before_ssh(client, logged_user, monkeypatch):
    import routes.user as user_routes

    monkeypatch.setattr(user_routes, "get_ssh_client", lambda username: (_ for _ in ()).throw(AssertionError("SSH should not be opened")))

    response = client.post(f"/user/{logged_user}/rename-item", json={"old_path": "main.ino", "new_name": "../hack.ino"})

    assert response.status_code == 400


def test_rename_success_stays_inside_home(client, logged_user, monkeypatch):
    import routes.user as user_routes

    fake_client = FakeSshClient()
    monkeypatch.setattr(user_routes, "get_ssh_client", lambda username: fake_client)
    monkeypatch.setattr(user_routes, "log_action", lambda *args, **kwargs: None)

    response = client.post(f"/user/{logged_user}/rename-item", json={"old_path": "main.ino", "new_name": "renamed.ino"})

    assert response.status_code == 200
    assert fake_client.sftp.renamed == ("/home/route_user/main.ino", "/home/route_user/renamed.ino")


def test_delete_rejects_home_and_traversal(client, logged_user):
    response = client.post(f"/user/{logged_user}/delete-item", json={"path": "."})
    assert response.status_code == 403

    response = client.post(f"/user/{logged_user}/delete-item", json={"path": "../../etc/passwd"})
    assert response.status_code == 400


def test_upload_skips_unsafe_filename_and_uploads_safe_file(client, logged_user, monkeypatch):
    import routes.user as user_routes

    fake_sftp = FakeSftp()
    fake_client = FakeSshClient(fake_sftp)
    monkeypatch.setattr(user_routes, "get_ssh_client", lambda username: fake_client)
    monkeypatch.setattr(user_routes, "log_action", lambda *args, **kwargs: None)

    data = {"path": ".", "files": [(BytesIO(b"abc"), "main.ino"), (BytesIO(b"bad"), "../bad.ino")]}
    response = client.post(f"/user/{logged_user}/upload-files", data=data, content_type="multipart/form-data")

    assert response.status_code == 200
    assert fake_sftp.uploaded == [(b"abc", "/home/route_user/main.ino"), (b"bad", "/home/route_user/bad.ino")]
