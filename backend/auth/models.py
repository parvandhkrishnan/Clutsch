import os
from pydantic import BaseModel
from typing import Optional, List
from passlib.context import CryptContext

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

# Mock Database
tenants_db = [
    Tenant(id="t-acme", name="Acme Corp", domain="acme.com"),
    Tenant(id="t-globex", name="Globex Corporation", domain="globex.com")
]

_users_db: Optional[List[User]] = None

def get_users_db() -> List[User]:
    global _users_db
    if _users_db is None:
        admin_pw = os.environ.get("ADMIN_PASSWORD")
        john_pw = os.environ.get("JOHN_PASSWORD")
        sarah_pw = os.environ.get("SARAH_PASSWORD")
        
        if not admin_pw or not john_pw or not sarah_pw:
            raise RuntimeError("CRITICAL: Missing required password environment variables (ADMIN_PASSWORD, JOHN_PASSWORD, SARAH_PASSWORD)")

        _users_db = [
            User(
                id="u-1",
                username="admin",
                email="admin@acme.com",
                tenant_id="t-acme",
                role="admin",
                hashed_password=pwd_context.hash(admin_pw),
                mfa_enabled=False  # MFA is opt-in; users enable via /auth/mfa/setup
            ),
            User(
                id="u-2",
                username="john",
                email="john@acme.com",
                tenant_id="t-acme",
                role="user",
                hashed_password=pwd_context.hash(john_pw),
                mfa_enabled=False
            ),
            User(
                id="u-3",
                username="sarah",
                email="sarah@globex.com",
                tenant_id="t-globex",
                role="admin",
                hashed_password=pwd_context.hash(sarah_pw),
                mfa_enabled=False
            )
        ]
    return _users_db

def get_user_by_username(username: str) -> Optional[User]:
    for user in get_users_db():
        if user.username == username:
            return user
    return None

def get_user_by_email(email: str) -> Optional[User]:
    for user in get_users_db():
        if user.email == email:
            return user
    return None

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def delete_user(user_id: str):
    global _users_db
    users = get_users_db()
    _users_db = [user for user in users if user.id != user_id]

def get_tenant_by_id(tenant_id: str) -> Optional[Tenant]:
    for tenant in tenants_db:
        if tenant.id == tenant_id:
            return tenant
    return None

def add_user(username: str, email: str, password: str, tenant_id: str = "t-acme", role: str = "user", hashed_password: str = None) -> User:
    """Add a new user to the in-memory database."""
    global _users_db
    users = get_users_db()
    # Check for duplicates
    for u in users:
        if u.username == username:
            return None
    new_id = f"u-{len(users) + 1}"
    new_user = User(
        id=new_id,
        username=username,
        email=email,
        tenant_id=tenant_id,
        role=role,
        hashed_password=hashed_password or pwd_context.hash(password),
        mfa_enabled=False
    )
    users.append(new_user)
    _users_db = users
    return new_user
