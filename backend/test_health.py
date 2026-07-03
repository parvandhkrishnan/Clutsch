import requests
import time

BASE_URL = "http://localhost:3000"

def test_health_endpoints():
    print("Testing health and readiness endpoints...")
    
    # Test /health
    resp = requests.get(f"{BASE_URL}/health")
    print(f"GET /health: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    
    # Test /ready
    resp = requests.get(f"{BASE_URL}/ready")
    print(f"GET /ready: {resp.status_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["background_worker"] == "ok"
    
    # Test that they are NOT rate limited (hitting it many times)
    print("Verifying endpoints are NOT rate limited...")
    for i in range(15):
        resp_h = requests.get(f"{BASE_URL}/health")
        resp_r = requests.get(f"{BASE_URL}/ready")
        if resp_h.status_code == 429 or resp_r.status_code == 429:
            raise Exception("Health/Ready endpoints were rate limited!")
    print("Verified: Health/Ready endpoints are not rate limited.")

    print("Health and readiness tests passed!")

if __name__ == "__main__":
    try:
        test_health_endpoints()
    except Exception as e:
        print(f"Health tests failed: {e}")
        exit(1)
