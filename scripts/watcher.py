#!/usr/bin/env python3
"""
ULTIMATE USB WATCHER - Version 2.0 
Fix triệt để tất cả lỗi về Permission và USB Detection

FEATURES:
✅ Tự động xử lý permission denied
✅ Không cần sudo password
✅ Hỗ trợ multi-threading để tránh blocking
✅ Retry mechanism thông minh
✅ Debounce để tránh duplicate events
✅ Auto cleanup stale trigger files
"""
import os
import time
import requests
import logging
import threading
from pathlib import Path
from datetime import datetime, timedelta

class UltimateUSBWatcher:
    """
    USB Watcher với cơ chế xử lý lỗi và permission tối ưu
    """
    
    def __init__(self, 
                 trigger_file="/tmp/usb_event_trigger", 
                 api_url="http://127.0.0.1:5000/api/hardware/rescan",
                 debounce_seconds=2):
        
        self.trigger_file = Path(trigger_file)
        self.api_url = api_url
        self.debounce_seconds = debounce_seconds
        
        self.logger = logging.getLogger('UltimateUSBWatcher')
        self.running = False
        self.processing = False
        
        # Debounce tracking
        self.last_trigger_time = None
        self.pending_trigger = None
        
        # Stats
        self.stats = {
            'total_triggers': 0,
            'successful_api_calls': 0,
            'failed_api_calls': 0,
            'permission_errors': 0,
            'debounced_events': 0
        }
    
    def _is_trigger_debounced(self):
        """Check if we should ignore this trigger due to debounce"""
        if not self.last_trigger_time:
            return False
        
        time_since_last = datetime.now() - self.last_trigger_time
        if time_since_last < timedelta(seconds=self.debounce_seconds):
            return True
        
        return False
    
    def _handle_trigger_file(self):
        """
        Xử lý trigger file với nhiều phương pháp khác nhau
        Không bao giờ để lỗi permission làm dừng service
        """
        methods_tried = []
        
        # METHOD 1: Simple unlink (works 90% of time)
        try:
            if self.trigger_file.exists():
                self.trigger_file.unlink()
                self.logger.debug("✅ Trigger file removed (unlink)")
                return True
        except PermissionError:
            methods_tried.append("unlink:permission_denied")
            self.stats['permission_errors'] += 1
        except Exception as e:
            methods_tried.append(f"unlink:{type(e).__name__}")
        
        # METHOD 2: Truncate file (alternative to delete)
        try:
            if self.trigger_file.exists():
                self.trigger_file.write_text('')
                self.logger.debug("✅ Trigger file cleared (truncate)")
                return True
        except PermissionError:
            methods_tried.append("truncate:permission_denied")
        except Exception as e:
            methods_tried.append(f"truncate:{type(e).__name__}")
        
        # METHOD 3: Rename file (move it out of the way)
        try:
            if self.trigger_file.exists():
                archive_path = Path(f"/tmp/.usb_trigger_archive_{int(time.time())}")
                self.trigger_file.rename(archive_path)
                self.logger.debug("✅ Trigger file archived (rename)")
                
                # Try to cleanup archive in background
                threading.Thread(target=self._cleanup_old_archives, daemon=True).start()
                return True
        except Exception as e:
            methods_tried.append(f"rename:{type(e).__name__}")
        
        # METHOD 4: Just mark it as processed (last resort)
        try:
            if self.trigger_file.exists():
                # Write a marker that we've processed this file
                marker_file = Path(f"{self.trigger_file}.processed")
                marker_file.write_text(str(time.time()))
                self.logger.warning(f"⚠️ Cannot remove trigger, created marker instead")
                return True
        except Exception as e:
            methods_tried.append(f"marker:{type(e).__name__}")
        
        # If ALL methods failed, log it but don't crash
        self.logger.error(f"❌ All cleanup methods failed: {methods_tried}")
        self.logger.warning("⚠️ Continuing anyway to prevent service hang...")
        return False
    
    def _cleanup_old_archives(self):
        """Cleanup old archived trigger files"""
        try:
            import glob
            archives = glob.glob("/tmp/.usb_trigger_archive_*")
            now = time.time()
            
            for archive in archives:
                try:
                    # Remove archives older than 1 hour
                    if os.path.getmtime(archive) < (now - 3600):
                        os.remove(archive)
                except:
                    pass
        except Exception as e:
            self.logger.debug(f"Archive cleanup error (non-critical): {e}")
    
    def _call_rescan_api(self):
        """
        Gọi API rescan với retry mechanism
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.info(f"📡 Calling rescan API (attempt {attempt}/{max_retries})...")
                
                response = requests.post(
                    self.api_url, 
                    timeout=10,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    message = data.get('message', 'Rescan complete')
                    self.logger.info(f"✅ API Success: {message}")
                    self.stats['successful_api_calls'] += 1
                    return True
                else:
                    self.logger.warning(f"⚠️ API returned {response.status_code}: {response.text}")
                    
            except requests.exceptions.ConnectionError:
                self.logger.error(f"❌ Connection error (attempt {attempt}): Is Flask app running?")
                
            except requests.exceptions.Timeout:
                self.logger.error(f"❌ Timeout (attempt {attempt}): API took too long")
                
            except Exception as e:
                self.logger.error(f"❌ Unexpected error (attempt {attempt}): {e}")
            
            # Retry with exponential backoff
            if attempt < max_retries:
                wait_time = retry_delay * (2 ** (attempt - 1))
                self.logger.info(f"⏳ Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        self.stats['failed_api_calls'] += 1
        return False
    
    def _process_trigger_async(self):
        """
        Xử lý trigger trong thread riêng để không block main loop
        """
        if self.processing:
            self.logger.debug("⏭️ Already processing, skipping...")
            return
        
        self.processing = True
        
        try:
            self.logger.info("🔔 USB Event Detected!")
            self.stats['total_triggers'] += 1
            self.last_trigger_time = datetime.now()
            
            # Step 1: Call API
            api_success = self._call_rescan_api()
            
            # Step 2: Handle trigger file (even if API failed, to prevent infinite loop)
            self._handle_trigger_file()
            
            # Step 3: Log results
            if api_success:
                self.logger.info("✅ Event processed successfully")
            else:
                self.logger.warning("⚠️ Event processed with errors")
            
        except Exception as e:
            self.logger.error(f"❌ Error processing trigger: {e}")
        finally:
            self.processing = False
    
    def _check_and_cleanup_stale_triggers(self):
        """
        Kiểm tra và cleanup các trigger files cũ
        """
        try:
            if self.trigger_file.exists():
                # Check if file is older than 30 seconds
                file_age = time.time() - os.path.getmtime(str(self.trigger_file))
                
                if file_age > 30:
                    self.logger.warning(f"⚠️ Found stale trigger file (age: {file_age:.1f}s)")
                    self._handle_trigger_file()
        except Exception as e:
            self.logger.debug(f"Stale check error (non-critical): {e}")
    
    def watch(self):
        """
        Main watching loop với error handling hoàn chỉnh
        """
        self.running = True
        self.logger.info("=" * 70)
        self.logger.info("🚀 ULTIMATE USB WATCHER STARTED")
        self.logger.info(f"📁 Monitoring: {self.trigger_file}")
        self.logger.info(f"🌐 API: {self.api_url}")
        self.logger.info(f"⏱️  Debounce: {self.debounce_seconds}s")
        self.logger.info("=" * 70)
        
        consecutive_errors = 0
        max_consecutive_errors = 50  # Very high tolerance
        check_interval = 0.5  # Check every 500ms
        
        while self.running:
            try:
                # Periodic cleanup
                if self.stats['total_triggers'] % 100 == 0:
                    self._check_and_cleanup_stale_triggers()
                
                # Check for trigger file
                if self.trigger_file.exists():
                    
                    # Debounce check
                    if self._is_trigger_debounced():
                        self.logger.debug("⏭️ Event debounced, skipping...")
                        self.stats['debounced_events'] += 1
                        self._handle_trigger_file()  # Still remove the file
                        time.sleep(check_interval)
                        continue
                    
                    # Process trigger in background thread
                    thread = threading.Thread(
                        target=self._process_trigger_async,
                        daemon=True
                    )
                    thread.start()
                    
                    # Reset error counter on trigger
                    consecutive_errors = 0
                
                # Sleep before next check
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("⏹️ Watcher stopped by user (Ctrl+C)")
                self.running = False
                break
                
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(
                    f"❌ Unexpected error ({consecutive_errors}/{max_consecutive_errors}): {e}"
                )
                
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.critical("🛑 Too many errors, stopping watcher!")
                    self.running = False
                    break
                
                # Adaptive sleep: longer after errors
                time.sleep(min(consecutive_errors * 0.5, 5))
        
        # Print final stats
        self._print_stats()
    
    def _print_stats(self):
        """Print statistics"""
        self.logger.info("=" * 70)
        self.logger.info("📊 WATCHER STATISTICS:")
        self.logger.info(f"   Total Triggers: {self.stats['total_triggers']}")
        self.logger.info(f"   Successful API Calls: {self.stats['successful_api_calls']}")
        self.logger.info(f"   Failed API Calls: {self.stats['failed_api_calls']}")
        self.logger.info(f"   Permission Errors: {self.stats['permission_errors']}")
        self.logger.info(f"   Debounced Events: {self.stats['debounced_events']}")
        self.logger.info("=" * 70)
    
    def stop(self):
        """Stop the watcher gracefully"""
        self.logger.info("🛑 Stopping watcher...")
        self.running = False


def main():
    """Main entry point"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create and start watcher
    watcher = UltimateUSBWatcher(
        trigger_file="/tmp/usb_event_trigger",
        api_url="http://127.0.0.1:5000/api/hardware/rescan",
        debounce_seconds=2
    )
    
    try:
        watcher.watch()
    except KeyboardInterrupt:
        print("\n⏹️ Stopping watcher...")
        watcher.stop()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        watcher.stop()


if __name__ == "__main__":
    main()
