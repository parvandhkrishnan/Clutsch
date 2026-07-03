import requests
import time

BASE_URL = "http://localhost:3000"

def test_oauth_flow():
    # 1. Login
    print("Logging in...")
    login_res = requests.post(f"{BASE_URL}/auth/login", data={"username": "admin", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Auth URL
    print("\nGetting Auth URL for Gmail...")
    auth_url_res = requests.get(f"{BASE_URL}/integrations/gmail/auth-url", headers=headers)
    print(f"Auth URL: {auth_url_res.json()['url']}")

    # 3. Simulate Redirect to Callback (normally done by Google)
    print("\nSimulating Callback...")
    callback_res = requests.get(f"{BASE_URL}/integrations/gmail/callback?code=mock-code-123&state=xyz")
    code = callback_res.json()["code"]
    print(f"Received Code: {code}")

    # 4. Exchange Code for Tokens
    print("\nExchanging Code for Tokens...")
    exchange_res = requests.post(
        f"{BASE_URL}/integrations/gmail/exchange", 
        headers=headers,
        json={"code": code}
    )
    print(f"Exchange Result: {exchange_res.json()}")

    # 5. List Integrations to verify connection
    print("\nVerifying connection in list...")
    list_res = requests.get(f"{BASE_URL}/integrations", headers=headers)
    connected = [i["provider"] for i in list_res.json()["connected"]]
    print(f"Connected integrations: {connected}")
    if "gmail" in connected:
        print("SUCCESS: Gmail is connected via OAuth exchange.")
    else:
        print("FAILURE: Gmail not found in connected list.")

    # 6. Trigger Sync to test token usage (and refresh logic)
    print("\nTriggering Sync...")
    sync_res = requests.post(f"{BASE_URL}/integrations/sync", headers=headers)
    print(f"Sync response: {sync_res.json()}")
    
    # Wait for sync to complete (since it's background)
    time.sleep(2)
    
    # 7. Check priority feed
    print("\nChecking priority feed...")
    feed_res = requests.get(f"{BASE_URL}/priorities/feed", headers=headers)
    items = feed_res.json()["items"]
    print(f"Found {len(items)} items in feed.")
    gmail_items = [i for i in items if i["source"] == "gmail"]
    print(f"Gmail items: {len(gmail_items)}")

if __name__ == "__main__":
    test_oauth_flow()
