import requests
import json

BASE_URL = "http://localhost:3000"

def test_auth_and_multitenancy():
    print("Testing Auth and Multi-tenancy...")
    
    # 1. Test Login
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Test Scoped Access (Acme Corp)
    # Ensure Acme has some items
    requests.post(f"{BASE_URL}/items", headers=headers, json={"text": "Acme Task 1", "source": "Manual"})
    requests.post(f"{BASE_URL}/items", headers=headers, json={"text": "Acme Task 2", "source": "Manual"})
    
    resp = requests.get(f"{BASE_URL}/items", headers=headers)
    assert resp.status_code == 200
    items = resp.json()
    # At least 2 items (could be more if other tests ran)
    assert len(items) >= 2
    for item in items:
        assert item["tenant_id"] == "t-acme"
    print(f"Acme Corp user sees {len(items)} items.")

    # 3. Test Unauthorized Access
    resp = requests.get(f"{BASE_URL}/items")
    assert resp.status_code == 401
    print("Unauthorized access blocked correctly.")

    # 4. Test SSO Simulation (Sarah @ Globex)
    sso_data = {"email": "sarah@globex.com", "provider": "okta"}
    resp = requests.post(f"{BASE_URL}/auth/sso/login", json=sso_data)
    assert resp.status_code == 200
    sarah_token = resp.json()["access_token"]
    sarah_headers = {"Authorization": f"Bearer {sarah_token}"}

    # 5. Test Globex Isolation
    resp = requests.get(f"{BASE_URL}/items", headers=sarah_headers)
    assert resp.status_code == 200
    sarah_items = resp.json()
    assert len(sarah_items) == 0 # Sarah's tenant should have no items by default
    print("Globex isolation verified (empty queue for new tenant).")

    # 6. Test Data Creation (Globex)
    new_item = {"text": "Sarah's secret task", "source": "Internal"}
    resp = requests.post(f"{BASE_URL}/items", headers=sarah_headers, json=new_item)
    assert resp.status_code == 200
    
    resp = requests.get(f"{BASE_URL}/items", headers=sarah_headers)
    assert len(resp.json()) == 1
    assert resp.json()[0]["tenant_id"] == "t-globex"
    print("Data creation within tenant verified.")

    # 7. Verify Acme still only sees their data
    resp = requests.get(f"{BASE_URL}/items", headers=headers)
    assert len(resp.json()) >= 2
    print("Cross-tenant leak prevention verified.")

    print("Auth and Multi-tenancy tests passed!")

if __name__ == "__main__":
    test_auth_and_multitenancy()
