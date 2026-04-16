from main import app
from routes.admin import admin_api_assign_device
import json

with app.test_client() as client:
    # Need to simulate session and json
    with client.session_transaction() as sess:
        sess['user_role'] = 'admin'
        sess['username'] = 'admin'
    
    response = client.post('/admin/api/devices/assign', 
                           json={"device_id": 1, "usernames": ["toan_ha"]})
    print("Status:", response.status_code)
    print("Data:", response.get_data(as_text=True))
    if response.status_code == 500:
        # To get the actual exception
        try:
            with app.test_request_context('/admin/api/devices/assign', 
                                          method='POST', 
                                          json={"device_id": 1, "usernames": ["toan_ha"]}):
                from flask import session
                session['user_role'] = 'admin'
                session['username'] = 'admin'
                admin_api_assign_device()
        except Exception as e:
            import traceback
            traceback.print_exc()
