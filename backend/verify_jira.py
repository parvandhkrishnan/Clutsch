import requests
import json
import time

BASE_URL = "http://localhost:3000"

def test_jira_integration():
    # Login
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "john", "password": "password"})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Connect Jira
    resp = requests.post(f"{BASE_URL}/integrations/jira/connect", 
                         headers=headers, 
                         json={"token": "mock-jira-token"})
    print(f"Connect Jira: {resp.status_code} {resp.text}")
    
    # Sync
    resp = requests.post(f"{BASE_URL}/integrations/sync", headers=headers)
    print(f"Sync: {resp.status_code} {resp.text}")
    
    # Wait for sync
    print("Waiting for sync...")
    time.sleep(5)
    
    # Get feed
    resp = requests.get(f"{BASE_URL}/priorities/feed", headers=headers)
    if resp.status_code != 200:
        print(f"Feed failed: {resp.status_code} {resp.text}")
        return
    
    items = resp.json()
    print(f"Received {len(items)} items in feed.")
    
    for item in items:
        if item["source"] == "jira":
            print(f"\nJira Item: {item['subject']}")
            print(f"Score: {item['priorityScore']}")
            print(f"Tier: {item['priorityTier']}")
            print(f"Explanation: {item['explanation']}")

if __name__ == "__main__":
    test_jira_integration()
