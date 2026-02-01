"""
Background Services Manager
Manages background tasks like USB watcher, file monitoring, etc.
"""
import threading
import logging
from pathlib import Path
import sys

# Add scripts directory to Python path
SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

logger = logging.getLogger('BackgroundServices')


class BackgroundServices:
    """Manager for all background services"""
    
    def __init__(self):
        self.services = {}
        self.threads = {}
        
    def start_usb_watcher(self):
        """Start USB watcher service in background thread"""
        try:
            from watcher import USBWatcher
            
            watcher = USBWatcher()
            self.services['usb_watcher'] = watcher
            
            # Start in daemon thread so it stops when main app stops
            thread = threading.Thread(
                target=watcher.watch,
                name="USBWatcher",
                daemon=True
            )
            thread.start()
            self.threads['usb_watcher'] = thread
            
            logger.info(" USB Watcher service started")
            return True
            
        except ImportError as e:
            logger.error(f" Cannot import watcher module: {e}")
            return False
        except Exception as e:
            logger.error(f" Failed to start USB Watcher: {e}")
            return False
    
    def stop_all(self):
        """Stop all background services gracefully"""
        logger.info(" Stopping all background services...")
        
        for name, service in self.services.items():
            try:
                if hasattr(service, 'stop'):
                    service.stop()
                    logger.info(f"✅ Stopped {name}")
            except Exception as e:
                logger.error(f" Error stopping {name}: {e}")
        
        # Wait for threads to finish (with timeout)
        for name, thread in self.threads.items():
            try:
                thread.join(timeout=5)
                if thread.is_alive():
                    logger.warning(f" Thread {name} did not stop in time")
                else:
                    logger.info(f" Thread {name} stopped")
            except Exception as e:
                logger.error(f" Error joining thread {name}: {e}")
    
    def get_status(self):
        """Get status of all services"""
        status = {}
        for name, thread in self.threads.items():
            status[name] = {
                'running': thread.is_alive(),
                'daemon': thread.daemon
            }
        return status


# Global instance
_background_services = None


def get_background_services():
    """Get or create the global BackgroundServices instance"""
    global _background_services
    if _background_services is None:
        _background_services = BackgroundServices()
    return _background_services


def init_background_services():
    """Initialize and start all background services"""
    services = get_background_services()
    
    logger.info("🚀 Initializing background services...")
    
    # Start USB watcher
    if services.start_usb_watcher():
        logger.info("✅ All background services started successfully")
    else:
        logger.warning("⚠️ Some background services failed to start")
    
    return services


def stop_background_services():
    """Stop all background services"""
    global _background_services
    if _background_services:
        _background_services.stop_all()
        _background_services = None
