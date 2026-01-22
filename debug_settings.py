import requests
import json

def test_settings():
    url = 'http://localhost:5000/api/hsm/config'
    
    # Test 1: Switch to Real HSM (Expect Failure in this env)
    print("Test 1: Enabling Real HSM...")
    payload = {'useHsm': True, 'pin': '1234'}
    try:
        r = requests.post(url, json=payload)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Request Failed: {e}")

    # Test 2: Switch to Simulated HSM
    print("\nTest 2: Enabling Simulated HSM...")
    payload = {'useHsm': False}
    try:
        r = requests.post(url, json=payload)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
    except Exception as e:
        print(f"Request Failed: {e}")

if __name__ == '__main__':
    test_settings()
