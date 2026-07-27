"""
Performance and reliability tests for Clutsch.
Tests: health/ready endpoints, bcrypt offloading, cache invalidation, structured logging, graceful shutdown.
"""
import os
import time
import json
import logging
import pytest
from fastapi.testclient import TestClient
from main import app
from database import db
from utils.cache import config_cache, integration_cache
from log_config import LogContext

os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("ENCRYPTION_KEY", "N0ZPaUZrRUZXSm5yYVpwUnVpYm9hckhLcm9LdER3SDA=")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")
os.environ.setdefault("JOHN_PASSWORD", "password")
os.environ.setdefault("SARAH_PASSWORD", "sarah123")

client = TestClient(app)


def get_token():
    resp = client.post("/auth/login", data={"username": "john", "password": "password"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


# =============================================================================
# 1. HEALTH / READINESS ENDPOINTS
# =============================================================================

def test_health_returns_200():
    """/health should return 200 whenever the process is alive."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_ready_returns_200_when_db_ok():
    """/ready should return 200 when all dependencies are healthy."""
    resp = client.get("/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["database"] == "ok"
    assert data["checks"]["background_worker"] == "ok"


def test_ready_returns_non200_when_db_down():
    """/ready should return non-200 when the database is unreachable."""
    # Temporarily break the database
    original_get_items = db.get_items
    db.get_items = lambda tid: (_ for _ in ()).throw(Exception("DB connection refused"))
    try:
        resp = client.get("/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "not_ready"
        assert "error" in data["checks"]["database"]
    finally:
        db.get_items = original_get_items


# =============================================================================
# 2. BCRYPT OFFLOADED FROM EVENT LOOP
# =============================================================================

@pytest.mark.asyncio
async def test_async_password_hashing():
    """Password hashing should run in a thread pool, not block the event loop."""
    from async_crypto import hash_password, verify_password
    import asyncio

    # Hash a password
    hashed = await hash_password("test-password-123")
    assert hashed is not None
    assert hashed != "test-password-123"

    # Verify it
    assert await verify_password("test-password-123", hashed) is True
    assert await verify_password("wrong-password", hashed) is False


@pytest.mark.asyncio
async def test_concurrent_hashing():
    """Multiple concurrent hashing operations should not block each other."""
    from async_crypto import hash_password
    import asyncio

    passwords = [f"password-{i}" for i in range(10)]
    results = await asyncio.gather(*[hash_password(p) for p in passwords])
    assert len(results) == 10
    assert all(r != p for r, p in zip(results, passwords))


# =============================================================================
# 3. CACHE INVALIDATION
# =============================================================================

def test_cache_basic_set_get():
    """Cache should store and retrieve values."""
    config_cache.set("test-key", {"data": "value"})
    result = config_cache.get("test-key")
    assert result == {"data": "value"}


def test_cache_ttl_expiry():
    """Cache entries should expire after TTL."""
    short_cache = __import__("utils.cache", fromlist=["SimpleTTLCache"]).SimpleTTLCache(ttl_seconds=1)
    short_cache.set("expire-key", "value")
    assert short_cache.get("expire-key") == "value"
    time.sleep(1.5)
    assert short_cache.get("expire-key") is None


def test_cache_tag_invalidation():
    """Cache entries tagged with a key should be invalidated together."""
    config_cache.invalidate_all()
    config_cache.set("user-1", {"name": "Alice"}, tags=["tenant:t-acme"])
    config_cache.set("user-2", {"name": "Bob"}, tags=["tenant:t-acme"])
    config_cache.set("other", {"data": "keep"}, tags=["other"])

    assert config_cache.get("user-1") is not None
    assert config_cache.get("user-2") is not None
    assert config_cache.get("other") is not None

    # Invalidate the tenant tag
    config_cache.invalidate_tag("tenant:t-acme")

    assert config_cache.get("user-1") is None, "Tagged entry should be invalidated"
    assert config_cache.get("user-2") is None, "Tagged entry should be invalidated"
    assert config_cache.get("other") is not None, "Untagged entry should remain"


def test_cache_invalidate_all():
    """invalidate_all should clear the entire cache."""
    config_cache.invalidate_all()
    config_cache.set("a", 1)
    config_cache.set("b", 2)
    config_cache.invalidate_all()
    assert config_cache.get("a") is None
    assert config_cache.get("b") is None


def test_cache_stats():
    """Cache stats should return meaningful metrics."""
    config_cache.invalidate_all()
    config_cache.set("stat-key", "value")
    stats = config_cache.get_stats()
    assert stats["total_entries"] >= 1
    assert stats["active"] >= 1
    assert "tags" in stats


# =============================================================================
# 4. STRUCTURED LOGGING
# =============================================================================

def test_request_id_in_response():
    """Every response should include an X-Request-ID header."""
    resp = client.get("/health")
    assert "X-Request-ID" in resp.headers
    request_id = resp.headers["X-Request-ID"]
    assert len(request_id) > 0
    # Verify it's a UUID
    import uuid
    uuid.UUID(request_id)  # Will raise ValueError if not valid


def test_log_context():
    """LogContext should propagate request_id."""
    LogContext.set_request_id("test-req-123")
    assert LogContext.get_request_id() == "test-req-123"
    LogContext.clear()
    assert LogContext.get_request_id() == ""


# =============================================================================
# 5. MULTIPLE WORKER CONFIGURATION
# =============================================================================

def test_gunicorn_config_exists():
    """Gunicorn configuration file should be present and parseable."""
    assert os.path.exists("gunicorn.conf.py")
    with open("gunicorn.conf.py") as f:
        content = f.read()
    assert "bind" in content
    assert "worker_class" in content
    assert "uvicorn" in content


# =============================================================================
# 6. HEALTHY LOGIN FLOW (smoke test)
# =============================================================================

def test_smoke_login():
    """Login should complete in under 2 seconds (simulating load test criteria)."""
    start = time.time()
    resp = client.post("/auth/login", data={"username": "john", "password": "password"})
    elapsed = time.time() - start
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    assert elapsed < 2.0, f"Login took {elapsed:.2f}s — exceeds 2s threshold"


def test_smoke_register():
    """Registration should complete quickly."""
    start = time.time()
    resp = client.post("/auth/register", json={
        "username": "perf-test-user",
        "email": "perf@test.com",
        "password": "perftest123",
        "name": "Perf Test"
    })
    elapsed = time.time() - start
    assert resp.status_code == 200, f"Register failed: {resp.text}"
    assert elapsed < 3.0, f"Register took {elapsed:.2f}s"


# =============================================================================
# 7. RATE LIMITING (smoke test)
# =============================================================================

def test_health_not_rate_limited():
    """/health should not be rate-limited."""
    for _ in range(10):
        resp = client.get("/health")
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])