import json

import services.logger as logger_service


class FakeCursor:
    def __init__(self):
        self.executed = None

    def execute(self, query, params=None):
        self.executed = (query, params)

    def close(self):
        pass


class FakeDb:
    def __init__(self):
        self.cursor_obj = FakeCursor()
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_log_action_without_request_context(monkeypatch):
    fake_db = FakeDb()
    monkeypatch.setattr(logger_service, "get_db_connection", lambda: fake_db)

    logger_service.log_action("student", "Did thing", success=False, details={"x": 1})

    _query, params = fake_db.cursor_obj.executed
    assert params[0] == "student"
    assert params[1] == "Did thing"
    assert params[2] == "System/Background"
    assert params[4] is False
    assert json.loads(params[5]) == {"x": 1}
    assert fake_db.committed is True
    assert fake_db.closed is True


def test_log_action_with_request_context(app, monkeypatch):
    fake_db = FakeDb()
    monkeypatch.setattr(logger_service, "get_db_connection", lambda: fake_db)

    with app.test_request_context("/", environ_base={"REMOTE_ADDR": "10.0.0.1", "HTTP_USER_AGENT": "pytest"}):
        logger_service.log_action("student", "Request action")

    _query, params = fake_db.cursor_obj.executed
    assert params[2] == "10.0.0.1"
    assert params[3] in {"pytest", "Unknown"}


def test_log_action_no_db_is_noop(monkeypatch):
    monkeypatch.setattr(logger_service, "get_db_connection", lambda: None)

    logger_service.log_action("student", "No DB")
