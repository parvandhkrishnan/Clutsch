import requests
import time
import json

BASE_URL = "http://localhost:3000"

def test_sync_enabled_setting():
    print("--- Testing Sync Enabled Setting ---")
    
    # 1. Login
    login_resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "john", "password": "password"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Connect Jira
    requests.post(
        f"{BASE_URL}/integrations/jira/connect", 
        json={"token": "mock-jira-token"},
        headers=headers
    )

    # 3. Disable Jira
    requests.patch(
        f"{BASE_URL}/integrations/jira/settings",
        json={"enabled": False},
        headers=headers
    )
    print("Jira integration disabled.")

    # 4. Trigger sync
    sync_resp = requests.post(f"{BASE_URL}/integrations/sync", headers=headers)
    print(f"Sync triggered: {sync_resp.json().get('status')}")
    
    # Wait for background worker
    print("Waiting for sync...")
    time.sleep(5)

    # 5. Check items
    feed_resp = requests.get(f"{BASE_URL}/priorities/feed", headers=headers)
    items = feed_resp.json()
    jira_items = [i for i in items if i.get("source") == "jira"]
    print(f"Found {len(jira_items)} Jira items in feed.")
    
    if len(jira_items) == 0:
        print("SUCCESS: Sync respected disabled setting (no items fetched).")
    else:
        print("FAILURE: Sync fetched items despite being disabled.")

    # 6. Re-enable Jira
    requests.patch(
        f"{BASE_URL}/integrations/jira/settings",
        json={"enabled": True},
        headers=headers
    )
    print("Jira integration re-enabled.")

    # 7. Trigger sync again
    requests.post(f"{BASE_URL}/integrations/sync", headers=headers)
    print("Waiting for sync...")
    time.sleep(5)

    # 8. Check items again
    feed_resp = requests.get(f"{BASE_URL}/priorities/feed", headers=headers)
    items = feed_resp.json()
    jira_items = [i for i in items if i.get("source") == "jira"]
    print(f"Found {len(jira_items)} Jira items in feed.")
    
    if len(jira_items) > 0:
        print("SUCCESS: Sync fetched items after re-enabling.")
    else:
        print("FAILURE: Sync still not fetching items.")

if __name__ == "__main__":
    test_sync_enabled_setting()
