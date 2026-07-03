import requests
import time

BASE_URL = "http://localhost:3000"

def test_endpoint_rate_limit(endpoint, method="GET", data=None, json=None, limit=5, auth_token=None):
    print(f"Testing rate limiting on {endpoint} ({method})...")
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    hit = False
    # We try limit + 2 requests. 
    # If the limit is 5, the 6th should ideally hit 429.
    for i in range(limit + 2):
        try:
            if method == "GET":
                resp = requests.get(f"{BASE_URL}{endpoint}", headers=headers)
            elif method == "POST":
                resp = requests.post(f"{BASE_URL}{endpoint}", data=data, json=json, headers=headers)
            
            if resp.status_code == 429:
                print(f"Rate limit hit successfully on {endpoint} after {i+1} requests!")
                hit = True
                break
        except Exception as e:
            print(f"Request failed: {e}")
            break
    
    if not hit:
        print(f"Rate limit NOT hit on {endpoint} after {limit + 2} requests.")
    return hit

def run_tests():
    # 1. Login to get token first (while we have quota)
    print("Logging in to get token...")
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        print(f"Login failed with status {resp.status_code}: {resp.text}")
        return
    token = resp.json()["access_token"]
    print("Login successful.")

    # 2. Get Notice (Limit 5/minute)
    test_endpoint_rate_limit("/dpdp/notice", method="GET", limit=5)

    # 3. Privacy Export (Limit 1/minute)
    test_endpoint_rate_limit("/privacy/export", method="GET", auth_token=token, limit=1)

    # 4. Preferences (Limit 20/minute)
    test_endpoint_rate_limit("/preferences/contacts", method="GET", auth_token=token, limit=20)

    # 5. Finally, test Login rate limit (Limit 5/minute)
    # We do this last because it will block our IP from logging in again for a minute.
    test_endpoint_rate_limit("/auth/login", method="POST", data={"username": "admin", "password": "wrong"}, limit=5)

if __name__ == "__main__":
    run_tests()
