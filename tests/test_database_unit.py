from types import SimpleNamespace

import config.database as database


class FakeCursor:
    def __init__(self, admin_exists=False):
        self.admin_exists = admin_exists
        self.statements = []
        self.inserted_admin = False

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if query.strip().startswith("INSERT INTO users"):
            self.inserted_admin = True

    def fetchone(self):
        return (1,) if self.admin_exists else None

    def close(self):
        pass


class FakeDb:
    def __init__(self, cursor):
        self.cursor_obj = cursor
        self.committed = False
        self.closed = False

    def cursor(self, dictionary=False):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def test_get_db_connection_initializes_pool(monkeypatch):
    class FakePool:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def get_connection(self):
            return SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(database.pooling, "MySQLConnectionPool", FakePool)
    monkeypatch.setenv("DB_HOST", "db")
    monkeypatch.setenv("DB_USER", "user")
    monkeypatch.setenv("DB_PASSWORD", "pw")
    monkeypatch.setenv("DB_DATABASE", "lab")
    database._db_pool = None

    conn = database.get_db_connection()

    assert conn is not None
    assert database._db_pool.kwargs["host"] == "db"
    assert database._db_pool.kwargs["database"] == "lab"


def test_get_db_connection_returns_none_on_pool_error(monkeypatch):
    def raise_error(**kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(database.pooling, "MySQLConnectionPool", raise_error)
    database._db_pool = None

    assert database.get_db_connection() is None


def test_init_db_creates_schema_and_default_admin(monkeypatch):
    cursor = FakeCursor(admin_exists=False)
    fake_db = FakeDb(cursor)
    monkeypatch.setattr(database, "get_db_connection", lambda: fake_db)

    database.init_db()

    executed_sql = "\n".join(query for query, _params in cursor.statements)
    assert "CREATE TABLE IF NOT EXISTS users" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS submissions" in executed_sql
    assert cursor.inserted_admin is True
    assert fake_db.committed is True
    assert fake_db.closed is True


def test_init_db_skips_default_admin_when_present(monkeypatch):
    cursor = FakeCursor(admin_exists=True)
    fake_db = FakeDb(cursor)
    monkeypatch.setattr(database, "get_db_connection", lambda: fake_db)

    database.init_db()

    assert cursor.inserted_admin is False
    assert fake_db.committed is True
