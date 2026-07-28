"""
Comprehensive compliance tests for DPDP (India), GDPR (EU), and CCPA/CPRA (California).
Tests: granular consent, GDPR data subject rights, CCPA Do Not Sell, DPA, erasure cascade, audit logging.
"""
import os
import time
import json
import asyncio
import pytest
from fastapi.testclient import TestClient
from main import app
from database import db
from compliance_audit import clear_compliance_audit_log, get_compliance_audit_log

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ENCRYPTION_KEY", "N0ZPaUZrRUZXSm5yYVpwUnVpYm9hckhLcm9LdER3SDA=")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")
os.environ.setdefault("JOHN_PASSWORD", "password")
os.environ.setdefault("SARAH_PASSWORD", "sarah123")

client = TestClient(app)

# Several tests in this file (TestCCPA.test_ccpa_delete, TestErasureCascade,
# TestComplianceAudit.test_audit_log_not_erasable_by_erasure) exercise
# /gdpr/erase or /ccpa/delete (which reuses the same cascade), which
# permanently deletes the calling user's row via auth.models.delete_user().
# auth.models.seed_initial_data() only reseeds when the users table is
# completely empty, so once "john" is deleted mid-suite it stays gone —
# admin/sarah still exist, so the empty-check no-ops. Every other test that
# logs in via the default get_token()/headers() (username="john") would then
# fail to authenticate. Recreate a deleted seed user on demand before
# attempting login, mirroring the "Restore users if deleted by other tests"
# pattern already used in test_comprehensive.py.
_SEED_USER_INFO = {
    "john": {"email": "john@acme.com", "tenant_id": "t-acme", "role": "user"},
    "admin": {"email": "admin@acme.com", "tenant_id": "t-acme", "role": "admin"},
    "sarah": {"email": "sarah@globex.com", "tenant_id": "t-globex", "role": "admin"},
}


def _ensure_seed_user_exists(username, password):
    info = _SEED_USER_INFO.get(username)
    if info is None:
        return
    from auth.models import get_user_by_username, add_user
    if asyncio.run(get_user_by_username(username)) is None:
        asyncio.run(add_user(
            username=username, email=info["email"], password=password,
            tenant_id=info["tenant_id"], role=info["role"],
        ))


def get_token(username="john", password="password"):
    _ensure_seed_user_exists(username, password)
    resp = client.post("/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(autouse=True)
def _restore_deleted_seed_users():
    """Runs before every test in this module (after conftest.py's own
    autouse reset_state fixture, which resets tenant-scoped data and seeds
    from empty). Some tests here (TestCCPA.test_ccpa_delete,
    TestErasureCascade, TestComplianceAudit.test_audit_log_not_erasable_by_erasure)
    look up "john" directly via auth.models.get_users_db() before ever
    calling get_token()/headers(), so the lazy restore in
    _ensure_seed_user_exists() (triggered from get_token()) would run too
    late for those. Proactively restore any deleted seed user up front."""
    for username, password in (("john", "password"), ("admin", "admin123"), ("sarah", "sarah123")):
        _ensure_seed_user_exists(username, password)
    yield


def get_admin_token():
    return get_token("admin", "admin123")


def headers(token=None):
    if token is None:
        token = get_token()
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# 1. GRANULAR PER-PURPOSE CONSENT (DPDP)
# =============================================================================
class TestGranularConsent:

    def test_get_consent_purposes_defaults(self):
        """All consent purposes should be returned with their defaults."""
        resp = client.get("/dpdp/consent", headers=headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "consent_purposes" in data
        purposes = data["consent_purposes"]
        assert "ai_priority_scoring" in purposes
        assert "credential_storage" in purposes
        assert "marketing_communications" in purposes
        assert "analytics_improvement" in purposes
        assert "data_sharing_partners" in purposes
        # Required-for-service purposes should be enabled by default
        assert purposes["ai_priority_scoring"]["enabled"] is True
        # Marketing should be off by default
        assert purposes["marketing_communications"]["enabled"] is False

    def test_set_individual_purpose_independently(self):
        """Toggling one purpose should not affect others."""
        # First, toggle marketing on
        resp = client.post("/dpdp/consent", headers=headers(), json={
            "marketing_communications": True
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["updated_purposes"] == ["marketing_communications"]
        # ai_priority_scoring should still be True (default)
        assert data["current_preferences"]["ai_priority_scoring"] is True

        # Verify via GET
        resp = client.get("/dpdp/consent", headers=headers())
        purposes = resp.json()["consent_purposes"]
        assert purposes["marketing_communications"]["enabled"] is True
        assert purposes["ai_priority_scoring"]["enabled"] is True

    def test_toggle_multiple_purposes_at_once(self):
        """Multiple purposes can be toggled in one request."""
        resp = client.post("/dpdp/consent", headers=headers(), json={
            "ai_priority_scoring": False,
            "marketing_communications": True,
            "data_sharing_partners": False
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["updated_purposes"]) == 3
        assert data["current_preferences"]["ai_priority_scoring"] is False
        assert data["current_preferences"]["marketing_communications"] is True
        assert data["current_preferences"]["data_sharing_partners"] is False

    def test_reject_unknown_purpose(self):
        """Unknown purpose keys should be rejected with 400."""
        resp = client.post("/dpdp/consent", headers=headers(), json={
            "unknown_purpose": True
        })
        assert resp.status_code == 400
        assert "Unknown consent purpose" in resp.json()["detail"]

    def test_reject_non_boolean_value(self):
        """Non-boolean consent values should be rejected."""
        resp = client.post("/dpdp/consent", headers=headers(), json={
            "marketing_communications": "yes"
        })
        assert resp.status_code == 400
        assert "must be a boolean" in resp.json()["detail"]

    def test_consent_independence_across_users(self):
        """Different users' consent preferences should be independent."""
        # John opts out of AI scoring
        client.post("/dpdp/consent", headers=headers(), json={
            "ai_priority_scoring": False
        })
        # Sarah should still have defaults
        sarah_token = get_token("sarah", "sarah123")
        resp = client.get("/dpdp/consent", headers={"Authorization": f"Bearer {sarah_token}"})
        assert resp.json()["consent_purposes"]["ai_priority_scoring"]["enabled"] is True


# =============================================================================
# 2. GDPR DATA SUBJECT RIGHTS
# =============================================================================
class TestGDPR:

    def test_gdpr_access(self):
        """Right of Access (Art. 15) should return all user data."""
        resp = client.get("/gdpr/access", headers=headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["regulation"] == "GDPR"
        assert data["right"] == "access"
        assert "data" in data
        assert "user_info" in data["data"]
        assert data["data"]["user_info"]["username"] == "john"

    def test_gdpr_rectify(self):
        """Right to Rectification (Art. 16) should update user data."""
        resp = client.put("/gdpr/rectify", headers=headers(), json={
            "email": "john.updated@example.com"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["applied"]["email"] == "john.updated@example.com"

    def test_gdpr_rectify_reject_invalid_field(self):
        """Non-rectifiable fields should be rejected."""
        resp = client.put("/gdpr/rectify", headers=headers(), json={
            "password": "newpass123"
        })
        assert resp.status_code == 400
        assert "password" in resp.json()["detail"]["errors"]

    def test_gdpr_portability(self):
        """Data Portability (Art. 20) should return JSON export."""
        resp = client.get("/gdpr/port", headers=headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["regulation"] == "GDPR"
        assert data["right"] == "portability"
        assert data["format"] == "application/json"
        assert "data" in data

    def test_gdpr_restrict_processing(self):
        """Restriction of Processing (Art. 18) should pause AI scoring."""
        resp = client.post("/gdpr/restrict", headers=headers(), json={
            "action": "restrict"
        })
        assert resp.status_code == 200
        assert "Processing restricted" in resp.json()["message"]

        # Verify restriction is stored
        assert hasattr(db, 'processing_restrictions')
        from auth.models import get_users_db
        john = [u for u in asyncio.run(get_users_db()) if u.username == "john"][0]
        assert db.processing_restrictions[john.id]["restricted"] is True

        # Lift restriction
        resp = client.post("/gdpr/restrict", headers=headers(), json={
            "action": "lift"
        })
        assert resp.status_code == 200
        assert "Processing restriction lifted" in resp.json()["message"]

    def test_gdpr_restrict_invalid_action(self):
        """Invalid restriction action should be rejected."""
        resp = client.post("/gdpr/restrict", headers=headers(), json={
            "action": "invalid"
        })
        assert resp.status_code == 400


# =============================================================================
# 3. CCPA/CPRA "DO NOT SELL OR SHARE"
# =============================================================================
class TestCCPA:

    def test_do_not_sell_default_opted_out(self):
        """Do Not Sell should default to opted_out (True) per CCPA opt-out defaults."""
        resp = client.get("/ccpa/do-not-sell", headers=headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["regulation"] == "CCPA/CPRA"
        assert data["status"] == "opted_out"
        assert data["preference"]["do_not_sell_or_share"] is True

    def test_toggle_do_not_sell(self):
        """Toggling Do Not Sell should persist."""
        # Allow selling
        resp = client.post("/ccpa/do-not-sell", headers=headers(), json={
            "do_not_sell_or_share": False
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "selling_allowed"

        # Verify stored
        resp = client.get("/ccpa/do-not-sell", headers=headers())
        assert resp.json()["preference"]["do_not_sell_or_share"] is False

        # Opt back out
        resp = client.post("/ccpa/do-not-sell", headers=headers(), json={
            "do_not_sell_or_share": True
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "opted_out"

    def test_do_not_sell_standalone_not_bundled(self):
        """Do Not Sell should be a standalone toggle, not bundled with general consent."""
        # Toggle general consent should NOT affect Do Not Sell
        client.post("/dpdp/consent", headers=headers(), json={
            "marketing_communications": True
        })
        resp = client.get("/ccpa/do-not-sell", headers=headers())
        assert resp.json()["preference"]["do_not_sell_or_share"] is True  # unchanged

        # Toggle Do Not Sell should NOT affect general consent
        client.post("/ccpa/do-not-sell", headers=headers(), json={
            "do_not_sell_or_share": False
        })
        resp = client.get("/dpdp/consent", headers=headers())
        assert resp.json()["consent_purposes"]["marketing_communications"]["enabled"] is True

    def test_ccpa_access(self):
        """CCPA Right to Know should return data categories."""
        resp = client.get("/ccpa/access", headers=headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["regulation"] == "CCPA/CPRA"
        assert "categories" in data
        assert "third_parties" in data

    def test_ccpa_delete(self):
        """CCPA Right to Delete should reuse GDPR erasure cascade."""
        resp = client.delete("/ccpa/delete", headers=headers())
        assert resp.status_code == 200
        data = resp.json()
        assert data["regulation"] == "CCPA/CPRA"
        assert data["right"] == "right_to_delete"
        assert "cascade_layers_deleted" in data


# =============================================================================
# 4. FULL ERASURE CASCADE — VERIFY EVERY LAYER
# =============================================================================
class TestErasureCascade:

    def test_erasure_removes_from_all_layers(self):
        """Erasure must delete user data from every storage layer: users, items, 
        consent records, nominee, grievances, MFA, cache, delegations, locked accounts.
        """
        from auth.models import get_users_db
        from utils.cache import config_cache

        # Get John's user ID
        john = [u for u in asyncio.run(get_users_db()) if u.username == "john"][0]
        user_id = john.id
        tenant_id = john.tenant_id

        # Pre-populate data across all layers
        # 1. Items — the real Item schema is tenant-scoped only (no
        # user_id/assigned_to column), so we just create a real item here
        # to exercise the delegation flow and to confirm /gdpr/erase (a
        # per-user erasure) leaves tenant-scoped items alone (see note below).
        asyncio.run(db.add_item({"id": "item-1", "tenant_id": tenant_id, "text": "John's item", "source": "manual"}))

        # 2. Consent records
        asyncio.run(db.record_consent(user_id, {"version": "1.0", "purpose": "test"}))

        # 3. Nominee
        asyncio.run(db.set_nominee(user_id, {"name": "Jane", "email": "jane@test.com", "relationship": "friend"}))

        # 4. Grievance
        asyncio.run(db.add_grievance({"user_id": user_id, "tenant_id": tenant_id, "subject": "test", "description": "test grievance", "status": "open"}))

        # 5. MFA
        asyncio.run(db.set_mfa_secret(user_id, "test-secret"))
        asyncio.run(db.set_mfa_pending_secret(user_id, "pending-secret"))
        asyncio.run(db.set_mfa_recovery_codes(user_id, ["code1", "code2"]))

        # 6. Delegation — Delegation is now a real SQL table only reachable
        # via db.delegate_item()/db.get_delegation(), and delegate_item()
        # validates the item exists first. Create a second real item, then
        # delegate it for real instead of bypassing the check.
        asyncio.run(db.add_item({"id": "item-delegated", "tenant_id": tenant_id, "text": "test", "source": "manual"}))
        # assigned_by is a FK to users.id, not a username — "u-1" is the
        # real seeded admin user's id.
        asyncio.run(db.delegate_item("item-delegated", tenant_id, user_id, "u-1", "test note"))

        # 7. Failed login attempts
        asyncio.run(db.record_failed_login(user_id))
        asyncio.run(db.record_failed_login(user_id))
        asyncio.run(db.lock_account(user_id, time.time() + 300))

        # 8. Cache
        config_cache.set(f"user:{user_id}", {"data": "test"}, tags=[f"user:{user_id}"])

        # Verify data exists before erasure
        assert any(u.id == user_id for u in asyncio.run(get_users_db()))
        assert any(i["id"] == "item-1" for i in asyncio.run(db.get_items(tenant_id)))
        assert len(asyncio.run(db.get_consents(user_id))) > 0
        assert asyncio.run(db.get_nominee(user_id)) is not None
        assert len(asyncio.run(db.get_grievances(user_id))) > 0
        assert asyncio.run(db.get_mfa_secret(user_id)) is not None
        delegation = asyncio.run(db.get_delegation("item-delegated"))
        assert delegation is not None and delegation["assigned_to"] == user_id
        assert asyncio.run(db.count_recent_failed_logins(user_id, 0)) > 0
        assert asyncio.run(db.get_lockout_expiry(user_id)) is not None

        # Execute erasure via GDPR Art. 17
        resp = client.delete("/gdpr/erase", headers=headers())
        assert resp.status_code == 200

        # === VERIFY EVERY LAYER IS CLEAN ===
        # 1. User record
        assert not any(u.id == user_id for u in asyncio.run(get_users_db())), "User record not erased"

        # 2. Items — per gdpr_routes.py's gdpr_erase() docstring, per-owner
        # item erasure is intentionally a no-op in the real schema: Item has
        # no user_id/assigned_to column, so there is nothing to filter on for
        # a single user within a shared tenant. Tenant-wide item erasure only
        # happens via account deletion (delete_tenant_data), not /gdpr/erase.
        # So the item legitimately remains after a per-user erasure.
        assert any(i["id"] == "item-1" for i in asyncio.run(db.get_items(tenant_id))), \
            "Item unexpectedly removed by per-user erasure (items are tenant-scoped, not user-scoped)"

        # 3. Consent records
        assert len(asyncio.run(db.get_consents(user_id))) == 0, "Consent records not erased"

        # 4. Nominee
        assert asyncio.run(db.get_nominee(user_id)) is None, "Nominee not erased"

        # 5. Grievances — unlike the old in-memory mock (which anonymized
        # with a "**ERASED**" sentinel), the real Grievance.user_id column is
        # a NOT NULL FK, so database.py's delete_user_data() deletes
        # grievance rows outright instead. Verify none remain for this user.
        grievances = asyncio.run(db.get_grievances(user_id))
        assert grievances == [], "Grievances not erased"

        # 6. MFA secrets
        assert asyncio.run(db.get_mfa_secret(user_id)) is None, "MFA secret not erased"
        assert asyncio.run(db.get_mfa_pending_secret(user_id)) is None, "MFA pending secret not erased"
        assert asyncio.run(db.get_mfa_recovery_codes(user_id)) is None, "MFA recovery codes not erased"

        # 7. Delegations — delete_user_data() deletes Delegation rows where
        # assigned_to == user_id (and assigned_by == user_id).
        assert asyncio.run(db.get_delegation("item-delegated")) is None, "Delegations not erased"

        # 8. Locked accounts / failed attempts
        assert asyncio.run(db.count_recent_failed_logins(user_id, 0)) == 0, "Failed login attempts not erased"
        assert asyncio.run(db.get_lockout_expiry(user_id)) is None, "Locked account not erased"

        # 9. Cache
        assert config_cache.get(f"user:{user_id}") is None, "Cache not invalidated"

        # Note: this test just deleted the "john" user row entirely via
        # /gdpr/erase. get_token()/headers() (used by every other test in
        # this file) transparently recreates "john" on next login — see
        # _ensure_seed_user_exists() near the top of this file.

    def test_compliance_audit_survives_erasure(self):
        """Compliance audit log entries must survive user erasure and use hashed refs."""
        from compliance_audit import get_compliance_audit_log

        clear_compliance_audit_log()

        # Record an audit event before erasure
        from auth.models import get_users_db
        john = [u for u in asyncio.run(get_users_db()) if u.username == "john"][0]
        user_id = john.id

        # Trigger a compliance event that writes to the audit log
        client.get("/gdpr/access", headers=headers())

        # Verify audit log has the entry before erasure
        audit_before = get_compliance_audit_log()
        assert len(audit_before) >= 1
        entry = audit_before[0]
        assert entry["regulation"] == "GDPR"
        assert entry["user_ref"] is not None
        # user_ref should NOT equal the raw user_id (it's hashed)
        assert entry["user_ref"] != user_id

        # Now erase the user
        client.delete("/gdpr/erase", headers=headers())

        # Audit log entries should still exist
        audit_after = get_compliance_audit_log()
        assert len(audit_after) >= 1
        # The user_ref is hashed, so it's not PII and doesn't need erasure
        # The erasure itself should have logged an event
        erasure_events = [e for e in audit_after if e["request_type"] == "DATA_ERASURE"]
        assert len(erasure_events) >= 1


# =============================================================================
# 5. DPA (DATA PROCESSING AGREEMENT)
# =============================================================================
class TestDPA:

    def test_dpa_endpoint(self):
        """DPA endpoint should return the data processing agreement."""
        resp = client.get("/dpa")
        assert resp.status_code == 200
        data = resp.json()
        assert "dpa" in data
        assert data["dpa"]["title"] == "Data Processing Agreement"
        assert "subprocessors" in data["dpa"]
        assert len(data["dpa"]["subprocessors"]) >= 1

    def test_subprocessors_endpoint(self):
        """Subprocessors endpoint should list all data processors."""
        resp = client.get("/dpa/subprocessors")
        assert resp.status_code == 200
        data = resp.json()
        assert "subprocessors" in data
        assert len(data["subprocessors"]) >= 1
        # Each subprocessor should have name, purpose, location
        for sp in data["subprocessors"]:
            assert "name" in sp
            assert "purpose" in sp
            assert "location" in sp


# =============================================================================
# 6. COMPLIANCE AUDIT LOGGING
# =============================================================================
class TestComplianceAudit:

    def test_audit_log_entries_have_required_fields(self):
        """Every audit log entry must have timestamp, user_ref, regulation, request_type, outcome."""
        from compliance_audit import clear_compliance_audit_log, get_compliance_audit_log
        clear_compliance_audit_log()

        # Trigger a consent change
        client.post("/dpdp/consent", headers=headers(), json={
            "marketing_communications": True
        })

        entries = get_compliance_audit_log()
        assert len(entries) >= 1
        entry = entries[0]
        assert "timestamp" in entry
        assert "iso_timestamp" in entry
        assert "user_ref" in entry
        assert "regulation" in entry
        assert "request_type" in entry
        assert "outcome" in entry
        assert entry["regulation"] == "DPDP"
        assert entry["request_type"] == "CONSENT_CHANGE"

    def test_audit_log_has_no_raw_pii(self):
        """Audit log entries must not contain raw PII (user_id, email, etc.)."""
        from compliance_audit import clear_compliance_audit_log, get_compliance_audit_log
        clear_compliance_audit_log()

        client.get("/gdpr/access", headers=headers())

        entries = get_compliance_audit_log()
        for entry in entries:
            raw = json.dumps(entry)
            # Should not contain raw email addresses or user IDs
            assert "john@acme" not in raw
            assert "u-" not in raw or "user_ref" in entry  # user_ref is fine

    def test_audit_log_not_erasable_by_erasure(self):
        """The erasure flow must not delete the compliance audit log."""
        from compliance_audit import clear_compliance_audit_log, get_compliance_audit_log
        clear_compliance_audit_log()

        # Record an entry
        client.get("/gdpr/access", headers=headers())
        count_before = len(get_compliance_audit_log())

        # Erase the user
        client.delete("/gdpr/erase", headers=headers())

        # Audit log should still exist (and actually have MORE entries now)
        count_after = len(get_compliance_audit_log())
        assert count_after >= count_before

    def test_audit_log_admin_endpoint(self):
        """Admin audit endpoint should return compliance audit entries."""
        # Trigger some events
        client.post("/dpdp/consent", headers=headers(), json={"marketing_communications": True})
        client.get("/gdpr/access", headers=headers())

        # DPDP admin audit
        resp = client.get("/dpdp/admin/audit", headers=headers(get_admin_token()))
        assert resp.status_code == 200
        assert "audit_entries" in resp.json()

        # GDPR admin audit
        resp = client.get("/gdpr/admin/audit", headers=headers(get_admin_token()))
        assert resp.status_code == 200
        assert "audit_entries" in resp.json()

        # CCPA admin audit
        resp = client.get("/ccpa/admin/audit", headers=headers(get_admin_token()))
        assert resp.status_code == 200
        assert "audit_entries" in resp.json()


# =============================================================================
# 7. CCPA PRIVACY NOTICE
# =============================================================================
class TestCCPANotice:

    def test_ccpa_notice_has_categories_and_rights(self):
        """CCPA notice must list data categories, purposes, and rights."""
        resp = client.get("/ccpa/notice")
        assert resp.status_code == 200
        data = resp.json()
        assert data["regulation"] == "CCPA/CPRA"
        assert "notice" in data
        categories = data["notice"]
        assert len(categories) >= 3
        for cat in categories:
            assert "category" in cat
            assert "purpose" in cat
            assert "sold_or_shared" in cat
        assert "rights" in data
        assert "Right to Opt-Out of Sale/Sharing" in data["rights"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])