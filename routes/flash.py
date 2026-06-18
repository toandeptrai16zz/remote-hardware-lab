"""
Benchmark flash API routes.
"""
import random
import time

from flask import Blueprint, jsonify, request, session

from services.arduino import get_user_assigned_device, release_reserved_device
from utils.metrics import ACTIVE_CONTAINERS, mark_usb_in_use

flash_bp = Blueprint("flash", __name__)


@flash_bp.route("/api/flash", methods=["POST"])
def flash_test_real_api():
    """
    [NCKH] API Flash đồng bộ dành riêng cho kiểm thử tải 300 SV - by Chương.
    Tích hợp Smart Routing thật sự từ services/arduino.
    """
    data = request.get_json(silent=True) or {}
    board_type = data.get("board_type", "ESP32")
    username = session.get("username", "ha quang chuong")

    assigned = get_user_assigned_device(username, reserve=True)
    if not assigned:
        return jsonify(success=False, error="No available hardware ports"), 503

    port = assigned["port"]

    try:
        ACTIVE_CONTAINERS.inc()
        mark_usb_in_use(port)

        delay = random.uniform(3.8, 4.3)
        time.sleep(delay)

        return jsonify(
            success=True,
            port=port,
            delay=delay,
            board_type=board_type,
        )
    finally:
        release_reserved_device(port)
        ACTIVE_CONTAINERS.dec()
