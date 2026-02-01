#!/bin/bash
# Fix USB Trigger File Permission Issues
# Run this script once to fix permission problems

TRIGGER_FILE="/tmp/usb_event_trigger"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 Fixing USB Watcher Permission Issues..."
echo ""

# 1. Create trigger file if it doesn't exist
if [ ! -f "$TRIGGER_FILE" ]; then
    echo "📝 Creating trigger file: $TRIGGER_FILE"
    sudo touch "$TRIGGER_FILE"
fi

# 2. Set proper permissions (world-writable)
echo "🔓 Setting permissions: 666 (rw-rw-rw-)"
sudo chmod 666 "$TRIGGER_FILE"

# 3. Change ownership to current user
echo "👤 Changing owner to: $USER"
sudo chown "$USER:$USER" "$TRIGGER_FILE"

# 4. Verify permissions
echo ""
echo "✅ Current permissions:"
ls -la "$TRIGGER_FILE"

echo ""
echo "🎉 Permission fix complete!"
echo ""
echo "💡 Tips:"
echo "   - If still having issues, run: sudo chmod 777 $TRIGGER_FILE"
echo "   - Or create a systemd service for the watcher"
echo "   - Check logs in: logs/app.log"
