import os
import urllib.request

import pytest

os.environ.setdefault("TESTING", "1")
os.environ.setdefault("ENABLE_CONTAINER_GC", "0")
os.environ.setdefault("AI_GRADER_RECORD_DATASET", "0")
os.environ.setdefault("FLASK_SECRET_KEY", "test-secret")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("ANTHROPIC_API_KEY", "")
os.environ.setdefault("GROQ_API_KEY", "")


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    def blocked_urlopen(*args, **kwargs):
        raise AssertionError("External network calls are disabled in tests")

    monkeypatch.setattr(urllib.request, "urlopen", blocked_urlopen)

    try:
        import requests
    except ImportError:
        return

    def blocked_request(*args, **kwargs):
        raise AssertionError("External HTTP calls are disabled in tests")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked_request)

    try:
        import httpx
    except ImportError:
        return

    monkeypatch.setattr(httpx.Client, "request", blocked_request)
    monkeypatch.setattr(httpx.AsyncClient, "request", blocked_request)


@pytest.fixture()
def app():
    from app import app as flask_app

    flask_app.config.update(TESTING=True, SECRET_KEY="test-secret")
    return flask_app


@pytest.fixture()
def client(app):
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture()
def login_user(client):
    def _login(username="test_user", role="user"):
        with client.session_transaction() as sess:
            sess["username"] = username
            sess["role"] = role
        return username

    return _login
