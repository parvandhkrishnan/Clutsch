import requests
import time
import json

BASE_URL = "http://localhost:3000"

def test_integration_lifecycle():
    print("--- Testing Integration Lifecycle ---")
    
    # 1. Login
    print("\n1. Logging in...")
    login_resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "john", "password": "password"})
    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        return
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")

    # 2. Connect Jira
    print("\n2. Connecting Jira...")
    connect_resp = requests.post(
        f"{BASE_URL}/integrations/jira/connect", 
        json={"token": "mock-jira-token"},
        headers=headers
    )
    print(f"Connect response: {connect_resp.status_code} - {connect_resp.json()}")

    # 3. List integrations (check default settings)
    print("\n3. Listing integrations...")
    list_resp = requests.get(f"{BASE_URL}/integrations", headers=headers)
    print(f"Integrations: {json.dumps(list_resp.json(), indent=2)}")

    # 4. Update settings
    print("\n4. Updating settings for Jira...")
    patch_resp = requests.patch(
        f"{BASE_URL}/integrations/jira/settings",
        json={
            "enabled": False,
            "sync_frequency": 30,
            "priority_threshold": 80
        },
        headers=headers
    )
    print(f"Patch response: {patch_resp.status_code} - {patch_resp.json()}")

    # 5. List integrations again (verify changes)
    print("\n5. Verifying settings change...")
    list_resp = requests.get(f"{BASE_URL}/integrations", headers=headers)
    jira_config = next((i for i in list_resp.json()["connected"] if i["provider"] == "jira"), None)
    if jira_config:
        print(f"Jira Settings: {json.dumps(jira_config['settings'], indent=2)}")
        if jira_config["settings"]["enabled"] == False and jira_config["settings"]["sync_frequency"] == 30:
            print("SUCCESS: Settings updated correctly.")
        else:
            print("FAILURE: Settings not updated correctly.")
    else:
        print("FAILURE: Jira integration not found.")

    # 6. Disconnect Jira
    print("\n6. Disconnecting Jira...")
    delete_resp = requests.delete(f"{BASE_URL}/integrations/jira", headers=headers)
    print(f"Delete response: {delete_resp.status_code} - {delete_resp.json()}")

    # 7. List integrations finally
    print("\n7. Final check...")
    list_resp = requests.get(f"{BASE_URL}/integrations", headers=headers)
    connected_providers = [i["provider"] for i in list_resp.json()["connected"]]
    print(f"Connected providers: {connected_providers}")
    if "jira" not in connected_providers:
        print("SUCCESS: Jira disconnected correctly.")
    else:
        print("FAILURE: Jira still connected.")

if __name__ == "__main__":
    test_integration_lifecycle()
