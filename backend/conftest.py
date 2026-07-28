"""Shared test fixtures — reset state between tests so rate limiters don't bleed over."""
import asyncio
import os
import pytest
from main import app
from database import db
from auth.models import set_mfa_enabled, seed_initial_data
from compliance_audit import clear_compliance_audit_log

# Known seed user ids (see auth/models.py's seed_initial_data). The User rows
# themselves persist for the whole test session (db.clear() below doesn't
# touch them), but tests mutate per-user columns like mfa_enabled — those
# need resetting between tests even though the rows stay.
_SEED_USER_IDS = ["u-1", "u-2", "u-3"]


@pytest.fixture(autouse=True)
def reset_state():
    """Reset rate limiter, database, and per-user mutable state before every test."""
    # Reset the shared rate limiter so each test starts with a clean budget
    app.state.limiter.reset()

    async def _reset_async():
        # Idempotent (no-ops once tenants/users already exist). Needed
        # explicitly because this test suite uses `TestClient(app)` without
        # `with` throughout, so main.py's app lifespan — which normally
        # calls this — never actually runs.
        await seed_initial_data()
        # Clears all tenant-scoped data: items, integrations, consent
        # records, audit logs, MFA recovery codes, failed-login/lockout
        # state, billing, etc. Does NOT touch Tenant/User rows (see
        # MockDatabase.clear() in database.py).
        await db.clear()
        # db.clear() doesn't reset per-user columns (mfa_enabled/mfa_secret
        # live on the User row itself) — reset those for the seed users.
        for user_id in _SEED_USER_IDS:
            await set_mfa_enabled(user_id, False)
            await db.clear_mfa_secret(user_id)
            await db.clear_mfa_recovery_codes(user_id)

    asyncio.run(_reset_async())

    # Reset MAX_LOGIN_ATTEMPTS to default
    os.environ.pop("MAX_LOGIN_ATTEMPTS", None)
    # Clear compliance audit log
    clear_compliance_audit_log()
    yield