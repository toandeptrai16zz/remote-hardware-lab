import os
import time
import requests
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

TRIGGER_FILE = "/tmp/usb_event_trigger"
RESCAN_API_URL = "http://127.0.0.1:5000/api/hardware/rescan"

logging.info(f"Watcher started. Using robust method: checking for and deleting {TRIGGER_FILE}.")

while True:
    try:
        # 1. KIỂM TRA SỰ TỒN TẠI CỦA FILE TRIGGER
        if os.path.exists(TRIGGER_FILE):
            logging.info("Detected trigger file. Firing rescan API.")
            
            # 2. GỌI API ĐỂ CẬP NHẬT
            try:
                response = requests.post(RESCAN_API_URL)
                if response.status_code == 200:
                    logging.info(f"API call successful: {response.json().get('message')}")
                    
                    # 3. DỌN DẸP: XÓA FILE SAU KHI XỬ LÝ THÀNH CÔNG
                    try:
                        os.remove(TRIGGER_FILE)
                        logging.info(f"Successfully processed and removed trigger file.")
                    except OSError as e:
                        with open(TRIGGER_FILE, 'w') as f:
                            f.write('')
                    except OSError: pass        

                else:
                    logging.error(f"API call failed with status {response.status_code}: {response.text}")
            
            except requests.exceptions.RequestException as e:
                logging.error(f"Could not connect to Flask API: {e}")
                # Nếu không kết nối được, không xóa file để thử lại lần sau

        # Đợi 1 giây trước khi kiểm tra lại
        time.sleep(1)

    except Exception as e:
        logging.error(f"An unexpected error occurred in watcher loop: {e}")
        time.sleep(5)