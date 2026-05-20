def test_api_requires_login(client):
    response = client.post("/user/someone/editor/load", json={"path": ".", "filename": "main.ino"})

    assert response.status_code == 401
    assert response.json["success"] is False


def test_user_cannot_access_other_user_workspace(client, login_user):
    login_user("alice", "user")

    response = client.post("/user/bob/editor/load", json={"path": ".", "filename": "main.ino"})

    assert response.status_code == 403
    assert response.json["success"] is False


def test_admin_role_rejected_from_user_api(client, login_user):
    login_user("admin", "admin")

    response = client.post("/user/admin/editor/load", json={"path": ".", "filename": "main.ino"})

    assert response.status_code == 403
    assert response.json["success"] is False
