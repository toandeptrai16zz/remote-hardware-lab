"""
Enhanced Docker Manager với Container Restart khi có USB mới
"""
import os
import subprocess
import time
import logging
import glob
from utils import make_safe_name
from config import get_db_connection

logger = logging.getLogger(__name__)

def get_physical_usb_devices():
    """Scan và return danh sách thiết bị USB thực tế"""
    devices = glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*')
    return set(devices)

def container_has_device_access(container_name, device_path):
    """
    Kiểm tra xem container có thể truy cập device không
    """
    try:
        result = subprocess.run(
            ["docker", "exec", container_name, "test", "-e", device_path],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error checking device access in {container_name}: {e}")
        return False

def sync_container_devices(container_name, username):
    """
    Đồng bộ devices vào container KHÔNG cần restart
    Sử dụng docker exec để update permissions
    """
    try:
        # Get current USB devices
        usb_devices = get_physical_usb_devices()
        
        if not usb_devices:
            logger.info(f"No USB devices found for {container_name}")
            return True
        
        logger.info(f"Syncing {len(usb_devices)} devices to {container_name}")
        
        # Fix permissions for all devices
        for device in usb_devices:
            try:
                # Method 1: chmod 666 (give everyone read/write)
                subprocess.run(
                    ["docker", "exec", "--user", "root", container_name, 
                     "chmod", "666", device],
                    capture_output=True,
                    timeout=5,
                    check=False
                )
                
                # Method 2: chown to user
                subprocess.run(
                    ["docker", "exec", "--user", "root", container_name,
                     "chown", f"{username}:dialout", device],
                    capture_output=True,
                    timeout=5,
                    check=False
                )
                
                logger.debug(f"✅ Fixed permissions: {device}")
                
            except Exception as e:
                logger.warning(f"Could not fix {device}: {e}")
        
        # Ensure user is in dialout group
        try:
            subprocess.run(
                ["docker", "exec", "--user", "root", container_name,
                 "usermod", "-a", "-G", "dialout", username],
                capture_output=True,
                timeout=5,
                check=False
            )
        except Exception as e:
            logger.debug(f"usermod dialout error (may be already in group): {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error syncing devices to {container_name}: {e}")
        return False

def restart_container_for_usb(container_name, username):
    """
    Restart container để nhận diện thiết bị USB mới
    
    IMPORTANT: Docker containers cần restart để:
    1. Re-mount /dev directory
    2. Re-scan USB devices
    3. Update device permissions
    """
    try:
        logger.info(f"🔄 Restarting {container_name} for USB detection...")
        
        # Check if container exists and is running
        status_result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Status}}", container_name],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if status_result.returncode != 0:
            logger.warning(f"Container {container_name} does not exist")
            return False
        
        status = status_result.stdout.strip()
        
        if status != "running":
            logger.info(f"Container {container_name} is {status}, starting it...")
            subprocess.run(["docker", "start", container_name], timeout=10)
            time.sleep(3)
        else:
            # Restart the container
            subprocess.run(
                ["docker", "restart", container_name],
                timeout=30,
                check=True
            )
            logger.info(f"✅ Container {container_name} restarted")
            
            # Wait for container to be fully ready
            time.sleep(5)
        
        # After restart, fix permissions
        sync_container_devices(container_name, username)
        
        logger.info(f"✅ USB sync complete for {container_name}")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Timeout restarting {container_name}")
        return False
    except Exception as e:
        logger.error(f"❌ Error restarting {container_name}: {e}")
        return False

def smart_container_resync(container_name, username):
    """
    Thông minh hơn: Chỉ restart nếu thật sự cần thiết
    
    Logic:
    1. Kiểm tra xem container có thể thấy devices không
    2. Nếu có → chỉ fix permissions
    3. Nếu không → phải restart
    """
    try:
        usb_devices = get_physical_usb_devices()
        
        if not usb_devices:
            logger.debug(f"No USB devices to sync for {container_name}")
            return True
        
        # Check if container can see at least one device
        can_see_devices = False
        for device in usb_devices:
            if container_has_device_access(container_name, device):
                can_see_devices = True
                break
        
        if can_see_devices:
            # Container có thể thấy devices → chỉ cần fix permissions
            logger.info(f"📝 {container_name} can see devices, fixing permissions only...")
            return sync_container_devices(container_name, username)
        else:
            # Container KHÔNG thấy devices → cần restart
            logger.info(f"🔄 {container_name} cannot see devices, restarting...")
            return restart_container_for_usb(container_name, username)
            
    except Exception as e:
        logger.error(f"Error in smart resync for {container_name}: {e}")
        # Fallback: restart anyway
        return restart_container_for_usb(container_name, username)

def batch_resync_all_containers():
    """
    Resync tất cả containers đang chạy
    """
    try:
        # Get all running containers with pattern *-dev
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=-dev", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.error("Failed to list Docker containers")
            return False
        
        containers = result.stdout.strip().split('\n')
        containers = [c for c in containers if c]  # Remove empty strings
        
        if not containers:
            logger.info("No running containers found")
            return True
        
        logger.info(f"🔄 Resyncing {len(containers)} containers...")
        
        success_count = 0
        for container_name in containers:
            try:
                # Extract username from container name (format: username-dev)
                username = container_name.replace('-dev', '')
                
                if smart_container_resync(container_name, username):
                    success_count += 1
                    logger.info(f"✅ {container_name} synced")
                else:
                    logger.warning(f"⚠️ {container_name} sync had issues")
                    
            except Exception as e:
                logger.error(f"Error syncing {container_name}: {e}")
        
        logger.info(f"✅ Batch resync complete: {success_count}/{len(containers)} successful")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"Error in batch resync: {e}")
        return False

# ============================================================================
# INTEGRATION FUNCTION - Gọi từ hardware.py
# ============================================================================

def handle_usb_rescan():
    """
    Main function được gọi từ /api/hardware/rescan
    
    Returns:
        dict: Status của quá trình resync
    """
    try:
        logger.info("=" * 70)
        logger.info("🔍 STARTING USB RESCAN AND CONTAINER SYNC")
        logger.info("=" * 70)
        
        # Step 1: Scan physical devices
        usb_devices = get_physical_usb_devices()
        logger.info(f"📱 Found {len(usb_devices)} USB devices: {usb_devices}")
        
        # Step 2: Resync all running containers
        resync_success = batch_resync_all_containers()
        
        result = {
            'success': resync_success,
            'devices_found': len(usb_devices),
            'devices': list(usb_devices),
            'message': 'Container sync complete' if resync_success else 'Container sync had issues'
        }
        
        logger.info("=" * 70)
        logger.info(f"✅ RESCAN COMPLETE: {result['message']}")
        logger.info("=" * 70)
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Error in USB rescan: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Rescan failed'
        }
