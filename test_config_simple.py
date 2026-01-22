import requests
import json
import time

def test_full_config():
    url = 'http://localhost:5000/api/hsm/config'
    
    # Requested Settings
    payload = {
        'useHsm': True, 
        'pin': '1111', 
        'label': 'master_key',
        'slotId': 1
    }
    
    print(f"Applying Config: {payload}")
    try:
        r = requests.post(url, json=payload)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Request Failed: {e}")

if __name__ == '__main__':
    # Wait for server restart
    time.sleep(2) 
    test_full_config()
