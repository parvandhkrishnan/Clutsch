import requests
import json
import time

BASE_URL = "http://localhost:3000"

def test_dpdp_flow():
    print("Testing DPDP Flow...")
    
    # 1. Get Notice
    resp = requests.get(f"{BASE_URL}/dpdp/notice")
    if resp.status_code != 200:
        print(f"Notice failed: {resp.status_code} - {resp.text}")
    assert resp.status_code == 200
    assert "version" in resp.json()
    print("Privacy Notice verified.")

    # 2. Login as admin
    resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        print(f"Login failed: {resp.status_code} {resp.text}")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. Record Consent
    consent_data = {"version": "1.2", "purpose": "AI optimization", "extra_field": "ignore me"}
    resp = requests.post(f"{BASE_URL}/dpdp/consent", headers=headers, json=consent_data)
    assert resp.status_code == 200
    print("Consent recorded.")
    
    # 4. Get Consent History (Verify Data Minimization)
    resp = requests.get(f"{BASE_URL}/dpdp/consent", headers=headers)
    assert resp.status_code == 200
    consents = resp.json()["consent_history"]
    assert len(consents) >= 1
    last_consent = consents[-1]
    assert "extra_field" not in last_consent
    print("Consent history & data minimization verified.")
    
    # 5. Nominate Person
    nominee_data = {"name": "Nominee Name", "email": "nominee@example.com", "relationship": "Spouse", "secret": "shh"}
    resp = requests.post(f"{BASE_URL}/dpdp/nominate", headers=headers, json=nominee_data)
    assert resp.status_code == 200
    print("Nominee registered.")
    
    # 6. Get Nominee (Verify Data Minimization)
    resp = requests.get(f"{BASE_URL}/dpdp/nominee", headers=headers)
    assert resp.status_code == 200
    nominee = resp.json()["nominee"]
    assert nominee["name"] == "Nominee Name"
    assert "secret" not in nominee
    print("Nominee verified & data minimization verified.")
    
    # 7. Log Grievance
    grievance_data = {"subject": "Data Correction", "description": "My email is wrong."}
    resp = requests.post(f"{BASE_URL}/dpdp/grievance", headers=headers, json=grievance_data)
    assert resp.status_code == 200
    print("Grievance logged.")
    
    # 8. Admin Get Grievances
    resp = requests.get(f"{BASE_URL}/dpdp/admin/grievances", headers=headers)
    assert resp.status_code == 200
    grievances = resp.json()["grievances"]
    assert len(grievances) >= 1
    grievance_id = grievances[-1]["id"]
    print(f"Admin retrieved grievances. Last ID: {grievance_id}")
    
    # 9. Admin Resolve Grievance
    resp = requests.post(f"{BASE_URL}/dpdp/admin/grievances/{grievance_id}/resolve", headers=headers)
    assert resp.status_code == 200
    print("Grievance resolved by admin.")
    
    # 10. Verify Grievance Status
    resp = requests.get(f"{BASE_URL}/dpdp/grievances", headers=headers)
    assert resp.status_code == 200
    my_grievances = resp.json()["grievances"]
    assert any(g["id"] == grievance_id and g["status"] == "resolved" for g in my_grievances)
    print("Grievance resolution verified by user.")
    
    print("DPDP Flow tests passed!")

if __name__ == "__main__":
    try:
        test_dpdp_flow()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
