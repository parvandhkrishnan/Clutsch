import asyncio
import json
from fastapi.testclient import TestClient
from main import app
from database import db

def test_custom_integration_crud():
    client = TestClient(app)
    
    # Login to get token
    response = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Add custom integration
    config = {
        "name": "My Custom API",
        "url": "https://api.example.com/data",
        "mapping": {"text": "msg", "external_id": "uid"},
        "urgency_triggers": [{"field": "priority", "value": "high", "boost": 0.5}]
    }
    response = client.post("/integrations/custom", json=config, headers=headers)
    assert response.status_code == 200
    integration_id = response.json()["id"]
    
    # List integrations
    response = client.get("/integrations/custom", headers=headers)
    assert response.status_code == 200
    # get_custom_integrations() now returns a list of dicts (each with an
    # "id" key), not a {id: config} dict, so membership must be checked by id.
    assert any(c["id"] == integration_id for c in response.json())
    
    # Update integration
    client.patch(f"/integrations/custom/{integration_id}", json={"enabled": False}, headers=headers)
    assert next(c for c in asyncio.run(db.get_custom_integrations("t-acme")) if c["id"] == integration_id)["enabled"] == False

    # Delete integration
    client.delete(f"/integrations/custom/{integration_id}", headers=headers)
    assert not any(c["id"] == integration_id for c in asyncio.run(db.get_custom_integrations("t-acme")))
    print("Custom Integration CRUD test passed!")

def test_custom_integration_sync_and_scoring():
    client = TestClient(app)
    asyncio.run(db.clear())
    
    # Login
    response = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Add a custom integration that points to a mock server or we just mock the fetch
    # For testing, we'll manually insert an item that looks like it came from a custom adapter
    config = {
        "name": "AlertSystem",
        "url": "http://mock-api/alerts",
        "mapping": {"text": "message", "external_id": "id"},
        "urgency_triggers": [{"field": "severity", "value": "critical", "boost": 0.5}]
    }
    integration_id = asyncio.run(db.add_custom_integration("t-acme", config))
    
    # Simulate an item fetched via this custom integration
    item_data = {
        "id": "item-1",
        "tenant_id": "t-acme",
        "text": "Server down in rack 4",
        "source": "AlertSystem",
        "external_id": "alert-101",
        "metadata": {
            "severity": "critical",
            "custom_boost": 0.5 # Normally set by CustomAdapter._normalize
        },
        "timestamp": 123456789
    }
    asyncio.run(db.upsert_items([item_data]))
    
    # Get priority feed
    response = client.get("/priorities/feed", headers=headers)
    items = response.json()
    
    # Check if the boost was applied
    custom_item = next(i for i in items if i["id"] == "item-1")
    assert custom_item["importance"] >= 0.5
    assert "Custom urgency trigger matched" in custom_item["explanation"]
    
    print("Custom Integration Sync and Scoring test passed!")

def test_workflow_engine():
    client = TestClient(app)
    asyncio.run(db.clear())
    
    # Login
    response = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create a workflow: auto-archive items with score < 40
    workflow_config = {
        "name": "Auto-Archive Noise",
        "conditions": [
            {"field": "priorityScore", "operator": "lt", "value": 40}
        ],
        "actions": [
            {"type": "archive"}
        ]
    }
    client.post("/workflows", json=workflow_config, headers=headers)
    
    # 2. Simulate items via mock integration
    # We'll connect a mock slack integration
    client.post("/integrations/slack/connect", json={"token": "mock-token"}, headers=headers)
    
    # We need to mock the SlackAdapter.fetch_items to return our test items
    from adapters.slack import SlackAdapter
    from adapters.base import NormalizedCommunication
    import datetime

    now_iso = datetime.datetime.now().isoformat()
    mock_items = [
        NormalizedCommunication(
            id="high-p", 
            content="Urgent bug!", 
            source="slack", 
            external_id="1", 
            sender={"handle": "alice"}, 
            recipient="me", 
            timestamp=now_iso,
            metadata={}
        ),
        NormalizedCommunication(
            id="low-p", 
            content="Lunch menu", 
            source="slack", 
            external_id="2", 
            sender={"handle": "bob"}, 
            recipient="me", 
            timestamp=now_iso,
            metadata={}
        )
    ]
    
    # Patch SlackAdapter.fetch_items
    import unittest.mock as mock
    with mock.patch.object(SlackAdapter, 'fetch_items', return_value=mock_items):
        # 3. Trigger a sync
        from integration_routes import sync_all_integrations
        asyncio.run(sync_all_integrations("t-acme"))
    
    # 4. Check results
    from services import archived_items
    print(f"Archived items: {archived_items.get('t-acme', set())}")
    
    # Let's check the items in DB to see their scores
    db_items = asyncio.run(db.get_items("t-acme"))
    for item in db_items:
        print(f"Item {item['id']} score: {item.get('priorityScore')}")

    assert "low-p" in archived_items.get("t-acme", set())
    assert "high-p" not in archived_items.get("t-acme", set())
    
    print("Workflow Engine test passed!")

if __name__ == "__main__":
    test_custom_integration_crud()
    test_custom_integration_sync_and_scoring()
    test_workflow_engine()
