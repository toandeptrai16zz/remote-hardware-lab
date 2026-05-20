import time

from services.security import (
    generate_captcha,
    generate_csrf_token,
    validate_captcha,
    validate_csrf_token,
    validate_password_strength,
)


def test_password_strength_rules():
    assert validate_password_strength("weak")[0] is False
    assert validate_password_strength("lowercase1")[0] is False
    assert validate_password_strength("NoNumberPassword")[0] is False
    assert validate_password_strength("StrongPass1")[0] is True


def test_captcha_validation():
    captcha, token = generate_captcha()
    assert validate_captcha(captcha, token) is True
    assert validate_captcha("wrong", token) is False
    assert validate_captcha(captcha, "not-base64") is False


def test_csrf_token_lifecycle(app, monkeypatch):
    with app.test_request_context("/", environ_base={"REMOTE_ADDR": "127.0.0.1"}):
        token = generate_csrf_token()
        assert validate_csrf_token(token) is True

        monkeypatch.setattr(time, "time", lambda: 10**12)
        assert validate_csrf_token(token) is False
