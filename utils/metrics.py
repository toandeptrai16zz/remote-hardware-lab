from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Gauge, Histogram
import glob
import os

# Initialize metrics
metrics = None
DEFAULT_USB_PORTS = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2']
_known_usb_ports = set(DEFAULT_USB_PORTS)
_usb_ports_in_use = set()

# Custom Gauges
ACTIVE_CONTAINERS = Gauge('active_containers_total', 'Số lượng container đang chạy')
FLASH_QUEUE_DEPTH = Gauge('flash_queue_depth', 'Số lượng task đang chờ nạp code', ['port'])
USB_DEVICE_STATUS = Gauge('usb_device_status', 'Trạng thái thiết bị USB (0=offline, 1=available, 2=in_use)', ['port'])

def _scan_usb_ports():
    return set(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'))

def update_usb_device_metrics(active_ports=None):
    """Reflect real USB plug/unplug state while preserving ports in active upload."""
    if active_ports is None:
        active_ports = _scan_usb_ports()
    else:
        active_ports = set(active_ports)

    _known_usb_ports.update(active_ports)
    for port in list(_usb_ports_in_use):
        if not os.path.exists(port):
            _usb_ports_in_use.discard(port)

    for port in sorted(_known_usb_ports):
        if port in _usb_ports_in_use:
            USB_DEVICE_STATUS.labels(port=port).set(2)
        elif port in active_ports:
            USB_DEVICE_STATUS.labels(port=port).set(1)
        else:
            USB_DEVICE_STATUS.labels(port=port).set(0)

def mark_usb_in_use(port):
    _known_usb_ports.add(port)
    _usb_ports_in_use.add(port)
    USB_DEVICE_STATUS.labels(port=port).set(2)

def mark_usb_available(port):
    _known_usb_ports.add(port)
    _usb_ports_in_use.discard(port)
    USB_DEVICE_STATUS.labels(port=port).set(1 if os.path.exists(port) else 0)

def mark_usb_detected(port):
    _known_usb_ports.add(port)
    if port not in _usb_ports_in_use:
        USB_DEVICE_STATUS.labels(port=port).set(1 if os.path.exists(port) else 0)

def update_real_containers():
    # by Chương: Chạy ngầm để đếm chính xác số lượng sinh viên đang online
    import subprocess, time
    while True:
        try:
            cmd = ["docker", "ps", "--format", "{{.Names}}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                count = sum(1 for line in result.stdout.splitlines() if line.endswith("-dev"))
                ACTIVE_CONTAINERS.set(count)
        except Exception:
            pass
        update_usb_device_metrics()
        time.sleep(10)

def init_metrics(app):
    global metrics
    metrics = PrometheusMetrics(app)
    # Static info
    metrics.info('app_info', 'Hệ thống IoT Lab Monitoring', version='1.0.0')
    
    # Initialize gauges for default ports to avoid "No Data" in Grafana.
    # Default to Offline; admin scan or serial/upload flows will promote real ports.
    # by Chương
    for port in DEFAULT_USB_PORTS:
        FLASH_QUEUE_DEPTH.labels(port=port).set(0)
        USB_DEVICE_STATUS.labels(port=port).set(0)
    update_usb_device_metrics()
        
    import threading
    t = threading.Thread(target=update_real_containers, daemon=True)
    t.start()
    
    return metrics
