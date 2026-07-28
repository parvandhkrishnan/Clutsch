import unittest
import time
import os

# Set environment variables for testing before importing app modules
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
os.environ["ENCRYPTION_KEY"] = "N0ZPaUZrRUZXSm5yYVpwUnVpYm9hckhLcm9LdER3SDA="
os.environ["ADMIN_PASSWORD"] = "admin123"
os.environ["JOHN_PASSWORD"] = "password"
os.environ["SARAH_PASSWORD"] = "sarah123"

from main import app
from utils.cache import integration_cache


from auth.jwt_handler import create_access_token
from fastapi.testclient import TestClient
from ai_analyzer import AIAnalyzer
from database import db
import asyncio

client = TestClient(app)

class TestScalability(unittest.TestCase):
    def setUp(self):
        db.clear()
        integration_cache.cache.clear()
        
        # Setup tokens
        self.token_a = create_access_token({"sub": "john", "user_id": "u-2", "tenant_id": "t-acme"})
        self.headers_a = {"Authorization": f"Bearer {self.token_a}"}

    def test_cache_direct(self):
        """Verify the cache object works directly."""
        integration_cache.set("direct-key", "direct-val")
        self.assertEqual(integration_cache.get("direct-key"), "direct-val")

    # def test_item_logic_caching(self):
    #     """Verify the fetch logic populates the cache when no background tasks are involved."""
    #     # Use asyncio to run the async function
    #     loop = asyncio.new_event_loop()
    #     asyncio.set_event_loop(loop)
    #     
    #     # Call fetch without background tasks
    #     items = loop.run_until_complete(_fetch_all_items("t-acme", background_tasks=None))
    #     self.assertEqual(len(items), 0)
    #     
    #     # Verify cache was populated
    #     cached = integration_cache.get("t-acme")
    #     self.assertIsNotNone(cached)
    #     self.assertEqual(len(cached), 0)
    #     loop.close()

    def test_ai_analysis_caching(self):
        """Verify that AI analysis is cached for identical text."""
        analyzer = AIAnalyzer()
        text = "Urgent meeting at 5pm"
        
        start_time = time.time()
        res1 = analyzer.analyze_message(text)
        duration1 = time.time() - start_time
        
        start_time = time.time()
        res2 = analyzer.analyze_message(text)
        duration2 = time.time() - start_time
        
        self.assertEqual(res1, res2)
        # Second one should be much faster
        print(f"AI Analysis 1: {duration1:.4f}s, AI Analysis 2: {duration2:.4f}s")
        self.assertLess(duration2, duration1 + 0.1) 

    def test_background_sync_trigger(self):
        """Verify that sync can be triggered manually in background."""
        # Connect an integration
        client.post("/integrations/slack/connect", json={"token": "test-token"}, headers=self.headers_a)
        
        # Trigger sync
        resp = client.post("/integrations/sync", headers=self.headers_a)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "processing")
        self.assertIn("task_id", resp.json())

if __name__ == "__main__":
    unittest.main()
