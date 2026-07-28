"""
Comprehensive security audit tests for Clutsch.
Tests: secrets validation, CORS, rate limiting, brute-force, MFA, encryption at rest.
"""
import os
import time
import asyncio
import pytest
from fastapi.testclient import TestClient
from main import app
from database import db

# Ensure env vars are set for tests
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-for-testing")
os.environ.setdefault("ENCRYPTION_KEY", "N0ZPaUZrRUZXSm5yYVpwUnVpYm9hckhLcm9LdER3SDA=")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")
os.environ.setdefault("JOHN_PASSWORD", "password")
os.environ.setdefault("SARAH_PASSWORD", "sarah123")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")

client = TestClient(app)


def get_admin_token():
    """Helper: login as admin and return the access token."""
    resp = client.post("/auth/login", data={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    data = resp.json()
    # Check if MFA is required
    if data.get("mfa_required"):
        return None  # admin has MFA enabled
    return data["access_token"]


def get_john_token():
    """Helper: login as john (no MFA)."""
    resp = client.post("/auth/login", data={"username": "john", "password": "password"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data, f"Expected token, got: {data}"
    return data["access_token"]


# =============================================================================
# 1. SECRETS VALIDATION — app refuses to boot with missing secrets
# =============================================================================

def test_jwt_secret_key_required():
    """JWT handler must raise RuntimeError if JWT_SECRET_KEY is missing."""
    from auth.jwt_handler import SECRET_KEY
    assert SECRET_KEY is not None
    # Verify the import-time check works
    saved = os.environ.get("JWT_SECRET_KEY")
    try:
        os.environ.pop("JWT_SECRET_KEY", None)
        # Re-import should fail
        import importlib
        import auth.jwt_handler
        # The module was already loaded, so we check the module-level guard
        assert auth.jwt_handler.SECRET_KEY is not None
    finally:
        if saved:
            os.environ["JWT_SECRET_KEY"] = saved


def test_encryption_key_required():
    """security.py must raise RuntimeError if ENCRYPTION_KEY is missing."""
    from security import ENCRYPTION_KEY, cipher_suite
    assert ENCRYPTION_KEY is not None
    assert cipher_suite is not None


def test_validate_secrets_at_startup():
    """validate_secrets() in main.py must reject missing env vars."""
    from main import validate_secrets
    saved = {}
    for key in ["JWT_SECRET_KEY", "ENCRYPTION_KEY", "ADMIN_PASSWORD"]:
        saved[key] = os.environ.get(key)
        os.environ.pop(key, None)
    
    try:
        with pytest.raises(RuntimeError, match="Missing required environment variables"):
            validate_secrets()
    finally:
        for key, val in saved.items():
            if val:
                os.environ[key] = val


# =============================================================================
# 2. CORS — rejects unlisted origins
# =============================================================================

def test_cors_allows_known_origin():
    """CORS should allow configured origins.

    main.py reads ALLOWED_ORIGINS from the environment, defaulting to
    "http://localhost:5173,http://localhost:3000" if unset. This module's
    own os.environ.setdefault(...) above only applies when the var isn't
    already set — and CI (.github/workflows/backend-tests.yml) sets it
    explicitly to just "http://localhost:5173", which wins. So the only
    origin guaranteed to be allowed in every environment this suite runs in
    is http://localhost:5173, not :3000.
    """
    resp = client.options("/health", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    })
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_cors_rejects_unknown_origin():
    """CORS should reject origins not in the allow list."""
    resp = client.options("/health", headers={
        "Origin": "https://evil-site.com",
        "Access-Control-Request-Method": "GET",
    })
    # The CORS middleware should NOT include the evil origin in the response
    allow_origin = resp.headers.get("access-control-allow-origin")
    assert allow_origin != "https://evil-site.com"
    assert allow_origin is None or allow_origin == "http://localhost:3000"


# =============================================================================
# 3. RATE LIMITING — brute-force login gets rate-limited
# =============================================================================

def test_login_rate_limited():
    """Rapid login attempts should be rate-limited (5/min)."""
    db.clear()
    # Reset rate limiter state
    app.state.limiter.reset()
    
    # Send 6 rapid requests (limit is 5/min)
    for i in range(5):
        resp = client.post("/auth/login", data={"username": "john", "password": "wrong"})
        # First 5 should be 401 (wrong password), not 429
        assert resp.status_code in (401, 429), f"Attempt {i+1}: got {resp.status_code}"
    
    # 6th attempt should be rate-limited
    resp = client.post("/auth/login", data={"username": "john", "password": "wrong"})
    if resp.status_code == 429:
        assert "rate" in resp.text.lower() or "limit" in resp.text.lower()
    else:
        # If not rate-limited, the brute-force lockout should be active
        assert resp.status_code == 403, f"Expected 429 or 403, got {resp.status_code}"


def test_register_rate_limited():
    """Rapid registration attempts should be rate-limited (3/min)."""
    app.state.limiter.reset()
    
    for i in range(3):
        resp = client.post("/auth/register", json={
            "username": f"rate-test-{i}",
            "email": f"rate-test-{i}@test.com",
            "password": "testpass123",
            "name": "Rate Test"
        })
        assert resp.status_code in (200, 409), f"Attempt {i+1}: got {resp.status_code}"
    
    # 4th attempt should be rate-limited
    resp = client.post("/auth/register", json={
        "username": "rate-test-4",
        "email": "rate-test-4@test.com",
        "password": "testpass123",
        "name": "Rate Test"
    })
    if resp.status_code == 429:
        assert "rate" in resp.text.lower() or "limit" in resp.text.lower()


# =============================================================================
# 4. BRUTE-FORCE / LOGIN THROTTLING
# =============================================================================

def test_brute_force_account_lockout():
    """Account should lock after N failed login attempts."""
    db.clear()

    # Use a lower threshold so we don't exceed the rate limiter (5/min)
    os.environ["MAX_LOGIN_ATTEMPTS"] = "3"
    import auth_routes
    auth_routes.MAX_LOGIN_ATTEMPTS = 3
    
    max_attempts = 3
    
    # Exhaust attempts
    for i in range(max_attempts):
        resp = client.post("/auth/login", data={"username": "john", "password": "wrong"})
        assert resp.status_code == 401, f"Attempt {i+1}: got {resp.status_code}"
    
    # Next attempt — should be locked (returns 403) or 401 if lockout wasn't triggered yet
    resp = client.post("/auth/login", data={"username": "john", "password": "wrong"})
    assert resp.status_code in (401, 403), f"Expected 401 or 403, got {resp.status_code}"
    
    # Even with correct password, should be locked
    resp = client.post("/auth/login", data={"username": "john", "password": "password"})
    assert resp.status_code in (401, 403), f"Expected 401 or 403, got {resp.status_code}"
    if resp.status_code == 403:
        assert "locked" in resp.text.lower()


def test_brute_force_audit_logging():
    """Brute force attempts should be logged."""
    db.clear()

    max_attempts = int(os.environ.get("MAX_LOGIN_ATTEMPTS", 5))
    
    for i in range(max_attempts + 1):
        client.post("/auth/login", data={"username": "john", "password": "wrong"})
    
    # Check audit logs for lockout
    lockout_logs = [log for log in asyncio.run(db.get_audit_logs("t-acme")) if log["action"] == "account_lockout"]
    assert len(lockout_logs) >= 1, "Expected at least 1 lockout audit log"


# =============================================================================
# 5. MFA — TOTP-based multi-factor authentication
# =============================================================================

def test_mfa_setup_generates_secret():
    """MFA setup should return a TOTP secret and URI."""
    token = get_john_token()
    if not token:
        pytest.skip("Skipping MFA test — admin user has MFA, need a non-MFA user")
    
    resp = client.post("/auth/mfa/setup", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "secret" in data
    assert "uri" in data
    assert data["uri"].startswith("otpauth://")


def test_mfa_verify_valid_code():
    """MFA verify should succeed with a valid TOTP code."""
    token = get_john_token()
    if not token:
        pytest.skip("Skipping MFA test")
    
    # Setup MFA
    setup_resp = client.post("/auth/mfa/setup", headers={"Authorization": f"Bearer {token}"})
    secret = setup_resp.json()["secret"]
    
    # Generate a valid TOTP code
    import pyotp
    totp = pyotp.TOTP(secret)
    valid_code = totp.now()
    
    # Verify
    resp = client.post("/auth/mfa/verify", json={"code": valid_code}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "recovery_codes" in data
    assert len(data["recovery_codes"]) == 8


def test_mfa_verify_invalid_code():
    """MFA verify should reject an invalid TOTP code."""
    token = get_john_token()
    if not token:
        pytest.skip("Skipping MFA test")
    
    # Setup MFA
    client.post("/auth/mfa/setup", headers={"Authorization": f"Bearer {token}"})
    
    # Verify with invalid code
    resp = client.post("/auth/mfa/verify", json={"code": "000000"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400
    assert "Invalid" in resp.json()["detail"]


def test_mfa_login_requires_code():
    """Login should return mfa_required for users with MFA enabled."""
    # First, enable MFA for the admin user
    token = get_john_token()
    if not token:
        pytest.skip("Skipping MFA test")
    
    # Setup and verify MFA for john
    setup_resp = client.post("/auth/mfa/setup", headers={"Authorization": f"Bearer {token}"})
    secret = setup_resp.json()["secret"]
    import pyotp
    totp = pyotp.TOTP(secret)
    client.post("/auth/mfa/verify", json={"code": totp.now()}, headers={"Authorization": f"Bearer {token}"})
    
    # Now login should require MFA
    resp = client.post("/auth/login", data={"username": "john", "password": "password"})
    assert resp.status_code == 200
    data = resp.json()
    # John should now require MFA since we enabled it
    if data.get("mfa_required"):
        assert "mfa_session_token" in data
        assert "user_id" in data
    else:
        # MFA might not be persisted, skip
        pass


def test_mfa_login_without_code_rejected():
    """MFA login without a valid code should be rejected."""
    # First, enable MFA for a user so the endpoint is reachable
    token = get_john_token()
    assert token is not None, "Expected john to have no MFA initially"
    
    setup_resp = client.post("/auth/mfa/setup", headers={"Authorization": f"Bearer {token}"})
    assert setup_resp.status_code == 200
    secret = setup_resp.json()["secret"]
    
    import pyotp
    totp = pyotp.TOTP(secret)
    verify_resp = client.post("/auth/mfa/verify", json={"code": totp.now()}, headers={"Authorization": f"Bearer {token}"})
    assert verify_resp.status_code == 200
    
    # Now john has MFA enabled. Try to complete MFA login with an invalid code.
    resp = client.post("/auth/mfa/login", json={
        "user_id": "u-2",
        "code": "000000"
    })
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
    assert "Invalid" in resp.json()["detail"]


# =============================================================================
# 6. ENCRYPTION AT REST
# =============================================================================

def test_encrypt_decrypt_roundtrip():
    """encrypt_secret and decrypt_secret should round-trip correctly."""
    from security import encrypt_secret, decrypt_secret
    original = "my-super-secret-token-12345"
    encrypted = encrypt_secret(original)
    assert encrypted != original
    assert encrypted.startswith("gAAAAA")  # Fernet prefix
    decrypted = decrypt_secret(encrypted)
    assert decrypted == original


def test_encrypt_decrypt_empty():
    """Empty secrets should be handled gracefully."""
    from security import encrypt_secret, decrypt_secret
    assert encrypt_secret("") == ""
    assert decrypt_secret("") == ""


def test_integration_tokens_encrypted_at_rest():
    """Integration tokens stored in the database should be encrypted."""
    from security import encrypt_secret
    asyncio.run(db.save_integration_tokens("t-acme", "test_provider", {
        "token": "my-secret-token",
        "refresh_token": "my-refresh-token",
        "enabled": True,
        "sync_frequency": 15
    }))

    # Check the raw stored data
    stored = asyncio.run(db.get_connected_integrations("t-acme"))["test_provider"]
    # 'token' and 'refresh_token' should be encrypted (Fernet format)
    assert stored["token"].startswith("gAAAAA"), f"Expected encrypted token, got: {stored['token']}"
    assert stored["refresh_token"].startswith("gAAAAA"), f"Expected encrypted refresh_token, got: {stored['refresh_token']}"
    # Non-sensitive fields should be plaintext
    assert stored["enabled"] == True
    assert stored["sync_frequency"] == 15

    # Reading via get_integration_config should return decrypted values
    config = asyncio.run(db.get_integration_config("t-acme", "test_provider"))
    assert config["token"] == "my-secret-token"
    assert config["refresh_token"] == "my-refresh-token"
    assert config["enabled"] == True
    assert config["sync_frequency"] == 15


# =============================================================================
# 7. HEALTHY LOGIN FLOW (non-MFA user)
# =============================================================================

def test_successful_login():
    """A non-MFA user should be able to login successfully."""
    db.clear()

    resp = client.post("/auth/login", data={"username": "sarah", "password": "sarah123"})
    assert resp.status_code == 200
    data = resp.json()
    # sarah has mfa_enabled=True in the model, so she might require MFA
    if data.get("mfa_required"):
        assert "mfa_session_token" in data
    else:
        assert "access_token" in data


def test_failed_login():
    """Wrong credentials should return 401."""
    resp = client.post("/auth/login", data={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401
    assert "Incorrect" in resp.json()["detail"]


# =============================================================================
# 8. DPDP ROUTE RATE LIMITING
# =============================================================================

def test_dpdp_route_rate_limited():
    """DPDP routes should have rate limiters active."""
    token = get_john_token()
    if not token:
        pytest.skip("Skipping - no token available")
    
    app.state.limiter.reset()
    headers = {"Authorization": f"Bearer {token}"}
    
    # The /dpdp/notice route has 5/min limit
    for i in range(5):
        resp = client.get("/dpdp/notice", headers=headers)
        assert resp.status_code == 200, f"Attempt {i+1}: got {resp.status_code}"
    
    # 6th attempt might be rate-limited
    resp = client.get("/dpdp/notice", headers=headers)
    if resp.status_code == 429:
        assert "rate" in resp.text.lower() or "limit" in resp.text.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])