import os
from pydantic import BaseModel
from typing import Optional, List
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from db_engine import AsyncSessionLocal
from models import User as UserORM, Tenant as TenantORM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(BaseModel):
    id: str
    username: str
    email: str
    tenant_id: str
    role: str = "user"
    hashed_password: Optional[str] = None
    mfa_enabled: bool = False

class Tenant(BaseModel):
    id: str
    name: str
    domain: str

class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str

class TokenData(BaseModel):
    user_id: str
    tenant_id: str


# NOTE: one AsyncSessionLocal() session per call, not per HTTP request — see
# database.py's MockDatabase docstring for the rationale (this is the same
# migration pass, applied consistently to the users/tenants store too).

def _user_row_to_model(row: UserORM) -> User:
    return User(
        id=row.id,
        username=row.username,
        email=row.email,
        tenant_id=row.tenant_id,
        role=row.role,
        hashed_password=row.hashed_password,
        mfa_enabled=row.mfa_enabled,
    )


def _tenant_row_to_model(row: TenantORM) -> Tenant:
    return Tenant(id=row.id, name=row.name, domain=row.domain)


async def get_users_db() -> List[User]:
    """Return every user across every tenant. Kept for backward compatibility;
    prefer get_user_by_id()/get_users_by_tenant() for new code — listing every
    user just to find one by id or filter by tenant doesn't scale."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserORM))
        return [_user_row_to_model(r) for r in result.scalars().all()]


async def get_users_by_tenant(tenant_id: str) -> List[User]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserORM).where(UserORM.tenant_id == tenant_id))
        return [_user_row_to_model(r) for r in result.scalars().all()]


async def get_user_by_id(user_id: str) -> Optional[User]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserORM).where(UserORM.id == user_id))
        row = result.scalar_one_or_none()
        return _user_row_to_model(row) if row else None


async def get_user_by_username(username: str) -> Optional[User]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserORM).where(UserORM.username == username))
        row = result.scalar_one_or_none()
        return _user_row_to_model(row) if row else None


async def get_user_by_email(email: str) -> Optional[User]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserORM).where(UserORM.email == email))
        row = result.scalar_one_or_none()
        return _user_row_to_model(row) if row else None


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


async def delete_user(user_id: str) -> None:
    """Delete a single user row. Callers that need a fully FK-safe erasure
    (GDPR/DPDP right-to-erasure) must call database.db.delete_user_data(user_id)
    or database.db.delete_tenant_data(tenant_id) first — several tables have a
    NOT NULL foreign key to users.id and Postgres will reject this delete
    while those rows still reference the user."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserORM).where(UserORM.id == user_id))
        row = result.scalar_one_or_none()
        if row:
            await session.delete(row)
            await session.commit()


async def get_tenant_by_id(tenant_id: str) -> Optional[Tenant]:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(TenantORM).where(TenantORM.id == tenant_id))
        row = result.scalar_one_or_none()
        return _tenant_row_to_model(row) if row else None


async def add_user(username: str, email: str, password: str, tenant_id: str = "t-acme", role: str = "user", hashed_password: str = None) -> Optional[User]:
    """Add a new user, backed by the real users table."""
    async with AsyncSessionLocal() as session:
        existing = await session.execute(select(UserORM).where(UserORM.username == username))
        if existing.scalar_one_or_none():
            return None
        row = UserORM(
            username=username,
            email=email,
            tenant_id=tenant_id,
            role=role,
            hashed_password=hashed_password or pwd_context.hash(password),
            mfa_enabled=False,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return _user_row_to_model(row)


async def set_mfa_enabled(user_id: str, enabled: bool) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserORM).where(UserORM.id == user_id))
        row = result.scalar_one_or_none()
        if row:
            row.mfa_enabled = enabled
            await session.commit()


async def update_user_fields(user_id: str, **fields) -> Optional[User]:
    """Generic partial update — used by GDPR Art. 16 rectification (email/username)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserORM).where(UserORM.id == user_id))
        row = result.scalar_one_or_none()
        if not row:
            return None
        for key, value in fields.items():
            setattr(row, key, value)
        await session.commit()
        await session.refresh(row)
        return _user_row_to_model(row)


async def seed_initial_data() -> None:
    """Idempotently seed the two demo tenants and three demo users, matching
    the values that used to be hardcoded at module import time. Only inserts if
    the tenants/users tables are empty, so it's safe to call on every startup.

    Gunicorn starts multiple worker processes, each of which runs this at
    startup — the empty-check-then-insert is NOT atomic across processes, so
    two workers can both see "empty" and both attempt to insert the same
    fixed-id rows (id="t-acme", id="u-1", ...). Rather than relying on timing,
    we catch the resulting primary-key violation and treat it as "another
    worker won the race", instead of letting it crash this worker's startup."""
    async with AsyncSessionLocal() as session:
        existing_tenant = await session.execute(select(TenantORM.id).limit(1))
        existing_user = await session.execute(select(UserORM.id).limit(1))
        if existing_tenant.first() is not None or existing_user.first() is not None:
            return  # already seeded

        admin_pw = os.environ.get("ADMIN_PASSWORD")
        john_pw = os.environ.get("JOHN_PASSWORD")
        sarah_pw = os.environ.get("SARAH_PASSWORD")

        if not admin_pw or not john_pw or not sarah_pw:
            raise RuntimeError("CRITICAL: Missing required password environment variables (ADMIN_PASSWORD, JOHN_PASSWORD, SARAH_PASSWORD)")

        session.add_all([
            TenantORM(id="t-acme", name="Acme Corp", domain="acme.com"),
            TenantORM(id="t-globex", name="Globex Corporation", domain="globex.com"),
        ])
        session.add_all([
            UserORM(
                id="u-1", username="admin", email="admin@acme.com", tenant_id="t-acme", role="admin",
                hashed_password=pwd_context.hash(admin_pw), mfa_enabled=False,
            ),
            UserORM(
                id="u-2", username="john", email="john@acme.com", tenant_id="t-acme", role="user",
                hashed_password=pwd_context.hash(john_pw), mfa_enabled=False,
            ),
            UserORM(
                id="u-3", username="sarah", email="sarah@globex.com", tenant_id="t-globex", role="admin",
                hashed_password=pwd_context.hash(sarah_pw), mfa_enabled=False,
            ),
        ])
        try:
            await session.commit()
        except IntegrityError:
            # Another gunicorn worker inserted the same rows first — that's
            # fine, the data exists either way. Roll back this session's
            # half-applied insert and move on rather than crashing startup.
            await session.rollback()
