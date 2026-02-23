#!/bin/bash

# Auto-fix script for USB detection issue
# Run with: sudo bash fix_usb_detection.sh

echo "========================================="
echo "USB DETECTION AUTO-FIX SCRIPT"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}[ERROR] Please run as root: sudo bash $0${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/5] Stopping USB watcher service...${NC}"
systemctl stop usb-watcher 2>/dev/null || true
sleep 2

echo -e "${YELLOW}[2/5] Fixing watcher service permissions...${NC}"

# Check if service file exists
if [ ! -f /etc/systemd/system/usb-watcher.service ]; then
    echo -e "${RED}Service file not found. Creating new one...${NC}"
    
    cat > /etc/systemd/system/usb-watcher.service << 'EOF'
[Unit]
Description=USB Device Event Watcher
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/toan/flask-kerberos-demo/scripts
ExecStart=/usr/bin/python3 /home/toan/flask-kerberos-demo/scripts/watcher.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    echo -e "${GREEN}✓ Created new service file${NC}"
else
    # Backup existing service file
    cp /etc/systemd/system/usb-watcher.service /etc/systemd/system/usb-watcher.service.backup
    
    # Update User to root
    sed -i 's/^User=.*/User=root/' /etc/systemd/system/usb-watcher.service
    
    # Add StandardOutput and StandardError if not present
    if ! grep -q "StandardOutput" /etc/systemd/system/usb-watcher.service; then
        sed -i '/\[Service\]/a StandardOutput=journal\nStandardError=journal' /etc/systemd/system/usb-watcher.service
    fi
    
    echo -e "${GREEN}✓ Updated service file (backup saved)${NC}"
fi

echo -e "${YELLOW}[3/5] Fixing trigger file permissions...${NC}"

# Remove old trigger file
rm -f /tmp/usb_event_trigger

# Set proper permissions on /tmp
chmod 1777 /tmp

echo -e "${GREEN}✓ Fixed trigger file permissions${NC}"

echo -e "${YELLOW}[4/5] Reloading systemd and restarting service...${NC}"

systemctl daemon-reload
systemctl enable usb-watcher
systemctl restart usb-watcher

sleep 3

# Check service status
if systemctl is-active --quiet usb-watcher; then
    echo -e "${GREEN}✓ USB Watcher service is running${NC}"
else
    echo -e "${RED}✗ Failed to start USB Watcher service${NC}"
    echo "Check logs with: sudo journalctl -u usb-watcher -n 50"
    exit 1
fi

echo -e "${YELLOW}[5/5] Testing USB detection...${NC}"

# Test by creating trigger file
echo -e "Creating test trigger file..."
touch /tmp/usb_event_trigger

sleep 2

# Check if trigger file was removed (meaning watcher is working)
if [ ! -f /tmp/usb_event_trigger ]; then
    echo -e "${GREEN}✓ USB Watcher is working correctly!${NC}"
else
    echo -e "${RED}✗ USB Watcher did not remove trigger file${NC}"
    echo "Check logs with: sudo journalctl -u usb-watcher -n 50"
fi

echo ""
echo "========================================="
echo -e "${GREEN}FIX COMPLETED!${NC}"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Plug in your ESP32 device"
echo "2. Wait 2-3 seconds"
echo "3. Check logs: sudo journalctl -u usb-watcher -f"
echo "4. Verify in web interface: User > Scan Serial Ports"
echo ""
echo "If still not working:"
echo "- Check container: docker exec USERNAME-dev ls /dev/ttyUSB*"
echo "- Manual restart: docker restart USERNAME-dev"
echo "- View watcher logs: sudo journalctl -u usb-watcher -n 100"
echo ""
