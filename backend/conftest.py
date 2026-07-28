"""Shared test fixtures — reset state between tests so rate limiters don't bleed over."""
import asyncio
import os
import pytest
from passlib.context import CryptContext
from sqlalchemy import select
from main import app
from database import db
from db_engine import AsyncSessionLocal
from models import User as UserORM, Tenant as TenantORM
from auth.models import set_mfa_enabled, seed_initial_data
from compliance_audit import clear_compliance_audit_log

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Known seed users (see auth/models.py's seed_initial_data) — fixed ids
# because plenty of tests hardcode them (e.g. "u-2"). Several tests delete
# a seed user for real via the actual erasure endpoints (DELETE
# /privacy/account, /gdpr/erase) to verify erasure works — but
# seed_initial_data() only (re)seeds when the ENTIRE users table is empty,
# not per missing user, so once one test deletes "john" mid-session every
# later test in the whole run that logs in as john fails too. Recreate any
# missing seed user before every test. This is a test-isolation convenience
# specific to this fixture — production code should NOT silently resurrect
# a deleted account with its old id, which is why this lives here and not
# in auth/models.py.
_SEED_TENANTS = [
    ("t-acme", "Acme Corp", "acme.com"),
    ("t-globex", "Globex Corporation", "globex.com"),
    # "t1" is used throughout the test suite as an ad-hoc tenant id for items
    # unrelated to auth (e.g. TestDatabase's raw item/audit-log tests). Item,
    # Grievance, etc. all have a real FK to tenants.id now, so it needs to
    # actually exist rather than being an arbitrary string like the old
    # in-memory mock allowed.
    ("t1", "Test Tenant 1", "t1.test"),
]
_SEED_USERS = [
    ("u-1", "admin", "admin@acme.com", "t-acme", "admin", "ADMIN_PASSWORD"),
    ("u-2", "john", "john@acme.com", "t-acme", "user", "JOHN_PASSWORD"),
    ("u-3", "sarah", "sarah@globex.com", "t-globex", "admin", "SARAH_PASSWORD"),
]
_SEED_USER_IDS = [u[0] for u in _SEED_USERS]


async def _ensure_seed_data():
    async with AsyncSessionLocal() as session:
        for tenant_id, name, domain in _SEED_TENANTS:
            existing = await session.execute(select(TenantORM.id).where(TenantORM.id == tenant_id))
            if existing.first() is None:
                session.add(TenantORM(id=tenant_id, name=name, domain=domain))
        for user_id, username, email, tenant_id, role, pw_env in _SEED_USERS:
            existing = await session.execute(select(UserORM.id).where(UserORM.id == user_id))
            if existing.first() is None:
                session.add(UserORM(
                    id=user_id, username=username, email=email, tenant_id=tenant_id, role=role,
                    hashed_password=_pwd_context.hash(os.environ[pw_env]), mfa_enabled=False,
                ))
        await session.commit()


@pytest.fixture(autouse=True)
def reset_state():
    """Reset rate limiter, database, and per-user mutable state before every test."""
    # Reset the shared rate limiter so each test starts with a clean budget
    app.state.limiter.reset()

    async def _reset_async():
        # Idempotent first-time seed. Needed explicitly because this test
        # suite uses TestClient(app) without `with` throughout, so main.py's
        # app lifespan — which normally calls this — never actually runs.
        await seed_initial_data()
        # Recreate any seed user/tenant a previous test deleted for real —
        # see the module docstring above _SEED_USERS for why this is needed
        # in addition to seed_initial_data().
        await _ensure_seed_data()
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