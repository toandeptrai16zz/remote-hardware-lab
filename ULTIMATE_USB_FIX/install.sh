#!/bin/bash
# =============================================================================
# ULTIMATE USB FIX - INSTALLATION SCRIPT
# Cài đặt triệt để tất cả components để fix USB detection
# =============================================================================

set -e  # Exit on error

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"

echo "============================================================================="
echo "🚀 ULTIMATE USB FIX - INSTALLATION"
echo "============================================================================="
echo "Script Dir: $SCRIPT_DIR"
echo "Project Dir: $PROJECT_DIR"
echo ""

# =============================================================================
# STEP 1: BACKUP OLD FILES
# =============================================================================
echo "📦 STEP 1: Backing up old files..."

backup_dir="$PROJECT_DIR/backups/usb_fix_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"

# Backup old watcher if exists
if [ -f "$PROJECT_DIR/scripts/watcher.py" ]; then
    cp "$PROJECT_DIR/scripts/watcher.py" "$backup_dir/"
    echo "  ✅ Backed up old watcher.py"
fi

# Backup old service if exists
if [ -f "/etc/systemd/system/usb-watcher.service" ]; then
    sudo cp "/etc/systemd/system/usb-watcher.service" "$backup_dir/"
    echo "  ✅ Backed up old service file"
fi

# Backup old hardware routes if exists
if [ -f "$PROJECT_DIR/routes/hardware.py" ]; then
    cp "$PROJECT_DIR/routes/hardware.py" "$backup_dir/"
    echo "  ✅ Backed up old hardware.py"
fi

echo ""

# =============================================================================
# STEP 2: STOP OLD SERVICE
# =============================================================================
echo "🛑 STEP 2: Stopping old USB watcher service..."

if systemctl is-active --quiet usb-watcher; then
    sudo systemctl stop usb-watcher
    echo "  ✅ Stopped old usb-watcher service"
else
    echo "  ℹ️  Old service not running"
fi

if systemctl is-enabled --quiet usb-watcher 2>/dev/null; then
    sudo systemctl disable usb-watcher
    echo "  ✅ Disabled old service"
fi

echo ""

# =============================================================================
# STEP 3: INSTALL NEW FILES
# =============================================================================
echo "📝 STEP 3: Installing new files..."

# Copy new watcher to scripts directory (keep old location for compatibility)
cp "$SCRIPT_DIR/NEW_watcher.py" "$PROJECT_DIR/scripts/watcher_v2.py"
chmod +x "$PROJECT_DIR/scripts/watcher_v2.py"
echo "  ✅ Installed new watcher (watcher_v2.py)"

# Also keep in ULTIMATE_USB_FIX directory
chmod +x "$SCRIPT_DIR/NEW_watcher.py"
echo "  ✅ Made NEW_watcher.py executable"

# Copy USB sync module
cp "$SCRIPT_DIR/NEW_docker_usb_sync.py" "$PROJECT_DIR/services/docker_usb_sync.py"
chmod +x "$PROJECT_DIR/services/docker_usb_sync.py"
echo "  ✅ Installed USB sync module"

# Install new hardware routes
cp "$SCRIPT_DIR/NEW_hardware_routes.py" "$PROJECT_DIR/routes/hardware.py"
echo "  ✅ Updated hardware routes"

echo ""

# =============================================================================
# STEP 4: INSTALL SYSTEMD SERVICE
# =============================================================================
echo "⚙️  STEP 4: Installing systemd service..."

sudo cp "$SCRIPT_DIR/ultimate-usb-watcher.service" "/etc/systemd/system/"
echo "  ✅ Copied service file"

sudo systemctl daemon-reload
echo "  ✅ Reloaded systemd"

sudo systemctl enable ultimate-usb-watcher.service
echo "  ✅ Enabled service"

echo ""

# =============================================================================
# STEP 5: SETUP PERMISSIONS
# =============================================================================
echo "🔐 STEP 5: Setting up permissions..."

# Ensure /tmp is writable (should be by default)
if [ ! -w "/tmp" ]; then
    sudo chmod 1777 /tmp
    echo "  ✅ Fixed /tmp permissions"
fi

# Create trigger file directory if needed
trigger_dir="/tmp"
if [ ! -d "$trigger_dir" ]; then
    sudo mkdir -p "$trigger_dir"
    sudo chmod 1777 "$trigger_dir"
fi

# Clean up any existing trigger files
if [ -f "/tmp/usb_event_trigger" ]; then
    sudo rm -f "/tmp/usb_event_trigger"
    echo "  ✅ Cleaned up old trigger file"
fi

# Clean up old archive files
sudo rm -f /tmp/.usb_trigger_archive_* 2>/dev/null || true
echo "  ✅ Cleaned up archive files"

echo ""

# =============================================================================
# STEP 6: VERIFY DEPENDENCIES
# =============================================================================
echo "📦 STEP 6: Checking Python dependencies..."

if ! python3 -c "import requests" &>/dev/null; then
    echo "  ⚠️  requests module not found, installing..."
    pip3 install requests --break-system-packages || pip3 install requests
fi
echo "  ✅ Python dependencies OK"

echo ""

# =============================================================================
# STEP 7: START NEW SERVICE
# =============================================================================
echo "🚀 STEP 7: Starting new USB watcher service..."

sudo systemctl start ultimate-usb-watcher.service
sleep 2

if systemctl is-active --quiet ultimate-usb-watcher; then
    echo "  ✅ Service started successfully"
else
    echo "  ❌ Service failed to start"
    echo "  📋 Check logs: sudo journalctl -u ultimate-usb-watcher -n 50"
    exit 1
fi

echo ""

# =============================================================================
# STEP 8: VERIFY INSTALLATION
# =============================================================================
echo "🔍 STEP 8: Verifying installation..."

echo "  Service Status:"
sudo systemctl status ultimate-usb-watcher --no-pager | head -10

echo ""
echo "  Recent Logs:"
sudo journalctl -u ultimate-usb-watcher -n 5 --no-pager

echo ""

# =============================================================================
# STEP 9: TEST TRIGGER (OPTIONAL)
# =============================================================================
echo "🧪 STEP 9: Testing trigger mechanism..."
echo "  Creating test trigger file..."

sudo touch /tmp/usb_event_trigger
sleep 3

if [ -f "/tmp/usb_event_trigger" ]; then
    echo "  ⚠️  Trigger file still exists (watcher may not be removing it)"
    echo "  Check logs: sudo journalctl -u ultimate-usb-watcher -n 20"
else
    echo "  ✅ Trigger file was processed and removed"
fi

echo ""

# =============================================================================
# FINAL SUMMARY
# =============================================================================
echo "============================================================================="
echo "✅ INSTALLATION COMPLETE!"
echo "============================================================================="
echo ""
echo "📊 Summary:"
echo "  ✓ New watcher installed: $PROJECT_DIR/scripts/watcher_v2.py"
echo "  ✓ USB sync module: $PROJECT_DIR/services/docker_usb_sync.py"
echo "  ✓ Hardware routes updated: $PROJECT_DIR/routes/hardware.py"
echo "  ✓ Systemd service: ultimate-usb-watcher.service"
echo "  ✓ Service status: RUNNING"
echo ""
echo "🔧 Useful Commands:"
echo "  • Check status:    sudo systemctl status ultimate-usb-watcher"
echo "  • View logs:       sudo journalctl -u ultimate-usb-watcher -f"
echo "  • Restart service: sudo systemctl restart ultimate-usb-watcher"
echo "  • Stop service:    sudo systemctl stop ultimate-usb-watcher"
echo ""
echo "🧪 Testing:"
echo "  1. Plug in ESP32 device"
echo "  2. Check logs: sudo journalctl -u ultimate-usb-watcher -f"
echo "  3. Verify API call: curl -X POST http://localhost:5000/api/hardware/rescan"
echo "  4. Check container: docker exec USERNAME-dev ls -la /dev/ttyUSB*"
echo ""
echo "📦 Backup location: $backup_dir"
echo "============================================================================="
