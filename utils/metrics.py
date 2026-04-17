from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Gauge, Histogram

# Initialize metrics
metrics = None

# Custom Gauges
ACTIVE_CONTAINERS = Gauge('active_containers_total', 'Số lượng container đang chạy')
FLASH_QUEUE_DEPTH = Gauge('flash_queue_depth', 'Số lượng task đang chờ nạp code', ['port'])
USB_DEVICE_STATUS = Gauge('usb_device_status', 'Trạng thái thiết bị USB (0=offline, 1=available, 2=in_use)', ['port'])

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
        time.sleep(10)

def init_metrics(app):
    global metrics
    metrics = PrometheusMetrics(app)
    # Static info
    metrics.info('app_info', 'Hệ thống IoT Lab Monitoring', version='1.0.0')
    
    # Initialize gauges to 0 for default ports to avoid "No Data" in Grafana
    # by Chương
    for port in ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyUSB2']:
        FLASH_QUEUE_DEPTH.labels(port=port).set(0)
        USB_DEVICE_STATUS.labels(port=port).set(1) # Mặc định là Available
        
    import threading
    t = threading.Thread(target=update_real_containers, daemon=True)
    t.start()
    
    return metrics
