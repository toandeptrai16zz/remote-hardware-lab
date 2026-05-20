"""
Realtime user/admin synchronization over the default Socket.IO namespace.
"""
from flask import current_app, session
from flask_socketio import join_room


USER_ROOM_PREFIX = "user:"
ROLE_ROOM_PREFIX = "role:"


def user_room(username):
    return f"{USER_ROOM_PREFIX}{username}"


def role_room(role):
    return f"{ROLE_ROOM_PREFIX}{role}"


def register_realtime_handlers(socketio):
    """Join authenticated sockets to stable rooms for targeted updates."""

    @socketio.on("connect", namespace="/")
    def handle_realtime_connect():
        username = session.get("username")
        if not username:
            return False

        join_room(user_room(username))

        role = session.get("role")
        if role:
            join_room(role_room(role))

        current_app.logger.debug("Realtime socket connected for user=%s role=%s", username, role)


def _get_socketio():
    try:
        return current_app.extensions.get("socketio")
    except RuntimeError:
        return None


def _emit(event, payload, room):
    socketio = _get_socketio()
    if not socketio:
        return False

    try:
        socketio.emit(event, payload or {}, namespace="/", room=room)
        return True
    except Exception as exc:
        current_app.logger.warning("Realtime emit failed: event=%s room=%s error=%s", event, room, exc)
        return False


def emit_user_event(username, event, payload=None):
    if not username:
        return False
    return _emit(event, payload, user_room(username))


def emit_users_event(usernames, event, payload=None):
    sent = 0
    for username in dict.fromkeys(usernames or []):
        if emit_user_event(username, event, payload):
            sent += 1
    return sent


def emit_role_event(role, event, payload=None):
    if not role:
        return False
    return _emit(event, payload, role_room(role))
