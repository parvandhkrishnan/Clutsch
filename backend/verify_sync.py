import requests
import time
import os

BASE_URL = "http://localhost:3000"

def verify_sync():
    print("Verifying sync process...")
    
    # 1. Login
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Logged in.")

    # 2. Connect Slack
    resp = requests.post(f"{BASE_URL}/integrations/slack/connect", 
                         json={"token": "fake-token"}, 
                         headers=headers)
    if resp.status_code != 200:
        print(f"Connect Slack failed: {resp.text}")
        return
    print("Slack connected.")

    # 3. Trigger Sync
    resp = requests.post(f"{BASE_URL}/integrations/sync", headers=headers)
    if resp.status_code != 200:
        print(f"Trigger sync failed: {resp.text}")
        return
    task_id = resp.json()["task_id"]
    print(f"Sync triggered. Task ID: {task_id}")

    # 4. Wait for sync to complete (it's background)
    print("Waiting for sync to complete...")
    time.sleep(2) # Should be enough for mock data

    # 5. Check items
    resp = requests.get(f"{BASE_URL}/items", headers=headers)
    if resp.status_code != 200:
        print(f"Get items failed: {resp.text}")
        return
    
    items = resp.json()
    print(f"Found {len(items)} items.")
    
    slack_items = [i for i in items if i["source"] == "slack"]
    print(f"Found {len(slack_items)} Slack items.")
    
    if len(slack_items) > 0:
        print("Sync verification SUCCESSFUL!")
        # Print first item to verify structure
        print("Sample item:", slack_items[0])
    else:
        print("Sync verification FAILED: No Slack items found.")

if __name__ == "__main__":
    verify_sync()
