from types import SimpleNamespace
import json

import services.docker_manager as docker_manager


def test_start_container_gc_disabled(monkeypatch):
    monkeypatch.setenv("ENABLE_CONTAINER_GC", "0")
    docker_manager._gc_thread = None

    assert docker_manager.start_container_gc() is None
    assert docker_manager._gc_thread is None


def test_docker_status_returns_empty_on_missing_container(monkeypatch):
    completed = SimpleNamespace(returncode=1, stdout="")

    monkeypatch.setattr(docker_manager.subprocess, "run", lambda *args, **kwargs: completed)

    assert docker_manager.docker_status("missing-dev") == ""


def test_get_container_devices_reads_docker_inspect(monkeypatch):
    inspect_payload = [
        {
            "HostConfig": {
                "Devices": [
                    {"PathOnHost": "/dev/ttyUSB0"},
                    {"PathOnHost": "/dev/ttyUSB1"},
                ]
            }
        }
    ]
    completed = SimpleNamespace(returncode=0, stdout=json.dumps(inspect_payload))

    monkeypatch.setattr(docker_manager.subprocess, "run", lambda *args, **kwargs: completed)

    assert docker_manager.get_container_devices("student-dev") == {"/dev/ttyUSB0", "/dev/ttyUSB1"}


def test_get_container_devices_handles_bad_json(monkeypatch):
    completed = SimpleNamespace(returncode=0, stdout="not-json")

    monkeypatch.setattr(docker_manager.subprocess, "run", lambda *args, **kwargs: completed)

    assert docker_manager.get_container_devices("student-dev") == set()


class FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return {"ssh_port": None}

    def close(self):
        pass


class FakeDb:
    def __init__(self):
        self.commits = 0

    def cursor(self, dictionary=False):
        return FakeCursor()

    def commit(self):
        self.commits += 1

    def close(self):
        pass


class FakePortCursor:
    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchall(self):
        return [("/dev/ttyUSB0",), ("/dev/ttyUSB1",)]

    def close(self):
        pass


class FakePortDb:
    def cursor(self, dictionary=False):
        return FakePortCursor()

    def close(self):
        pass


def test_get_assigned_ports_returns_db_ports(monkeypatch):
    monkeypatch.setattr(docker_manager, "get_db_connection", lambda: FakePortDb())

    assert docker_manager.get_assigned_ports("student") == ["/dev/ttyUSB0", "/dev/ttyUSB1"]


def test_get_assigned_ports_handles_missing_db(monkeypatch):
    monkeypatch.setattr(docker_manager, "get_db_connection", lambda: None)

    assert docker_manager.get_assigned_ports("student") == []


def test_ensure_user_container_builds_docker_command_without_real_docker(monkeypatch, tmp_path):
    commands = []
    fake_device = tmp_path / "ttyUSB0"
    fake_device.touch()

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(docker_manager, "USER_DATA_DIR", str(tmp_path / "users"))
    monkeypatch.setattr(docker_manager, "ESP32_CORE_DIR", str(tmp_path / "esp32_core"))
    monkeypatch.setattr(docker_manager, "get_assigned_ports", lambda username: [str(fake_device)])
    monkeypatch.setattr(docker_manager, "docker_status", lambda cname: "")
    monkeypatch.setattr(docker_manager, "find_free_port", lambda: 2255)
    monkeypatch.setattr(docker_manager, "get_db_connection", lambda: FakeDb())
    monkeypatch.setattr(docker_manager.subprocess, "run", fake_run)
    monkeypatch.setattr(docker_manager.time, "sleep", lambda seconds: None)

    ssh_port = docker_manager.ensure_user_container("Student One")

    assert ssh_port == 2255
    docker_run = commands[-1]
    assert docker_run[:3] == ["docker", "run", "-d"]
    assert "--name" in docker_run
    assert "Student_One-dev" in docker_run
    assert "--device" in docker_run
    assert f"{fake_device}:{fake_device}" in docker_run


def test_running_user_helpers_and_permission_setup(monkeypatch):
    commands = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        if cmd[:2] == ["docker", "ps"]:
            return SimpleNamespace(returncode=0, stdout="alice-dev\nbob-dev\n")
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(docker_manager.subprocess, "run", fake_run)

    docker_manager.setup_container_permissions("alice-dev", "alice")
    assert docker_manager.get_all_running_users() == ["alice", "bob"]
    assert commands[0][:3] == ["docker", "exec", "alice-dev"]


def test_ensure_user_container_and_setup_delegates(monkeypatch):
    monkeypatch.setattr(docker_manager, "ensure_user_container", lambda username: 2201)

    assert docker_manager.ensure_user_container_and_setup("student") == 2201
