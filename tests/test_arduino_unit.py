from types import SimpleNamespace
import random
import json

from services import arduino


def test_analyze_compile_errors_extracts_errors_and_warnings():
    output = "\n".join(
        [
            "/tmp/main.ino:10:5: error: expected ';' before '}' token",
            "/tmp/main.ino:12:3: warning: unused variable 'x'",
        ]
    )

    result = arduino.analyze_compile_errors(output)

    assert result["error_count"] == 1
    assert result["warning_count"] == 1
    assert result["errors"][0]["file"] == "main.ino"
    assert result["errors"][0]["line"] == 10


def test_detect_board_from_sketch_defaults_to_esp32_when_keywords_found(monkeypatch):
    completed = SimpleNamespace(returncode=0, stdout="#include <WiFi.h>\nvoid setup(){ xTaskCreate(NULL, \"t\", 1, NULL, 1, NULL); }")

    monkeypatch.setattr(arduino.subprocess, "run", lambda *args, **kwargs: completed)

    assert arduino.detect_board_from_sketch("student", "main.ino") == "esp32:esp32:esp32"


def test_detect_board_from_sketch_defaults_to_uno_without_keywords(monkeypatch):
    completed = SimpleNamespace(returncode=0, stdout="void setup(){}\nvoid loop(){}")

    monkeypatch.setattr(arduino.subprocess, "run", lambda *args, **kwargs: completed)

    assert arduino.detect_board_from_sketch("student", "main.ino") == "arduino:avr:uno"


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchall(self):
        return self.rows

    def close(self):
        pass


class FakeDb:
    def __init__(self, rows):
        self.rows = rows

    def cursor(self, dictionary=False):
        return FakeCursor(self.rows)

    def close(self):
        pass


def test_get_user_assigned_device_reserves_lowest_queue(monkeypatch):
    rows = [
        {"port": "/dev/ttyUSB0", "type": "ESP32"},
        {"port": "/dev/ttyUSB1", "type": "ESP32"},
    ]

    monkeypatch.setattr(arduino, "get_db_connection", lambda: FakeDb(rows))
    monkeypatch.setattr(random, "choice", lambda candidates: candidates[0])
    arduino.queue_counts.clear()
    arduino.queue_counts["/dev/ttyUSB0"] = 2
    arduino.queue_counts["/dev/ttyUSB1"] = 0

    result = arduino.get_user_assigned_device("student", reserve=True)

    assert result["port"] == "/dev/ttyUSB1"
    assert result["fqbn"] == "esp32:esp32:esp32"
    assert arduino.queue_counts["/dev/ttyUSB1"] == 1


def test_compile_sketch_uses_docker_compile_command(monkeypatch):
    captured = {}

    def fake_run(cmd, capture_output, text, timeout):
        captured["cmd"] = cmd
        return SimpleNamespace(returncode=0, stdout="Compile ok", stderr="")

    monkeypatch.setattr(arduino, "prepare_sketch_folder", lambda cname, safe_username, sketch_filename: "/home/student/main/main.ino")
    monkeypatch.setattr(arduino.subprocess, "run", fake_run)

    result = arduino.compile_sketch("student", "arduino:avr:uno", "main.ino")

    assert result["success"] is True
    assert captured["cmd"][:3] == ["docker", "exec", "student-dev"]
    assert "arduino-cli" in captured["cmd"]


def test_get_upload_error_suggestions_and_board_mapping():
    suggestions = arduino.get_upload_error_suggestions("Permission denied\nTimed out")
    assert "Lỗi quyền truy cập cổng USB." in suggestions
    assert "Hết thời gian chờ. Kiểm tra nút BOOT." in suggestions

    assert arduino.get_boards_by_type("esp8266")[0]["fqbn"] == "esp8266:esp8266:nodemcuv2"
    assert arduino.get_boards_by_type("nano")[0]["fqbn"] == "arduino:avr:nano:cpu=atmega328old"
    assert arduino.get_boards_by_type("unknown")[0]["fqbn"] == "arduino:avr:uno"


def test_get_serial_ports_filters_by_db_assignments(monkeypatch):
    rows = [
        {"port": "/dev/ttyUSB0", "tag_name": "Board A", "type": "ESP32", "status": "available"},
        {"port": "/dev/ttyUSB1", "tag_name": "Board B", "type": "Arduino Uno", "status": "available"},
    ]
    detected = {
        "detected_ports": [
            {"port": {"address": "/dev/ttyS0"}},
            {"port": {"address": "/dev/ttyUSB0"}},
            {"port": {"address": "/dev/ttyUSB9"}},
        ]
    }

    monkeypatch.setattr(arduino, "get_db_connection", lambda: FakeDb(rows))
    monkeypatch.setattr(
        arduino.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=json.dumps(detected)),
    )

    result = arduino.get_serial_ports("student")

    assert result["success"] is True
    assert result["ports"] == [
        {
            "port": {"address": "/dev/ttyUSB0", "label": "Board A"},
            "boards": [{"name": "ESP32 Dev Module", "fqbn": "esp32:esp32:esp32"}],
        }
    ]


def test_get_serial_ports_reports_subprocess_errors(monkeypatch):
    def fail_run(*args, **kwargs):
        raise RuntimeError("docker unavailable")

    monkeypatch.setattr(arduino, "get_db_connection", lambda: None)
    monkeypatch.setattr(arduino.subprocess, "run", fail_run)

    result = arduino.get_serial_ports("student")

    assert result["success"] is False
    assert "docker unavailable" in result["error"]
