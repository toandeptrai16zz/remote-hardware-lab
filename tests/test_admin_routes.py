from types import SimpleNamespace


class FakeCursor:
    def __init__(self, user):
        self.user = user
        self.deleted_user_id = None

    def execute(self, query, params=None):
        if query.strip().startswith("DELETE FROM users"):
            self.deleted_user_id = params[0]

    def fetchone(self):
        return self.user

    def close(self):
        pass


class FakeDb:
    def __init__(self, user):
        self.cursor_obj = FakeCursor(user)
        self.committed = False

    def cursor(self, dictionary=False):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def close(self):
        pass


def test_admin_delete_user_deletes_only_under_user_data_dir(client, login_user, monkeypatch, tmp_path):
    import routes.admin as admin_routes

    login_user("admin", "admin")
    user_root = tmp_path / "users"
    user_dir = user_root / "student"
    user_dir.mkdir(parents=True)
    fake_db = FakeDb({"username": "student"})
    docker_commands = []

    monkeypatch.setattr(admin_routes, "USER_DATA_DIR", str(user_root))
    monkeypatch.setattr(admin_routes, "get_db_connection", lambda: fake_db)
    monkeypatch.setattr(admin_routes.subprocess, "run", lambda cmd, **kwargs: docker_commands.append(cmd) or SimpleNamespace(returncode=0))
    monkeypatch.setattr(admin_routes, "log_action", lambda *args, **kwargs: None)

    response = client.post("/admin/delete_user/1")

    assert response.status_code == 302
    assert not user_dir.exists()
    assert user_root.exists()
    assert docker_commands[0][:3] == ["docker", "rm", "-f"]
    assert fake_db.committed is True


def test_admin_delete_user_refuses_user_data_root_deletion(client, login_user, monkeypatch, tmp_path):
    import routes.admin as admin_routes

    login_user("admin", "admin")
    user_root = tmp_path / "users"
    user_root.mkdir()
    fake_db = FakeDb({"username": "student"})

    monkeypatch.setattr(admin_routes, "USER_DATA_DIR", str(user_root))
    monkeypatch.setattr(admin_routes, "make_safe_name", lambda username: "")
    monkeypatch.setattr(admin_routes, "get_db_connection", lambda: fake_db)
    monkeypatch.setattr(admin_routes.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))
    monkeypatch.setattr(admin_routes, "log_action", lambda *args, **kwargs: None)

    response = client.post("/admin/delete_user/1")

    assert response.status_code == 302
    assert user_root.exists()
    assert fake_db.committed is True
