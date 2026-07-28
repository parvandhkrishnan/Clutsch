import asyncio
from fastapi.testclient import TestClient
from main import app
from database import db
import datetime
import time

def test_priority_feedback_loop():
    client = TestClient(app)
    asyncio.run(db.clear())
    
    # 1. Login
    response = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Setup initial semantic weights
    client.post("/preferences/semantics", json={"weights": {"technical_debt": 0.1}}, headers=headers)
    
    # 3. Create an item with technical_debt semantics
    item_id = "test-item-1"
    item_data = {
        "id": item_id,
        "tenant_id": "t-acme",
        "text": "Fix this legacy bug ASAP",
        "source": "manual",
        "metadata": {"project_id": "proj-1"},
        "timestamp": time.time(),
        "priorityTier": "medium" # Assume it was ranked medium
    }
    asyncio.run(db.add_item(item_data))
    
    # 4. Submit correction feedback (should be higher)
    feedback_data = {
        "item_id": item_id,
        "feedback_type": "correction",
        "suggested_tier": "high"
    }
    response = client.post("/feedback/priority", json=feedback_data, headers=headers)
    assert response.status_code == 200
    
    # 5. Check if weights were adjusted
    # technical_debt should have increased from 0.1 to 0.15
    response = client.get("/preferences/semantics", headers=headers)
    weights = response.json()
    assert weights["technical_debt"] == 0.15
    
    # 6. Check if project priority was adjusted
    response = client.get("/preferences/projects", headers=headers)
    projects = response.json()
    assert projects["proj-1"] == "high"
    
    print("Priority Feedback Loop test passed!")

if __name__ == "__main__":
    test_priority_feedback_loop()
