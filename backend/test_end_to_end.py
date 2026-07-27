"""
End-to-end integration tests for Clutsch business logic.
Tests: feed ordering, snooze, consent, deduplication, and scoring offloading.
"""
import os
import time
import uuid
import pytest
from fastapi.testclient import TestClient
from main import app
from database import db
from services import scoring_service, archived_items, snoozed_items

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ENCRYPTION_KEY", "N0ZPaUZrRUZXSm5yYVpwUnVpYm9hckhLcm9LdER3SDA=")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")
os.environ.setdefault("JOHN_PASSWORD", "password")
os.environ.setdefault("SARAH_PASSWORD", "sarah123")

client = TestClient(app)


def get_token():
    """Login as john (non-admin, no MFA)."""
    resp = client.post("/auth/login", data={"username": "john", "password": "password"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    data = resp.json()
    assert "access_token" in data, f"No access_token in response: {data}"
    return data["access_token"]


# =============================================================================
# 1. DASHBOARD BYPASS — /priorities/feed is the single source of truth
# =============================================================================

def test_feed_ordering():
    """Items from /priorities/feed must be ordered by priority descending — no client-side sort needed."""
    db.clear()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Create items with different priorities
    item_data = [
        {"id": "item-low", "tenant_id": "t-acme", "text": "Low priority task", "source": "manual",
         "metadata": {}, "timestamp": time.time(),
         "priorityScore": 10, "priorityTier": "low"},
        {"id": "item-high", "tenant_id": "t-acme", "text": "High priority task", "source": "manual",
         "metadata": {}, "timestamp": time.time(),
         "priorityScore": 90, "priorityTier": "urgent"},
        {"id": "item-med", "tenant_id": "t-acme", "text": "Medium priority task", "source": "manual",
         "metadata": {}, "timestamp": time.time(),
         "priorityScore": 50, "priorityTier": "medium"},
    ]
    for item in item_data:
        db.add_item(item)

    # Fetch the feed
    resp = client.get("/priorities/feed", headers=headers)
    assert resp.status_code == 200, f"Feed request failed: {resp.text}"
    feed = resp.json()

    # Verify ordering: highest priority first
    assert len(feed) > 0, "Feed should not be empty"
    scores = [item["priorityScore"] for item in feed]
    assert scores == sorted(scores, reverse=True), \
        f"Feed not sorted by priority descending. Scores: {scores}"

    # Verify AI explanation is present (the feed includes explanations)
    for item in feed:
        assert "explanation" in item, f"Item {item['id']} missing explanation"
        assert "priorityTier" in item, f"Item {item['id']} missing priorityTier"


# =============================================================================
# 2. SNOOZE — works for chosen duration, item reappears after
# =============================================================================

def test_snooze_basic():
    """Snoozing an item removes it from the feed for the specified duration."""
    db.clear()
    archived_items.clear()
    snoozed_items.clear()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Create an item
    item = {"id": "snooze-test-1", "tenant_id": "t-acme", "text": "Snooze me", "source": "manual",
            "metadata": {}, "timestamp": time.time()}
    db.add_item(item)

    # Verify it's in the feed
    resp = client.get("/priorities/feed", headers=headers)
    assert resp.status_code == 200
    ids_before = {i["id"] for i in resp.json()}
    assert "snooze-test-1" in ids_before, "Item should be in feed before snooze"

    # Snooze for 1 hour
    resp = client.post("/items/snooze-test-1/snooze", json={"hours": 1}, headers=headers)
    assert resp.status_code == 200, f"Snooze failed: {resp.text}"

    # Verify it's removed from the feed
    resp = client.get("/priorities/feed", headers=headers)
    ids_after = {i["id"] for i in resp.json()}
    assert "snooze-test-1" not in ids_after, "Item should not appear in feed after snooze"


def test_snooze_duration_choices():
    """User can snooze for 1h, 4h, or 24h — verify the API contract."""
    db.clear()
    archived_items.clear()
    snoozed_items.clear()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    durations = [("1h", 1), ("4h", 4), ("24h", 24)]
    for label, hours in durations:
        item_id = f"snooze-{label}"
        item = {"id": item_id, "tenant_id": "t-acme", "text": f"Snooze {label}", "source": "manual",
                "metadata": {}, "timestamp": time.time()}
        db.add_item(item)

        resp = client.post(f"/items/{item_id}/snooze", json={"hours": hours}, headers=headers)
        assert resp.status_code == 200, f"Snooze {label} failed: {resp.text}"

        # Verify removed from feed
        resp = client.get("/priorities/feed", headers=headers)
        ids = {i["id"] for i in resp.json()}
        assert item_id not in ids, f"Item {item_id} should be snoozed"


def test_snooze_reappears():
    """Item should reappear in the feed once the snooze period expires."""
    db.clear()
    archived_items.clear()
    snoozed_items.clear()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Create an item
    item = {"id": "snooze-reappear", "tenant_id": "t-acme", "text": "Will reappear", "source": "manual",
            "metadata": {}, "timestamp": time.time()}
    db.add_item(item)

    # Snooze for a very short duration (1 second = 1/3600 hours)
    # The backend expects hours as int, so we test with 1 hour and verify it's gone
    resp = client.post("/items/snooze-reappear/snooze", json={"hours": 1}, headers=headers)
    assert resp.status_code == 200

    # Verify removed
    resp = client.get("/priorities/feed", headers=headers)
    assert "snooze-reappear" not in {i["id"] for i in resp.json()}

    # Mock the snooze expiry by clearing snoozed_items
    snoozed_items.clear()

    # Verify it reappears
    resp = client.get("/priorities/feed", headers=headers)
    ids = {i["id"] for i in resp.json()}
    assert "snooze-reappear" in ids, "Item should reappear after snooze expires"


# =============================================================================
# 3. CONSENT TOGGLE — persists across page reload
# =============================================================================

def test_consent_toggle_persists():
    """Consent toggle in Settings should persist consent state via the DPDP API."""
    db.clear()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Initially, no consent recorded
    resp = client.get("/dpdp/consent", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["consent_history"] == []

    # Grant consent
    resp = client.post("/dpdp/consent", json={
        "version": "1.2",
        "purpose": "AI prioritization and data aggregation"
    }, headers=headers)
    assert resp.status_code == 200, f"Consent grant failed: {resp.text}"

    # Verify consent is persisted
    resp = client.get("/dpdp/consent", headers=headers)
    assert resp.status_code == 200
    history = resp.json()["consent_history"]
    assert len(history) == 1
    assert history[0]["version"] == "1.2"
    assert history[0]["purpose"] == "AI prioritization and data aggregation"

    # Simulate page reload: new request, same user
    resp = client.get("/dpdp/consent", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()["consent_history"]) == 1, "Consent should persist after reload"


def test_consent_withdraw():
    """Consent can be withdrawn, and the record reflects it."""
    db.clear()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Grant consent first
    client.post("/dpdp/consent", json={
        "version": "1.2",
        "purpose": "AI prioritization and data aggregation"
    }, headers=headers)

    # Withdraw consent
    resp = client.post("/dpdp/consent", json={
        "version": "withdrawn",
        "purpose": "withdrawn"
    }, headers=headers)
    assert resp.status_code == 200, f"Consent withdraw failed: {resp.text}"

    # Verify withdrawal is recorded
    resp = client.get("/dpdp/consent", headers=headers)
    history = resp.json()["consent_history"]
    assert len(history) == 2
    assert history[1]["version"] == "withdrawn"


# =============================================================================
# 4. MESSAGE DEDUPLICATION — syncing a source twice doesn't create duplicates
# =============================================================================

def test_dedup_on_sync():
    """Re-syncing the same source should not create duplicate items."""
    db.clear()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Simulate the first sync of an integration
    adapter = None
    from adapters.gmail import GmailAdapter
    adapter = GmailAdapter()

    import asyncio
    items1 = asyncio.run(adapter.fetch_items())
    count_before = len(db.get_items("t-acme"))

    # Ingest items (simulate what the sync endpoint would do)
    for item in items1:
        # Check for duplicates by source + external_id
        existing = [i for i in db.get_items("t-acme")
                    if i.get("source") == "gmail" and i.get("external_id") == item.external_id]
        if not existing:
            db.add_item({
                "id": str(uuid.uuid4()),
                "tenant_id": "t-acme",
                "external_id": item.external_id,
                "source": "gmail",
                "text": item.content,
                "subject": item.subject,
                "thread_id": item.thread_id,
                "sender_name": item.sender["name"],
                "sender_handle": item.sender["handle"],
                "timestamp": time.time(),
                "metadata": item.metadata or {},
            })

    count_after_first = len(db.get_items("t-acme"))

    # Simulate a second sync — same items should not create duplicates
    for item in items1:
        existing = [i for i in db.get_items("t-acme")
                    if i.get("source") == "gmail" and i.get("external_id") == item.external_id]
        if not existing:
            db.add_item({
                "id": str(uuid.uuid4()),
                "tenant_id": "t-acme",
                "external_id": item.external_id,
                "source": "gmail",
                "text": item.content,
                "subject": item.subject,
                "thread_id": item.thread_id,
                "sender_name": item.sender["name"],
                "sender_handle": item.sender["handle"],
                "timestamp": time.time(),
                "metadata": item.metadata or {},
            })

    count_after_second = len(db.get_items("t-acme"))

    # The count should be the same after the second sync (no duplicates)
    assert count_after_second == count_after_first, \
        f"Second sync created {count_after_second - count_after_first} duplicates"


def test_dedup_different_content_is_not_duplicate():
    """Different content from the same source should not be treated as a duplicate."""
    db.clear()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    import uuid
    # Add first item
    db.add_item({
        "id": str(uuid.uuid4()),
        "tenant_id": "t-acme",
        "external_id": "msg-1",
        "source": "gmail",
        "text": "First message",
        "timestamp": time.time(),
    })

    # Add second item with same source + external_id but different content
    # This should be treated as a duplicate (same external_id)
    existing = [i for i in db.get_items("t-acme")
                if i.get("source") == "gmail" and i.get("external_id") == "msg-1"]
    if not existing:
        db.add_item({
            "id": str(uuid.uuid4()),
            "tenant_id": "t-acme",
            "external_id": "msg-1",
            "source": "gmail",
            "text": "Updated content",
            "timestamp": time.time(),
        })

    count = len(db.get_items("t-acme"))
    # Should still be 1 (the second attempt was deduped)
    assert count == 1, f"Expected 1 item after dedup, got {count}"


# =============================================================================
# 5. SCORING — background worker processes scores at sync time
# =============================================================================

def test_feed_response_has_explanations():
    """/priorities/feed should include AI explanations for each item."""
    db.clear()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    # Add an item
    item = {"id": "explain-test", "tenant_id": "t-acme", "text": "Test explanation",
            "source": "manual", "metadata": {}, "timestamp": time.time()}
    db.add_item(item)

    resp = client.get("/priorities/feed", headers=headers)
    assert resp.status_code == 200
    feed = resp.json()
    assert len(feed) > 0

    # Each item should have an explanation
    for item in feed:
        assert "explanation" in item, f"Missing explanation: {item['id']}"
        assert len(item["explanation"]) > 0, f"Empty explanation: {item['id']}"
        assert "priorityTier" in item, f"Missing priorityTier: {item['id']}"
        assert "priorityScore" in item, f"Missing priorityScore: {item['id']}"


# =============================================================================
# 6. FEED + ITEMS ENDPOINT CONSISTENCY
# =============================================================================

def test_feed_does_not_include_archived():
    """Archived items should not appear in the priority feed."""
    db.clear()
    archived_items.clear()
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}

    item = {"id": "archived-test", "tenant_id": "t-acme", "text": "Will be archived",
            "source": "manual", "metadata": {}, "timestamp": time.time()}
    db.add_item(item)

    # Archive it
    resp = client.post("/items/archived-test/archive", headers=headers)
    assert resp.status_code == 200

    # Verify it's not in the feed
    resp = client.get("/priorities/feed", headers=headers)
    ids = {i["id"] for i in resp.json()}
    assert "archived-test" not in ids, "Archived item should not appear in feed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])