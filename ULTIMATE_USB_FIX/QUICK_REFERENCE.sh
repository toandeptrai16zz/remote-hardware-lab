#!/bin/bash
# =============================================================================
# ULTIMATE USB FIX - QUICK REFERENCE CARD
# Copy file này để luôn có commands ở tầm tay
# =============================================================================

cat << 'EOF'
╔═══════════════════════════════════════════════════════════════════════════╗
║                   ULTIMATE USB FIX - QUICK REFERENCE                      ║
╚═══════════════════════════════════════════════════════════════════════════╝

📦 INSTALLATION
───────────────────────────────────────────────────────────────────────────
cd /home/toan/flask-kerberos-demo/ULTIMATE_USB_FIX
sudo ./install.sh

🔍 SERVICE MANAGEMENT
───────────────────────────────────────────────────────────────────────────
# Check status
sudo systemctl status ultimate-usb-watcher

# Start/Stop/Restart
sudo systemctl start ultimate-usb-watcher
sudo systemctl stop ultimate-usb-watcher
sudo systemctl restart ultimate-usb-watcher

# Enable/Disable auto-start
sudo systemctl enable ultimate-usb-watcher
sudo systemctl disable ultimate-usb-watcher

# View logs (real-time)
sudo journalctl -u ultimate-usb-watcher -f

# View last N lines
sudo journalctl -u ultimate-usb-watcher -n 50

# View logs since time
sudo journalctl -u ultimate-usb-watcher --since "10 minutes ago"
sudo journalctl -u ultimate-usb-watcher --since today
sudo journalctl -u ultimate-usb-watcher --since "2026-01-31 13:00:00"

🧪 TESTING
───────────────────────────────────────────────────────────────────────────
# Test trigger manually
sudo touch /tmp/usb_event_trigger

# Check trigger file
ls -la /tmp/usb_event_trigger

# Manual API call
curl -X POST http://localhost:5000/api/hardware/rescan

# Check hardware status
curl http://localhost:5000/api/hardware/status | jq

🐳 DOCKER CONTAINERS
───────────────────────────────────────────────────────────────────────────
# List all dev containers
docker ps --filter "name=-dev"

# Check device in container
docker exec USERNAME-dev ls -la /dev/ttyUSB* /dev/ttyACM*

# Check user groups in container
docker exec USERNAME-dev groups USERNAME

# Manual restart container
docker restart USERNAME-dev

# Manual permission fix
docker exec --user root USERNAME-dev chmod 666 /dev/ttyUSB*
docker exec --user root USERNAME-dev usermod -aG dialout USERNAME

💾 USB DEVICES
───────────────────────────────────────────────────────────────────────────
# List USB devices on host
ls -la /dev/ttyUSB* /dev/ttyACM*

# Monitor USB events
udevadm monitor --udev --subsystem-match=tty

# Check device info
udevadm info -a -n /dev/ttyUSB0

# Trigger udev rules manually
sudo udevadm trigger --subsystem-match=tty

📊 DEBUGGING
───────────────────────────────────────────────────────────────────────────
# Full diagnostic
echo "=== SERVICE STATUS ==="
sudo systemctl status ultimate-usb-watcher --no-pager

echo ""
echo "=== RECENT LOGS ==="
sudo journalctl -u ultimate-usb-watcher -n 20 --no-pager

echo ""
echo "=== USB DEVICES ==="
ls -la /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo "No devices found"

echo ""
echo "=== RUNNING CONTAINERS ==="
docker ps --filter "name=-dev" --format "table {{.Names}}\t{{.Status}}"

echo ""
echo "=== FLASK APP ==="
curl -s http://localhost:5000/api/hardware/status | jq -r '.success // "Flask not running"'

🔧 TROUBLESHOOTING
───────────────────────────────────────────────────────────────────────────
# If service won't start
sudo journalctl -u ultimate-usb-watcher -n 50
pip3 install requests --break-system-packages
sudo systemctl restart ultimate-usb-watcher

# If trigger file stuck
sudo rm -f /tmp/usb_event_trigger
sudo systemctl restart ultimate-usb-watcher

# If container not seeing devices
docker restart USERNAME-dev
curl -X POST http://localhost:5000/api/hardware/rescan

# If Flask app not running
cd /home/toan/flask-kerberos-demo
python3 app.py &

# If permissions wrong
docker exec --user root USERNAME-dev chmod 666 /dev/ttyUSB*

# Clean everything and restart
sudo systemctl stop ultimate-usb-watcher
sudo rm -f /tmp/usb_event_trigger /tmp/.usb_trigger_archive_*
docker restart $(docker ps --filter "name=-dev" -q)
sudo systemctl start ultimate-usb-watcher

📂 FILE LOCATIONS
───────────────────────────────────────────────────────────────────────────
Service file:  /etc/systemd/system/ultimate-usb-watcher.service
Watcher:       /home/toan/flask-kerberos-demo/scripts/watcher_v2.py
USB Sync:      /home/toan/flask-kerberos-demo/services/docker_usb_sync.py
Routes:        /home/toan/flask-kerberos-demo/routes/hardware.py
Trigger file:  /tmp/usb_event_trigger
Archives:      /tmp/.usb_trigger_archive_*
Backups:       /home/toan/flask-kerberos-demo/backups/

📞 QUICK FIXES FOR COMMON ERRORS
───────────────────────────────────────────────────────────────────────────
ERROR: "Permission denied: '/tmp/usb_event_trigger'"
FIX:   Ultimate watcher handles this automatically (4 fallback methods)
       Service should keep running. Check logs to verify.

ERROR: "Connection refused" when calling API
FIX:   Start Flask app: python3 /home/toan/flask-kerberos-demo/app.py

ERROR: Container not seeing /dev/ttyUSB0
FIX:   docker restart USERNAME-dev
       curl -X POST http://localhost:5000/api/hardware/rescan

ERROR: "No module named 'requests'"
FIX:   pip3 install requests --break-system-packages
       sudo systemctl restart ultimate-usb-watcher

ERROR: Multiple API calls for one device
FIX:   Debouncing is enabled (2s). If still happens, increase:
       Edit watcher_v2.py: debounce_seconds=5

🎯 WORKFLOW VERIFICATION
───────────────────────────────────────────────────────────────────────────
1. Check service:    sudo systemctl status ultimate-usb-watcher
   → Should be: active (running)

2. Plug ESP32:       [physically insert device]

3. Check watcher:    sudo journalctl -u ultimate-usb-watcher -f
   → Should see: 🔔 USB Event Detected!
   → Should see: ✅ API Success

4. Check Flask:      tail -f ~/flask-kerberos-demo/logs/app.log
   → Should see: PART 1: Scanning and updating database
   → Should see: PART 2: Syncing Docker containers

5. Check container:  docker exec USERNAME-dev ls /dev/ttyUSB0
   → Should see: /dev/ttyUSB0

6. Check IDE:        Login to workspace → Tools → Port
   → Should see: /dev/ttyUSB0 (ESP32 Dev Module)

7. Upload code:      Select port → Upload sketch
   → Should work! ✅

╔═══════════════════════════════════════════════════════════════════════════╗
║  💡 TIP: Save this file as ~/usb-fix-ref.sh and run: bash ~/usb-fix-ref.sh
║      to always have these commands available!                            ║
╚═══════════════════════════════════════════════════════════════════════════╝
EOF
