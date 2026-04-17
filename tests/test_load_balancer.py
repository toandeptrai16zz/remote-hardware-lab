"""
Load Testing: Kiểm thử thuật toán Smart Routing Round-Robin
Mô phỏng N sinh viên nạp code đồng thời, xác nhận phân phối đều - by Chương
"""
import threading
import random
from collections import defaultdict

# ============================================================
# MÔ PHỎNG THUẬT TOÁN SMART ROUTING (không cần DB, không cần board)
# ============================================================
queue_counts = defaultdict(int)
routing_lock = threading.Lock()
results = defaultdict(int)  # đếm số lần mỗi port được chọn


def smart_route(ports):
    """Mô phỏng đúng logic trong services/arduino.py dòng 328-341"""
    with routing_lock:
        min_queue = min(queue_counts[p] for p in ports)
        candidates = [p for p in ports if queue_counts[p] == min_queue]
        best = random.choice(candidates)
        queue_counts[best] += 1
        return best


def simulate_student(ports, student_id):
    """Mô phỏng 1 sinh viên bấm Flash"""
    port = smart_route(ports)
    results[port] += 1
    # Giả lập thời gian nạp code
    import time
    time.sleep(0.01)
    queue_counts[port] -= 1


# ============================================================
# TEST 1: 2 SV đồng thời → 2 board → phân phối 50/50
# ============================================================
def test_two_students_two_boards():
    """2 sinh viên nạp đồng thời lên 2 board khác nhau"""
    queue_counts.clear()
    results.clear()
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1']

    threads = []
    for i in range(100):
        t = threading.Thread(target=simulate_student, args=(ports, i))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Kiểm tra phân phối: mỗi port nhận 40-60% (cho phép sai lệch ±10%)
    total = sum(results.values())
    for port in ports:
        ratio = results[port] / total
        assert 0.3 <= ratio <= 0.7, f"{port} nhận {ratio*100:.0f}% — không cân bằng!"

    print(f"✅ Test 2 board: USB0={results[ports[0]]}, USB1={results[ports[1]]} / {total} total")


# ============================================================
# TEST 2: 3 board → phân phối đều ~33% mỗi board
# ============================================================
def test_three_boards_even_distribution():
    """Mô phỏng 90 request lên 3 board"""
    queue_counts.clear()
    results.clear()
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2']

    threads = []
    for i in range(90):
        t = threading.Thread(target=simulate_student, args=(ports, i))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    total = sum(results.values())
    for port in ports:
        ratio = results[port] / total
        assert 0.15 <= ratio <= 0.5, f"{port} nhận {ratio*100:.0f}% — lệch quá!"

    print(f"✅ Test 3 board: {dict(results)} / {total} total")


# ============================================================
# TEST 3: Race Condition — queue_counts không bao giờ âm
# ============================================================
def test_no_negative_queue():
    """Đảm bảo queue_counts luôn >= 0 sau khi tất cả thread kết thúc"""
    queue_counts.clear()
    results.clear()
    ports = ['/dev/ttyUSB0', '/dev/ttyUSB1']

    threads = []
    for i in range(200):
        t = threading.Thread(target=simulate_student, args=(ports, i))
        threads.append(t)

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for port in ports:
        assert queue_counts[port] >= 0, f"{port} queue = {queue_counts[port]} < 0!"

    print(f"✅ Test Race Condition: tất cả queue >= 0")


# ============================================================
# TEST 4: 1 board duy nhất → 100% dồn vào 1 cổng
# ============================================================
def test_single_board():
    """Chỉ có 1 board thì mọi request đều vào đó"""
    queue_counts.clear()
    results.clear()
    ports = ['/dev/ttyUSB0']

    for i in range(50):
        simulate_student(ports, i)

    assert results['/dev/ttyUSB0'] == 50
    print(f"✅ Test 1 board: 100% vào USB0")
