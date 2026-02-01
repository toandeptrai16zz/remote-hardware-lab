#!/bin/bash
# Install USB Watcher as systemd service
# This makes the watcher run automatically on system boot

SERVICE_NAME="usb-watcher"
SERVICE_FILE="usb-watcher.service"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"

echo "🔧 Installing USB Watcher Service..."
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ This script must be run as root"
    echo "   Please run: sudo $0"
    exit 1
fi

# 1. Copy service file
echo "📋 Copying service file to $SYSTEMD_DIR..."
cp "$SCRIPT_DIR/$SERVICE_FILE" "$SYSTEMD_DIR/"

# 2. Reload systemd
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# 3. Enable service (start on boot)
echo "✅ Enabling service to start on boot..."
systemctl enable "$SERVICE_NAME"

# 4. Start service now
echo "▶️  Starting service..."
systemctl start "$SERVICE_NAME"

# 5. Check status
echo ""
echo "📊 Service Status:"
systemctl status "$SERVICE_NAME" --no-pager

echo ""
echo "🎉 Installation complete!"
echo ""
echo "📝 Useful commands:"
echo "   Check status:  systemctl status $SERVICE_NAME"
echo "   View logs:     journalctl -u $SERVICE_NAME -f"
echo "   Stop service:  sudo systemctl stop $SERVICE_NAME"
echo "   Start service: sudo systemctl start $SERVICE_NAME"
echo "   Disable:       sudo systemctl disable $SERVICE_NAME"
