class MetricCounterStub:
    def __init__(self):
        self.value = 0

    def inc(self):
        self.value += 1

    def dec(self):
        self.value -= 1


def test_flash_benchmark_route_uses_smart_routing_and_releases(client, monkeypatch):
    import routes.flash as flash_routes

    reserved = []
    released = []
    in_use = []
    metric = MetricCounterStub()

    def fake_get_user_assigned_device(username, reserve=False):
        reserved.append((username, reserve))
        return {"port": "/dev/ttyUSB0", "type": "ESP32", "fqbn": "esp32:esp32:esp32"}

    monkeypatch.setattr(flash_routes, "get_user_assigned_device", fake_get_user_assigned_device)
    monkeypatch.setattr(flash_routes, "release_reserved_device", lambda port: released.append(port))
    monkeypatch.setattr(flash_routes, "mark_usb_in_use", lambda port: in_use.append(port))
    monkeypatch.setattr(flash_routes, "ACTIVE_CONTAINERS", metric)
    monkeypatch.setattr(flash_routes.random, "uniform", lambda start, end: 4.0)
    monkeypatch.setattr(flash_routes.time, "sleep", lambda delay: None)

    with client.session_transaction() as sess:
        sess["username"] = "student1"

    response = client.post("/api/flash", json={"board_type": "ESP32"})

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "port": "/dev/ttyUSB0",
        "delay": 4.0,
        "board_type": "ESP32",
    }
    assert reserved == [("student1", True)]
    assert in_use == ["/dev/ttyUSB0"]
    assert released == ["/dev/ttyUSB0"]
    assert metric.value == 0


def test_flash_benchmark_route_returns_503_when_no_port(client, monkeypatch):
    import routes.flash as flash_routes

    monkeypatch.setattr(flash_routes, "get_user_assigned_device", lambda username, reserve=False: None)

    response = client.post("/api/flash", json={"board_type": "ESP32"})

    assert response.status_code == 503
    assert response.get_json() == {
        "success": False,
        "error": "No available hardware ports",
    }
