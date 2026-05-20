from sockets.realtime import emit_role_event, emit_user_event, emit_users_event, role_room, user_room


class FakeSocketIO:
    def __init__(self):
        self.emitted = []

    def emit(self, event, payload, namespace=None, room=None):
        self.emitted.append(
            {
                "event": event,
                "payload": payload,
                "namespace": namespace,
                "room": room,
            }
        )


def test_realtime_helpers_emit_to_expected_rooms(app):
    fake_socketio = FakeSocketIO()
    original_socketio = app.extensions.get("socketio")
    app.extensions["socketio"] = fake_socketio

    try:
        with app.app_context():
            assert emit_user_event("alice", "mission_changed", {"action": "updated"}) is True
            assert emit_role_event("user", "device_changed", {"action": "scanned"}) is True
    finally:
        app.extensions["socketio"] = original_socketio

    assert fake_socketio.emitted == [
        {
            "event": "mission_changed",
            "payload": {"action": "updated"},
            "namespace": "/",
            "room": user_room("alice"),
        },
        {
            "event": "device_changed",
            "payload": {"action": "scanned"},
            "namespace": "/",
            "room": role_room("user"),
        },
    ]


def test_realtime_emit_users_deduplicates_usernames(app):
    fake_socketio = FakeSocketIO()
    original_socketio = app.extensions.get("socketio")
    app.extensions["socketio"] = fake_socketio

    try:
        with app.app_context():
            sent = emit_users_event(["alice", "bob", "alice"], "mission_changed", {"action": "created"})
    finally:
        app.extensions["socketio"] = original_socketio

    assert sent == 2
    assert [item["room"] for item in fake_socketio.emitted] == [user_room("alice"), user_room("bob")]


def test_realtime_socket_client_receives_targeted_user_room_event(app, client):
    from app import socketio

    with client.session_transaction() as sess:
        sess["username"] = "room_user"
        sess["role"] = "user"

    socket_client = socketio.test_client(app, flask_test_client=client, namespace="/")
    assert socket_client.is_connected("/") is True

    socketio.emit(
        "mission_changed",
        {"action": "updated", "mission_id": 1},
        namespace="/",
        room=user_room("room_user"),
    )

    received = socket_client.get_received("/")
    assert received == [
        {
            "name": "mission_changed",
            "args": [{"action": "updated", "mission_id": 1}],
            "namespace": "/",
        }
    ]
