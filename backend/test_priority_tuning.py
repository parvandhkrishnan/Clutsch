import unittest
import json
import time
import datetime
from fastapi.testclient import TestClient
from main import app
from database import db
from auth_routes import create_access_token

client = TestClient(app)

class TestPriorityTuning(unittest.TestCase):
    def setUp(self):
        # We don't clear DB because it might affect other things in this mock environment
        # but we can set specific weights for our test tenant
        self.tenant_id = "t-acme"
        self.token = create_access_token({"user_id": "u-1", "tenant_id": self.tenant_id, "role": "admin"})
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_custom_weights_persistence(self):
        weights = {
            "urgency": 0.5,
            "importance": 0.1,
            "sender_rank": 0.2,
            "deadline": 0.2
        }
        resp = client.post("/preferences/weights", json=weights, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        
        resp = client.get("/preferences/weights", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["urgency"], 0.5)

    def test_semantic_weights_persistence(self):
        semantics = {
            "weights": {
                "financial_impact": 0.5,
                "technical_debt": 0.0
            }
        }
        resp = client.post("/preferences/semantics", json=semantics, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        
        resp = client.get("/preferences/semantics", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["financial_impact"], 0.5)

    def test_semantic_prioritization(self):
        # Set a high boost for financial impact
        client.post("/preferences/semantics", json={"weights": {"financial_impact": 0.4}}, headers=self.headers)
        
        # Create an item with financial keywords
        item_data = {
            "text": "The budget for Q3 needs approval immediately for revenue targets.",
            "source": "manual"
        }
        client.post("/items", json=item_data, headers=self.headers)
        
        # Get priority feed
        resp = client.get("/priorities/feed", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        feed = resp.json()
        
        financial_item = next(i for i in feed if "budget" in i["text"])
        self.assertIn("Semantic match: financial impact", financial_item["explanation"])
        # With 0.4 boost, it should be quite high
        self.assertGreaterEqual(financial_item["importance"], 0.6) # 0.2 base + 0.4 boost

    def test_contextual_scaling_business_hours(self):
        # This test is tricky because it depends on the current time.
        # We can mock the time if we wanted, but for now let's just check if the explanation appears
        # if the test is run during business hours.
        resp = client.get("/priorities/feed", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        feed = resp.json()
        
        now = datetime.datetime.now()
        if 9 <= now.hour < 18:
            for item in feed:
                self.assertIn("Active business hours scaling applied", item["explanation"])

    def test_deadline_proximity_scaling(self):
        # Create an item with a deadline in 2 hours
        deadline = (datetime.datetime.now() + datetime.timedelta(hours=2)).isoformat()
        item_data = {
            "text": "Finish the report!",
            "source": "manual",
            "deadline": deadline
        }
        client.post("/items", json=item_data, headers=self.headers)
        
        resp = client.get("/priorities/feed", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        feed = resp.json()
        
        deadline_item = next(i for i in feed if "Finish the report" in i["text"])
        self.assertIn("Critical deadline proximity", deadline_item["explanation"])

    def test_entity_weighting(self):
        # Set project and client priorities
        client.post("/preferences/projects", json={"entity_id": "proj-123", "priority": "high"}, headers=self.headers)
        client.post("/preferences/clients", json={"entity_id": "client-456", "priority": "high"}, headers=self.headers)
        
        # Create items with these entities
        item_proj = {
            "text": "Project update",
            "source": "manual",
            "metadata": {"project_id": "proj-123"}
        }
        item_client = {
            "text": "Client request",
            "source": "manual",
            "metadata": {"client_id": "client-456"}
        }
        client.post("/items", json=item_proj, headers=self.headers)
        client.post("/items", json=item_client, headers=self.headers)
        
        resp = client.get("/priorities/feed", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        feed = resp.json()
        
        proj_item = next(i for i in feed if i.get("metadata", {}).get("project_id") == "proj-123")
        self.assertIn("High priority project (proj-123)", proj_item["explanation"])
        
        client_item = next(i for i in feed if i.get("metadata", {}).get("client_id") == "client-456")
        self.assertIn("High priority client (client-456)", client_item["explanation"])

if __name__ == "__main__":
    unittest.main()
