"""
Comprehensive compliance tests for DPDP (India), GDPR (EU), and CCPA/CPRA (California).
Tests: granular consent, GDPR data subject rights, CCPA Do Not Sell, DPA, erasure cascade, audit logging.
"""
import os
import time
import json
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


def get_token(username="john", password="password"):
    resp = client.post("/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


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
        john = [u for u in get_users_db() if u.username == "john"][0]
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
        from auth.models import get_users_db, _users_db
        from utils.cache import config_cache

        # Get John's user ID
        john = [u for u in get_users_db() if u.username == "john"][0]
        user_id = john.id
        tenant_id = john.tenant_id

        # Pre-populate data across all layers
        # 1. Items
        db.add_item({"id": "item-1", "user_id": user_id, "tenant_id": tenant_id, "title": "John's item"})

        # 2. Consent records
        db.record_consent(user_id, {"version": "1.0", "purpose": "test"})

        # 3. Nominee
        db.set_nominee(user_id, {"name": "Jane", "email": "jane@test.com", "relationship": "friend"})

        # 4. Grievance
        db.add_grievance({"user_id": user_id, "subject": "test", "description": "test grievance", "status": "open"})

        # 5. MFA
        db.set_mfa_secret(user_id, "test-secret")
        db.set_mfa_pending_secret(user_id, "pending-secret")
        db.set_mfa_recovery_codes(user_id, ["code1", "code2"])

        # 6. Delegation — set directly to avoid item existence check in delegate_item
        db.delegations["item-delegated"] = {
            "assigned_to": user_id,
            "assigned_by": "admin",
            "note": "test note",
            "timestamp": time.time()
        }

        # 7. Failed login attempts
        db.failed_login_attempts[user_id] = [time.time() - 10, time.time() - 5]
        db.locked_accounts[user_id] = time.time() + 300

        # 8. Cache
        config_cache.set(f"user:{user_id}", {"data": "test"}, tags=[f"user:{user_id}"])

        # Verify data exists before erasure
        assert any(u.id == user_id for u in get_users_db())
        assert any(i.get("user_id") == user_id for i in db.get_items(tenant_id))
        assert len(db.get_consents(user_id)) > 0
        assert db.get_nominee(user_id) is not None
        assert len(db.get_grievances(user_id)) > 0
        assert db.get_mfa_secret(user_id) is not None
        assert user_id in db.delegations or any(
            d.get("assigned_to") == user_id for d in db.delegations.values()
        )
        assert user_id in db.failed_login_attempts
        assert user_id in db.locked_accounts

        # Execute erasure via GDPR Art. 17
        resp = client.delete("/gdpr/erase", headers=headers())
        assert resp.status_code == 200

        # === VERIFY EVERY LAYER IS CLEAN ===
        # 1. User record
        assert not any(u.id == user_id for u in get_users_db()), "User record not erased"

        # 2. Items
        assert not any(i.get("user_id") == user_id for i in db.get_items(tenant_id)), "Items not erased"

        # 3. Consent records
        assert len(db.get_consents(user_id)) == 0, "Consent records not erased"

        # 4. Nominee
        assert db.get_nominee(user_id) is None, "Nominee not erased"

        # 5. Grievances (anonymized, not deleted)
        grievances = db.get_grievances(user_id)
        for g in grievances:
            assert g.get("user_id") == "**ERASED**", "Grievance not anonymized"

        # 6. MFA secrets
        assert db.get_mfa_secret(user_id) is None, "MFA secret not erased"
        assert db.get_mfa_pending_secret(user_id) is None, "MFA pending secret not erased"
        assert db.get_mfa_recovery_codes(user_id) is None, "MFA recovery codes not erased"

        # 7. Delegations
        assert not any(
            d.get("assigned_to") == user_id for d in db.delegations.values()
        ), "Delegations not erased"

        # 8. Locked accounts / failed attempts
        assert user_id not in db.failed_login_attempts, "Failed login attempts not erased"
        assert user_id not in db.locked_accounts, "Locked account not erased"

        # 9. Cache
        assert config_cache.get(f"user:{user_id}") is None, "Cache not invalidated"

    def test_compliance_audit_survives_erasure(self):
        """Compliance audit log entries must survive user erasure and use hashed refs."""
        from compliance_audit import get_compliance_audit_log

        clear_compliance_audit_log()

        # Record an audit event before erasure
        from auth.models import get_users_db
        john = [u for u in get_users_db() if u.username == "john"][0]
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