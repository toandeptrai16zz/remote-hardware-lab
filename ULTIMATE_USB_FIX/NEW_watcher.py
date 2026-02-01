#!/usr/bin/python3
import time, logging, pyudev, requests, sys
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s', handlers=[logging.StreamHandler(sys.stdout)])
logger = logging.getLogger("USB")

def watch():
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='tty')
    
    # URL API rescan
    url = "http://127.0.0.1:5000/api/hardware/rescan"
    headers = {"X-Internal-Secret": "yiehfoie9f5feifh", "Content-Type": "application/json"}
    
    logger.info("🚀 Watcher Started (Root)")
    
    # Gửi tín hiệu quét lần đầu
    try: requests.post(url, json={"trigger": "startup"}, headers=headers, timeout=2)
    except: pass

    for device in iter(monitor.poll, None):
        if device.action in ['add', 'remove'] and ('USB' in device.device_node or 'ACM' in device.device_node):
            time.sleep(0.5)
            logger.info(f"Event: {device.action} - {device.device_node}")
            try:
                requests.post(url, json={"trigger_device": device.device_node, "action": device.action}, headers=headers, timeout=5)
            except Exception as e:
                logger.error(f"API Error: {e}")

if __name__ == "__main__":
    watch()
