import unittest
import json
import os
import time
import asyncio

# Set environment variables for testing before importing app modules
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
os.environ["ENCRYPTION_KEY"] = "N0ZPaUZrRUZXSm5yYVpwUnVpYm9hckhLcm9LdER3SDA="
os.environ["ADMIN_PASSWORD"] = "admin123"
os.environ["JOHN_PASSWORD"] = "password"
os.environ["SARAH_PASSWORD"] = "sarah123"

from main import app
from auth_routes import limiter as auth_limiter

from database import db
from auth.jwt_handler import create_access_token
from fastapi.testclient import TestClient
from security import encrypt_secret, decrypt_secret, sanitize_pii

client = TestClient(app)
app.state.limiter.enabled = False
auth_limiter.enabled = False

class TestSecurity(unittest.TestCase):
    def setUp(self):
        # Clear mock DB
        db.clear()

        # Create a test item for Tenant A (u-2/t-acme)
        self.token_a = create_access_token({"sub": "john", "user_id": "u-2", "tenant_id": "t-acme"})
        self.headers_a = {"Authorization": f"Bearer {self.token_a}"}
        
        # Use existing items retrieval logic as /items POST might not exist in the current API
        # Actually, let's see if /items POST exists. 
        # Looking at main.py earlier, I didn't see a POST /items.
        # But for testing, we can inject into db directly.
        db.add_item({
            "id": "item-a",
            "tenant_id": "t-acme",
            "text": "Secret item for A",
            "content": "Secret content for A"
        })
        self.item_a = {"id": "item-a"}
        
        db.add_item({
            "id": "item-b",
            "tenant_id": "t-globex",
            "text": "Secret item for B",
            "content": "Secret content for B"
        })
        self.item_b = {"id": "item-b"}

    def test_secret_encryption(self):
        """Verify that integration tokens are encrypted in 'storage'."""
        provider = "slack"
        raw_token = "xoxp-secret-token"
        
        # Connect integration
        resp = client.post(f"/integrations/{provider}/connect", 
                          json={"token": raw_token}, 
                          headers=self.headers_a)
        self.assertEqual(resp.status_code, 200)
        
        # Check 'database' (connected_integrations)
        stored_data = asyncio.run(db.get_connected_integrations("t-acme"))[provider]
        stored_token = stored_data["token"]
        
        # It should be encrypted (not equal to raw)
        self.assertNotEqual(stored_token, raw_token)
        
        # Decrypting it should return raw token
        self.assertEqual(decrypt_secret(stored_token), raw_token)

    def test_pii_sanitization(self):
        """Verify that PII is sanitized."""
        input_text = "Contact me at john.doe@example.com or 555-123-4567. My SSN is 123-45-6789."
        sanitized = sanitize_pii(input_text)
        
        self.assertNotIn("john.doe@example.com", sanitized)
        self.assertNotIn("555-123-4567", sanitized)
        self.assertNotIn("123-45-6789", sanitized)
        self.assertIn("[EMAIL_REDACTED]", sanitized)
        self.assertIn("[PHONE_REDACTED]", sanitized)
        self.assertIn("[SSN_REDACTED]", sanitized)

    def test_cross_tenant_item_access_prevention(self):
        """
        Audit: Ensure a user cannot archive an item belonging to another tenant.
        """
        item_id_b = self.item_b["id"]
        
        # Tenant A tries to archive Tenant B's item
        resp = client.post(f"/items/{item_id_b}/archive", headers=self.headers_a)
        
        # Should be 403 Forbidden
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "Not authorized to access this item")
        
    def test_tenant_isolation_in_feed(self):
        """Verify that Tenant A cannot see Tenant B's items in the feed."""
        resp = client.get("/priorities/feed", headers=self.headers_a)
        items = resp.json()
        
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["text"], "Secret item for A")
        
        for item in items:
            self.assertNotEqual(item["text"], "Secret item for B")

    def test_brute_force_lockout(self):
        """Verify that account is locked after MAX_LOGIN_ATTEMPTS failed attempts."""
        username = "john"
        password = "wrong-password"
        
        # 1-4 failed attempts: 401 Unauthorized
        for _ in range(4):
            resp = client.post("/auth/login", data={"username": username, "password": password})
            self.assertEqual(resp.status_code, 401)
            
        # 5th failed attempt: 401 Unauthorized (this attempt triggers the lockout)
        resp = client.post("/auth/login", data={"username": username, "password": password})
        self.assertEqual(resp.status_code, 401)
        
        # 6th attempt: 403 Forbidden (locked)
        resp = client.post("/auth/login", data={"username": username, "password": password})
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Account temporarily locked", resp.json()["detail"])
        
        # Verify it's locked even with CORRECT password
        resp = client.post("/auth/login", data={"username": username, "password": "password"})
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Account temporarily locked", resp.json()["detail"])

    def test_successful_login_clears_failed_attempts(self):
        """Verify that a successful login resets the failed attempts counter."""
        username = "john"
        
        # 3 failed attempts
        for _ in range(3):
            client.post("/auth/login", data={"username": username, "password": "wrong-password"})
        
        self.assertEqual(asyncio.run(db.count_recent_failed_logins("u-2", 0)), 3)

        # 1 successful login
        resp = client.post("/auth/login", data={"username": username, "password": "password"})
        self.assertEqual(resp.status_code, 200)

        # Failed attempts should be cleared
        self.assertEqual(asyncio.run(db.count_recent_failed_logins("u-2", 0)), 0)

    def test_admin_can_unlock_user(self):
        """Verify that an admin can manually unlock a locked account."""
        # 1. Lock John's account
        asyncio.run(db.lock_account("u-2", time.time() + 1000))
        
        # 2. Verify it's locked
        resp = client.post("/auth/login", data={"username": "john", "password": "password"})
        self.assertEqual(resp.status_code, 403)
        
        # 3. Admin unlocks John
        # Need admin token
        admin_token = create_access_token(data={"sub": "admin", "user_id": "u-1", "tenant_id": "t-acme", "role": "admin"})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        resp = client.post("/auth/admin/unlock/u-2", headers=admin_headers)
        self.assertEqual(resp.status_code, 200)
        
        # 4. Verify John can now login
        resp = client.post("/auth/login", data={"username": "john", "password": "password"})
        self.assertEqual(resp.status_code, 200)

if __name__ == "__main__":
    unittest.main()
