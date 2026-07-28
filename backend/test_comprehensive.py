import os
import sys
import time
import json
import unittest
import threading
import asyncio
import datetime

# Set environment variables for testing before importing app modules
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
os.environ["ENCRYPTION_KEY"] = "N0ZPaUZrRUZXSm5yYVpwUnVpYm9hckhLcm9LdER3SDA="
os.environ["ADMIN_PASSWORD"] = "admin123"
os.environ["JOHN_PASSWORD"] = "password"
os.environ["SARAH_PASSWORD"] = "sarah123"

from fastapi.testclient import TestClient
from main import app
from database import db
from auth.jwt_handler import create_access_token, create_refresh_token, decode_access_token, decode_refresh_token
from auth.models import get_user_by_username, verify_password, delete_user, get_tenant_by_id, add_user
from security import encrypt_secret, decrypt_secret, sanitize_pii
from worker import background_worker
from prioritizer import PriorityEngine
from ai_analyzer import AIAnalyzer, MockAIProvider
from scoring_service import ScoringService
from utils.cache import SimpleTTLCache
from utils.retries import retry_with_backoff, async_retry_with_backoff

client = TestClient(app)

class TestAuthRoutes(unittest.TestCase):
    def setUp(self):
        db.clear()
        # Restore users if deleted by other tests
        if not asyncio.run(get_user_by_username("admin")):
            from auth.models import pwd_context
            asyncio.run(add_user(
                username="admin", email="admin@acme.com", password="",
                hashed_password=pwd_context.hash("admin123"),
                tenant_id="t-acme", role="admin"
            ))

    def test_login_success(self):
        resp = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(data["token_type"], "bearer")

    def test_login_failure(self):
        resp = client.post("/auth/login", data={"username": "admin", "password": "wrong"})
        self.assertEqual(resp.status_code, 401)

    def test_refresh_token(self):
        # Login first
        resp = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
        refresh_token = resp.json()["refresh_token"]
        resp = client.post("/auth/refresh", json={"refresh_token": refresh_token})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    def test_refresh_token_invalid(self):
        resp = client.post("/auth/refresh", json={"refresh_token": "invalid.token.here"})
        self.assertEqual(resp.status_code, 401)

    def test_sso_login_disabled_by_default(self):
        # Secure default: without ENABLE_SIMULATED_SSO explicitly set to
        # "true", the endpoint must fail closed with 501 rather than acting
        # as an unauthenticated login bypass. This is the important
        # regression-prevention case for the SSO security fix.
        saved = os.environ.pop("ENABLE_SIMULATED_SSO", None)
        try:
            resp = client.post("/auth/sso/login", json={"email": "sarah@globex.com", "provider": "okta"})
            self.assertEqual(resp.status_code, 501)
        finally:
            if saved is not None:
                os.environ["ENABLE_SIMULATED_SSO"] = saved

    def test_sso_login_success(self):
        # Opted-in behavior: with ENABLE_SIMULATED_SSO="true", an existing
        # user's email should authenticate successfully.
        saved = os.environ.get("ENABLE_SIMULATED_SSO")
        os.environ["ENABLE_SIMULATED_SSO"] = "true"
        try:
            resp = client.post("/auth/sso/login", json={"email": "sarah@globex.com", "provider": "okta"})
            self.assertEqual(resp.status_code, 200)
            self.assertIn("access_token", resp.json())
        finally:
            if saved is None:
                os.environ.pop("ENABLE_SIMULATED_SSO", None)
            else:
                os.environ["ENABLE_SIMULATED_SSO"] = saved

    def test_sso_login_user_not_found(self):
        # Opted-in behavior: with ENABLE_SIMULATED_SSO="true", an unknown
        # email should 404.
        saved = os.environ.get("ENABLE_SIMULATED_SSO")
        os.environ["ENABLE_SIMULATED_SSO"] = "true"
        try:
            resp = client.post("/auth/sso/login", json={"email": "nobody@nowhere.com", "provider": "okta"})
            self.assertEqual(resp.status_code, 404)
        finally:
            if saved is None:
                os.environ.pop("ENABLE_SIMULATED_SSO", None)
            else:
                os.environ["ENABLE_SIMULATED_SSO"] = saved

class TestMainEndpoints(unittest.TestCase):
    def setUp(self):
        db.clear()
        self.token = create_access_token({"user_id": "u-2", "tenant_id": "t-acme", "role": "user"})
        self.headers = {"Authorization": f"Bearer {self.token}"}
        asyncio.run(db.add_item({"id": "item-1", "tenant_id": "t-acme", "text": "Test item", "source": "gmail"}))

    def test_root(self):
        resp = client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("running", resp.json()["message"].lower())

    def test_create_item(self):
        resp = client.post("/items", json={"text": "New task", "source": "manual"}, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["text"], "New task")
        self.assertEqual(data["source"], "manual")
        self.assertEqual(data["tenant_id"], "t-acme")

    def test_get_items(self):
        resp = client.get("/items", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "item-1")

    def test_get_priority_feed(self):
        resp = client.get("/priorities/feed", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        items = resp.json()
        self.assertTrue(len(items) >= 0)

    def test_get_priority_feed_with_tier_filter(self):
        resp = client.get("/priorities/feed?tier=urgent", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        for item in resp.json():
            self.assertEqual(item["priorityTier"], "urgent")

    def test_archive_item(self):
        resp = client.post("/items/item-1/archive", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("archived", resp.json()["message"])
        items = asyncio.run(db.get_items("t-acme"))
        archived_ids = {i["id"] for i in items if i.get("is_archived")}
        self.assertIn("item-1", archived_ids)

    def test_snooze_item(self):
        resp = client.post("/items/item-1/snooze", json={"hours": 2}, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("snoozed", resp.json()["message"])

    def test_unsnooze_item(self):
        client.post("/items/item-1/snooze", json={"hours": 2}, headers=self.headers)
        resp = client.post("/items/item-1/unsnooze", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("unsnoozed", resp.json()["message"])

    def test_get_stats(self):
        client.post("/items/item-1/archive", headers=self.headers)
        resp = client.get("/stats", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["archived_count"], 1)

    def test_list_integrations(self):
        resp = client.get("/integrations", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("available", data)
        self.assertIn("gmail", data["available"])

    def test_connect_integration(self):
        resp = client.post("/integrations/gmail/connect", json={"token": "gmail-token-123"}, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")
        stored_all = asyncio.run(db.get_connected_integrations("t-acme"))
        stored = stored_all["gmail"]
        self.assertNotEqual(stored["token"], "gmail-token-123")  # Should be encrypted

    def test_connect_integration_invalid_provider(self):
        resp = client.post("/integrations/unknown/connect", json={"token": "x"}, headers=self.headers)
        self.assertEqual(resp.status_code, 404)

    def test_trigger_sync(self):
        client.post("/integrations/gmail/connect", json={"token": "gmail-token-123"}, headers=self.headers)
        resp = client.post("/integrations/sync", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "processing")
        self.assertIn("task_id", resp.json())

    def test_unauthorized_access(self):
        resp = client.get("/items")
        self.assertEqual(resp.status_code, 401)

class TestPrivacyRoutes(unittest.TestCase):
    def setUp(self):
        db.clear()
        self.token = create_access_token({"user_id": "u-2", "tenant_id": "t-acme", "role": "user"})
        self.headers = {"Authorization": f"Bearer {self.token}"}
        asyncio.run(db.add_item({"id": "priv-1", "tenant_id": "t-acme", "text": "Private note", "source": "manual"}))

    def test_export_data(self):
        resp = client.get("/privacy/export", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["user"]["username"], "john")
        texts = [i["text"] for i in data["items"]]
        self.assertIn("Private note", texts)

    def test_delete_account(self):
        resp = client.delete("/privacy/account", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("deleted", resp.json()["message"].lower())
        # Verify data gone
        self.assertEqual(len(asyncio.run(db.get_items("t-acme"))), 0)

    def test_audit_logs(self):
        asyncio.run(db.add_audit_log("u-2", "TEST_ACTION", "Test details"))
        resp = client.get("/privacy/audit-logs", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        logs = resp.json()["logs"]
        self.assertTrue(any(l["action"] == "TEST_ACTION" for l in logs))

class TestDPDPRoutes(unittest.TestCase):
    def setUp(self):
        db.clear()
        self.token = create_access_token({"user_id": "u-2", "tenant_id": "t-acme", "role": "user"})
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_get_notice(self):
        resp = client.get("/dpdp/notice")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("version", resp.json())
        self.assertIn("rights", resp.json())

    def test_record_consent(self):
        resp = client.post("/dpdp/consent", json={"marketing_communications": True}, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("marketing_communications", data["updated_purposes"])
        self.assertEqual(data["current_preferences"]["marketing_communications"], True)

    def test_record_consent_missing_fields(self):
        resp = client.post("/dpdp/consent", json={"version": "1.0"}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)

    def test_get_consent_history(self):
        client.post("/dpdp/consent", json={"marketing_communications": True}, headers=self.headers)
        resp = client.get("/dpdp/consent", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        purposes = resp.json()["consent_purposes"]
        self.assertIn("marketing_communications", purposes)
        self.assertEqual(purposes["marketing_communications"]["enabled"], True)

    def test_nominate_person(self):
        resp = client.post("/dpdp/nominate", json={"name": "Jane Doe", "email": "jane@example.com", "relationship": "Spouse"}, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")

    def test_nominate_person_missing_fields(self):
        resp = client.post("/dpdp/nominate", json={"name": "Jane"}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)

    def test_get_nominee(self):
        client.post("/dpdp/nominate", json={"name": "Jane Doe", "email": "jane@example.com", "relationship": "Spouse"}, headers=self.headers)
        resp = client.get("/dpdp/nominee", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["nominee"]["name"], "Jane Doe")

    def test_log_grievance(self):
        resp = client.post("/dpdp/grievance", json={"subject": "Data issue", "description": "I cannot see my data"}, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")

    def test_log_grievance_missing_fields(self):
        resp = client.post("/dpdp/grievance", json={"subject": "Data issue"}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)

    def test_get_my_grievances(self):
        client.post("/dpdp/grievance", json={"subject": "Data issue", "description": "I cannot see my data"}, headers=self.headers)
        resp = client.get("/dpdp/grievances", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(len(resp.json()["grievances"]) > 0)

    def test_admin_get_all_grievances(self):
        admin_token = create_access_token({"user_id": "u-1", "tenant_id": "t-acme", "role": "admin"})
        resp = client.get("/dpdp/admin/grievances", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("grievances", resp.json())

    def test_admin_get_all_grievances_forbidden(self):
        resp = client.get("/dpdp/admin/grievances", headers=self.headers)
        self.assertEqual(resp.status_code, 403)

    def test_admin_resolve_grievance(self):
        admin_token = create_access_token({"user_id": "u-1", "tenant_id": "t-acme", "role": "admin"})
        client.post("/dpdp/grievance", json={"subject": "Data issue", "description": "I cannot see my data"}, headers=self.headers)
        grievance = asyncio.run(db.get_grievances("u-2"))[0]
        resp = client.post(f"/dpdp/admin/grievances/{grievance['id']}/resolve", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")

class TestPreferenceRoutes(unittest.TestCase):
    def setUp(self):
        db.clear()
        self.token = create_access_token({"user_id": "u-2", "tenant_id": "t-acme", "role": "user"})
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def test_get_contact_priorities_empty(self):
        resp = client.get("/preferences/contacts", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {})

    def test_set_contact_priority(self):
        resp = client.post("/preferences/contacts", json={"platform": "gmail", "handle": "boss@acme.com", "priority": "high"}, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")

    def test_set_contact_priority_invalid(self):
        resp = client.post("/preferences/contacts", json={"platform": "gmail", "handle": "boss@acme.com", "priority": "super-high"}, headers=self.headers)
        self.assertEqual(resp.status_code, 400)

    def test_delete_contact_priority(self):
        client.post("/preferences/contacts", json={"platform": "gmail", "handle": "boss@acme.com", "priority": "high"}, headers=self.headers)
        resp = client.delete("/preferences/contacts/gmail/boss@acme.com", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "success")
        self.assertEqual(asyncio.run(db.get_contact_priorities("t-acme")), {})

class TestAuthDependencies(unittest.TestCase):
    def setUp(self):
        db.clear()

    def test_get_admin_user(self):
        admin_token = create_access_token({"user_id": "u-1", "tenant_id": "t-acme", "role": "admin"})
        resp = client.get("/dpdp/admin/grievances", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(resp.status_code, 200)

    def test_get_admin_user_forbidden(self):
        user_token = create_access_token({"user_id": "u-2", "tenant_id": "t-acme", "role": "user"})
        resp = client.get("/dpdp/admin/grievances", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(resp.status_code, 403)

class TestJWTHandler(unittest.TestCase):
    def test_create_and_decode_access_token(self):
        token = create_access_token({"user_id": "u-1"})
        payload = decode_access_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], "u-1")
        self.assertEqual(payload["type"], "access")

    def test_create_and_decode_refresh_token(self):
        token = create_refresh_token({"user_id": "u-1"})
        payload = decode_refresh_token(token)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["user_id"], "u-1")
        self.assertEqual(payload["type"], "refresh")

    def test_decode_invalid_token(self):
        self.assertIsNone(decode_access_token("bad.token.here"))

    def test_decode_wrong_type(self):
        refresh = create_refresh_token({"user_id": "u-1"})
        self.assertIsNone(decode_access_token(refresh))
        access = create_access_token({"user_id": "u-1"})
        self.assertIsNone(decode_refresh_token(access))

class TestAuthModels(unittest.TestCase):
    def test_get_user_by_username(self):
        user = asyncio.run(get_user_by_username("admin"))
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "admin")

    def test_get_user_by_username_not_found(self):
        self.assertIsNone(asyncio.run(get_user_by_username("nobody")))

    def test_verify_password(self):
        user = asyncio.run(get_user_by_username("admin"))
        self.assertTrue(verify_password("admin123", user.hashed_password))
        self.assertFalse(verify_password("wrong", user.hashed_password))

    def test_delete_user(self):
        from auth.models import pwd_context
        created = asyncio.run(add_user(
            username="testuser", email="test@test.com", password="",
            hashed_password=pwd_context.hash("testpass"),
            tenant_id="t-acme", role="user"
        ))
        self.assertIsNotNone(asyncio.run(get_user_by_username("testuser")))
        asyncio.run(delete_user(created.id))
        self.assertIsNone(asyncio.run(get_user_by_username("testuser")))

    def test_get_tenant_by_id(self):
        tenant = asyncio.run(get_tenant_by_id("t-acme"))
        self.assertIsNotNone(tenant)
        self.assertEqual(tenant.name, "Acme Corp")

    def test_get_tenant_by_id_not_found(self):
        self.assertIsNone(asyncio.run(get_tenant_by_id("t-unknown")))

class TestDatabase(unittest.TestCase):
    def setUp(self):
        asyncio.run(db.clear())

    def test_add_and_get_items(self):
        asyncio.run(db.add_item({"id": "d1", "tenant_id": "t1", "text": "Hello", "source": "gmail"}))
        items = asyncio.run(db.get_items("t1"))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["text"], "Hello")

    def test_delete_tenant_data(self):
        asyncio.run(db.add_item({"id": "d1", "tenant_id": "t1", "text": "Hello", "source": "gmail"}))
        asyncio.run(db.delete_tenant_data("t1"))
        self.assertEqual(len(asyncio.run(db.get_items("t1"))), 0)

    def test_upsert_items(self):
        asyncio.run(db.upsert_items([
            {"id": "u1", "tenant_id": "t1", "text": "First", "source": "slack"},
            {"id": "u2", "tenant_id": "t1", "text": "Second", "source": "slack"}
        ]))
        self.assertEqual(len(asyncio.run(db.get_items("t1"))), 2)
        asyncio.run(db.upsert_items([
            {"id": "u1", "tenant_id": "t1", "text": "Updated", "source": "slack"}
        ]))
        items = asyncio.run(db.get_items("t1"))
        self.assertEqual(len(items), 2)
        texts = [i["text"] for i in items]
        self.assertIn("Updated", texts)

    def test_audit_logs(self):
        asyncio.run(db.add_audit_log("u-1", "ACTION", "details"))
        # get_audit_logs() filters by tenant_id (via that tenant's user ids) —
        # u-1 (admin) belongs to t-acme in the seed data.
        logs = asyncio.run(db.get_audit_logs("t-acme"))
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["action"], "ACTION")
        self.assertEqual(logs[0]["details"], "details")

    def test_all_audit_logs(self):
        # u-1 (admin) and u-2 (john) both belong to t-acme in the seed data
        asyncio.run(db.add_audit_log("u-1", "A1", "d1"))
        asyncio.run(db.add_audit_log("u-2", "A2", "d2"))
        logs = asyncio.run(db.get_audit_logs("t-acme"))
        self.assertEqual(len(logs), 2)

    def test_contact_priorities(self):
        asyncio.run(db.set_contact_priority("t1", "gmail", "boss@acme.com", "high"))
        self.assertEqual(asyncio.run(db.get_contact_priorities("t1"))["gmail"]["boss@acme.com"], "high")
        asyncio.run(db.delete_contact_priority("t1", "gmail", "boss@acme.com"))
        self.assertEqual(asyncio.run(db.get_contact_priorities("t1")), {})

    def test_consent(self):
        asyncio.run(db.record_consent("u-1", {"version": "1.0", "purpose": "test"}))
        consents = asyncio.run(db.get_consents("u-1"))
        self.assertEqual(len(consents), 1)
        self.assertEqual(consents[0]["version"], "1.0")

    def test_nominee(self):
        asyncio.run(db.set_nominee("u-1", {"name": "Jane", "email": "jane@example.com", "relationship": "Spouse"}))
        nominee = asyncio.run(db.get_nominee("u-1"))
        self.assertEqual(nominee["name"], "Jane")

    def test_grievance(self):
        asyncio.run(db.add_grievance({"user_id": "u-1", "tenant_id": "t-acme", "subject": "S", "description": "D", "status": "open"}))
        grievances = asyncio.run(db.get_grievances("u-1"))
        self.assertEqual(len(grievances), 1)
        all_grievances = asyncio.run(db.get_grievances())
        self.assertEqual(len(all_grievances), 1)

    def test_enforce_retention_policy(self):
        old_item = {"id": "old", "tenant_id": "t1", "text": "Old", "source": "gmail", "timestamp": time.time() - (40 * 24 * 60 * 60)}
        new_item = {"id": "new", "tenant_id": "t1", "text": "New", "source": "gmail", "timestamp": time.time()}
        asyncio.run(db.add_item(old_item))
        asyncio.run(db.add_item(new_item))
        deleted = asyncio.run(db.enforce_retention_policy(days=30))
        self.assertEqual(deleted, 1)
        self.assertEqual(len(asyncio.run(db.get_items("t1"))), 1)

class TestSecurity(unittest.TestCase):
    def test_encrypt_decrypt(self):
        secret = "my-secret"
        encrypted = encrypt_secret(secret)
        self.assertNotEqual(encrypted, secret)
        self.assertEqual(decrypt_secret(encrypted), secret)

    def test_encrypt_empty(self):
        self.assertEqual(encrypt_secret(""), "")
        self.assertEqual(decrypt_secret(""), "")

    def test_decrypt_plaintext(self):
        # If decryption fails, should return as-is
        self.assertEqual(decrypt_secret("not-encrypted"), "not-encrypted")

    def test_sanitize_pii_empty(self):
        self.assertEqual(sanitize_pii(""), "")
        self.assertEqual(sanitize_pii(None), "")

class TestPrioritizer(unittest.TestCase):
    def test_deadline_factor_none(self):
        engine = PriorityEngine()
        self.assertEqual(engine.calculate_deadline_factor(None), 0.0)

    def test_deadline_factor_overdue(self):
        engine = PriorityEngine()
        past = "2020-01-01T00:00:00"
        self.assertEqual(engine.calculate_deadline_factor(past), 1.0)

    def test_deadline_factor_future(self):
        engine = PriorityEngine()
        future = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()
        factor = engine.calculate_deadline_factor(future)
        self.assertTrue(0.0 < factor < 1.0)

    def test_deadline_factor_invalid_string(self):
        engine = PriorityEngine()
        self.assertEqual(engine.calculate_deadline_factor("not-a-date"), 0.0)

    def test_deadline_factor_utc_z(self):
        engine = PriorityEngine()
        future = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).isoformat().replace("+00:00", "Z")
        factor = engine.calculate_deadline_factor(future)
        self.assertTrue(0.0 <= factor <= 1.0)

    def test_score_calculation(self):
        engine = PriorityEngine()
        # With default weights (urgency 0.3, importance 0.3, sender_rank 0.2,
        # deadline 0.2, summing to 1.0) and no deadline supplied, the
        # deadline factor is legitimately 0.0 (see calculate_deadline_factor
        # for deadline=None), so a fully-maxed urgency/importance/sender_rank
        # can only reach 0.8, not 1.0. Confirmed against test_custom_weights
        # below, which uses an explicit deadline weight of 0.0 and correctly
        # expects the un-scaled 0.5. The formula in prioritizer.py is
        # correct and intentional; this test's expected value was stale.
        score = engine.score(urgency=1.0, importance=1.0, sender_rank=1.0)
        self.assertEqual(score, 0.8)

    def test_custom_weights(self):
        engine = PriorityEngine(weights={"urgency": 1.0, "importance": 0.0, "sender_rank": 0.0, "deadline": 0.0})
        score = engine.score(urgency=0.5, importance=0.0, sender_rank=0.0)
        self.assertEqual(score, 0.5)

class TestAIAnalyzer(unittest.TestCase):
    def test_analyze_message_empty(self):
        analyzer = AIAnalyzer(provider=MockAIProvider())
        result = analyzer.analyze_message("")
        self.assertEqual(result["urgency"], 0.0)
        self.assertEqual(result["importance"], 0.0)

    def test_analyze_message_caching(self):
        analyzer = AIAnalyzer(provider=MockAIProvider())
        text = "Urgent: server down ASAP"
        r1 = analyzer.analyze_message(text)
        r2 = analyzer.analyze_message(text)
        self.assertEqual(r1, r2)

class TestScoringService(unittest.TestCase):
    def setUp(self):
        self.engine = PriorityEngine()
        self.analyzer = AIAnalyzer(provider=MockAIProvider())
        self.service = ScoringService(self.engine, self.analyzer)

    def test_process_items_empty(self):
        result = asyncio.run(self.service.process_items("t-acme", [], set(), {}))
        self.assertEqual(result, [])

    def test_archived_filtering(self):
        items = [{"id": "a1", "text": "test", "source": "gmail"}]
        result = asyncio.run(self.service.process_items("t-acme", items, {"a1"}, {}))
        self.assertEqual(len(result), 0)

    def test_snoozed_filtering(self):
        items = [{"id": "s1", "text": "test", "source": "gmail"}]
        snoozed = {"s1": datetime.datetime.now() + datetime.timedelta(hours=1)}
        result = asyncio.run(self.service.process_items("t-acme", items, set(), snoozed))
        self.assertEqual(len(result), 0)

    def test_source_signals_jira_highest(self):
        items = [{"id": "j1", "text": "Bug", "source": "Jira", "metadata": {"priority": "highest", "issue_type": "bug"}}]
        result = asyncio.run(self.service.process_items("t-acme", items, set(), {}))
        self.assertEqual(len(result), 1)
        self.assertIn("Highest Jira priority override", result[0]["explanation"])

    def test_source_signals_slack_dm(self):
        items = [{"id": "s1", "text": "Hey", "source": "Slack", "metadata": {"message_type": "dm"}}]
        result = asyncio.run(self.service.process_items("t-acme", items, set(), {}))
        self.assertIn("Direct Message", result[0]["explanation"])

    def test_contact_priority_high(self):
        items = [{"id": "c1", "text": "Hello", "source": "gmail", "sender": {"handle": "boss@acme.com"}}]
        contacts = {"gmail": {"boss@acme.com": "high"}}
        result = asyncio.run(self.service.process_items("t-acme", items, set(), {}, contacts))
        self.assertIn("High priority contact", result[0]["explanation"])

    def test_contact_priority_low(self):
        items = [{"id": "c1", "text": "Hello", "source": "gmail", "sender": {"handle": "spam@ads.com"}}]
        contacts = {"gmail": {"spam@ads.com": "low"}}
        result = asyncio.run(self.service.process_items("t-acme", items, set(), {}, contacts))
        self.assertIn("Low priority contact", result[0]["explanation"])

    def test_tier_boundaries(self):
        # Test tier classification
        self.assertEqual(self.service._get_tier(85), "urgent")
        self.assertEqual(self.service._get_tier(70), "high")
        self.assertEqual(self.service._get_tier(45), "medium")
        self.assertEqual(self.service._get_tier(10), "low")

class TestCache(unittest.TestCase):
    def test_ttl_cache(self):
        cache = SimpleTTLCache(ttl_seconds=0.1)
        cache.set("key", "value")
        self.assertEqual(cache.get("key"), "value")
        time.sleep(0.15)
        self.assertIsNone(cache.get("key"))

    def test_ttl_cache_delete(self):
        cache = SimpleTTLCache()
        cache.set("key", "value")
        cache.delete("key")
        self.assertIsNone(cache.get("key"))

class TestRetries(unittest.TestCase):
    def test_retry_with_backoff_success(self):
        call_count = [0]
        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("fail")
            return "success"
        result = flaky()
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 3)

    def test_retry_with_backoff_max_retries(self):
        call_count = [0]
        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def always_fail():
            call_count[0] += 1
            raise ValueError("fail")
        with self.assertRaises(ValueError):
            always_fail()
        self.assertEqual(call_count[0], 2)

    def test_async_retry_with_backoff_success(self):
        import asyncio
        call_count = [0]
        @async_retry_with_backoff(max_retries=3, base_delay=0.01)
        async def async_flaky():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("fail")
            return "success"
        result = asyncio.run(async_flaky())
        self.assertEqual(result, "success")
        self.assertEqual(call_count[0], 3)

    def test_async_retry_with_backoff_max_retries(self):
        import asyncio
        call_count = [0]
        @async_retry_with_backoff(max_retries=2, base_delay=0.01)
        async def async_always_fail():
            call_count[0] += 1
            raise ValueError("fail")
        with self.assertRaises(ValueError):
            asyncio.run(async_always_fail())
        self.assertEqual(call_count[0], 2)

class TestWorker(unittest.TestCase):
    def test_enqueue_and_status(self):
        def simple_task():
            return "done"
        task_id = background_worker.enqueue(simple_task)
        self.assertIsNotNone(task_id)
        # Wait a bit for execution
        time.sleep(0.2)
        self.assertEqual(background_worker.get_status(task_id), "completed")
        self.assertEqual(background_worker.get_result(task_id), "done")

    def test_enqueue_error(self):
        def bad_task():
            raise ValueError("boom")
        task_id = background_worker.enqueue(bad_task)
        time.sleep(0.2)
        self.assertEqual(background_worker.get_status(task_id), "failed")
        self.assertIn("boom", background_worker.get_error(task_id))

    def test_get_status_unknown(self):
        self.assertEqual(background_worker.get_status("unknown-id"), "unknown")

import atexit

def _stop_worker():
    try:
        background_worker.stop()
    except Exception:
        pass

atexit.register(_stop_worker)

if __name__ == "__main__":
    try:
        unittest.main()
    finally:
        _stop_worker()
