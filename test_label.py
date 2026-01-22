import requests
import json

def test_label():
    url = 'http://localhost:5000/api/hsm/config'
    
    # Test: Enable Real HSM with custom label
    print("Testing custom label configuration...")
    payload = {'useHsm': True, 'pin': '1234', 'label': 'custom_kek_label'}
    try:
        r = requests.post(url, json=payload)
        print(f"Status: {r.status_code}")
        # We expect a 400 or 500 error because HSM lib might not be found or key not found
        # But we want to see if the service TRIED to use the label?
        # Actually, RealHsmService init checks lib path first.
        # If env vars are set correctly (via run_test_env.sh/start.sh context), it might proceed to open session.
        # But without a real token/slot, it might fail at openSession.
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Request Failed: {e}")

if __name__ == '__main__':
    test_label()
