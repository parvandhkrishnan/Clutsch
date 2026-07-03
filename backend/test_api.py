import requests
import json
import time

BASE_URL = "http://localhost:3000"

def test_endpoints():
    print("Testing API endpoints...")
    
    # 1. Connect integrations
    providers = ["gmail", "outlook", "slack", "teams", "whatsapp", "jira"]
    for p in providers:
        resp = requests.post(f"{BASE_URL}/integrations/{p}/connect")
        print(f"Connecting {p}: {resp.status_code}")
        assert resp.status_code == 200

    # 2. Test /items
    resp = requests.get(f"{BASE_URL}/items")
    print(f"GET /items: {resp.status_code}")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) > 0
    assert "priorityScore" in items[0]
    assert "priorityTier" in items[0]
    assert "explanation" in items[0]

    # 3. Test /priorities/feed
    resp = requests.get(f"{BASE_URL}/priorities/feed?limit=5&offset=0")
    print(f"GET /priorities/feed: {resp.status_code}")
    assert resp.status_code == 200
    feed = resp.json()
    assert "items" in feed
    assert "total" in feed
    assert len(feed["items"]) <= 5
    
    # 4. Test filtering
    resp = requests.get(f"{BASE_URL}/priorities/feed?provider=slack")
    assert resp.status_code == 200
    slack_feed = resp.json()
    for item in slack_feed["items"]:
        assert item["source"].lower() == "slack"
    print("Filtering tests passed!")

    print("API endpoint tests passed!\n")

if __name__ == "__main__":
    try:
        test_endpoints()
    except Exception as e:
        print(f"API tests failed: {e}")
        # Make sure server is running
        exit(1)
