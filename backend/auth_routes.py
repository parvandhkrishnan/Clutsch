from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from auth.models import get_user_by_username, Token, get_users_db, get_user_by_email, User, add_user
from auth.jwt_handler import create_access_token, create_refresh_token, decode_refresh_token
from auth.dependencies import get_admin_user, get_current_active_user
from database import db
from pydantic import BaseModel
from limiter import limiter
from async_crypto import verify_password, hash_password
import os
import time
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["authentication"])

MAX_LOGIN_ATTEMPTS = int(os.environ.get("MAX_LOGIN_ATTEMPTS", 5))
LOCKOUT_DURATION_MINUTES = int(os.environ.get("LOCKOUT_DURATION_MINUTES", 15))

class SSOLoginRequest(BaseModel):
    email: str
    provider: str # e.g. "okta", "azure", "google"

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str
    name: str = ""

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/register", response_model=Token)
@limiter.limit("3/minute")
async def register(request: Request, reg_req: RegisterRequest):
    # Validate inputs
    if not reg_req.username or len(reg_req.username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if not reg_req.email or "@" not in reg_req.email:
        raise HTTPException(status_code=400, detail="Valid email required")
    if not reg_req.password or len(reg_req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    # Check if user already exists
    existing = get_user_by_username(reg_req.username)
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")
    existing_email = get_user_by_email(reg_req.email)
    if existing_email:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Create the user
    hashed = await hash_password(reg_req.password)
    user = add_user(
        username=reg_req.username,
        email=reg_req.email,
        password=reg_req.password,
        hashed_password=hashed,
        tenant_id="t-acme",
        role="user"
    )
    if not user:
        raise HTTPException(status_code=500, detail="Failed to create user")
    
    access_token = create_access_token(
        data={"user_id": user.id, "tenant_id": user.tenant_id, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"user_id": user.id}
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user = get_user_by_username(form_data.username)
    
    if user:
        # Check if locked
        lockout_expiry = db.locked_accounts.get(user.id)
        if lockout_expiry and time.time() < lockout_expiry:
            wait_minutes = int((lockout_expiry - time.time()) / 60) + 1
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account temporarily locked due to multiple failed login attempts. Try again in {wait_minutes} minutes.",
            )

    if not user or not await verify_password(form_data.password, user.hashed_password):
        if user:
            # Record failed attempt
            now = time.time()
            if user.id not in db.failed_login_attempts:
                db.failed_login_attempts[user.id] = []
            db.failed_login_attempts[user.id].append(now)
            
            # Filter attempts within lockout window
            cutoff = now - (LOCKOUT_DURATION_MINUTES * 60)
            db.failed_login_attempts[user.id] = [t for t in db.failed_login_attempts[user.id] if t > cutoff]
            
            if len(db.failed_login_attempts[user.id]) >= MAX_LOGIN_ATTEMPTS:
                db.locked_accounts[user.id] = now + (LOCKOUT_DURATION_MINUTES * 60)
                db.add_audit_log(user.id, "account_lockout", f"Account locked for {LOCKOUT_DURATION_MINUTES} minutes")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Success: clear failed attempts
    if user.id in db.failed_login_attempts:
        del db.failed_login_attempts[user.id]
    if user.id in db.locked_accounts:
        del db.locked_accounts[user.id]
    
    # If MFA is enabled, return a partial token (MFA session) instead of the final token
    if user.mfa_enabled:
        mfa_session_token = create_access_token(
            data={"user_id": user.id, "tenant_id": user.tenant_id, "role": user.role, "mfa_pending": True},
            expires_delta=timedelta(minutes=5)
        )
        return {
            "mfa_required": True,
            "mfa_session_token": mfa_session_token,
            "user_id": user.id,
            "message": "MFA code required. Call /auth/mfa/login to complete authentication."
        }
    
    access_token = create_access_token(
        data={"user_id": user.id, "tenant_id": user.tenant_id, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"user_id": user.id}
    )
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/admin/unlock/{user_id}")
async def admin_unlock_user(request: Request, user_id: str, admin: User = Depends(get_admin_user)):
    if user_id in db.locked_accounts:
        del db.locked_accounts[user_id]
    if user_id in db.failed_login_attempts:
        del db.failed_login_attempts[user_id]
    db.add_audit_log(admin.id, "admin_unlock_user", f"Admin unlocked user {user_id}")
    return {"status": "success", "message": f"User {user_id} unlocked"}

@router.post("/refresh", response_model=Token)
@limiter.limit("5/minute")
async def refresh(request: Request, refresh_req: RefreshRequest):
    payload = decode_refresh_token(refresh_req.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    user_id = payload.get("user_id")
    # Find user
    user = None
    for u in get_users_db():
        if u.id == user_id:
            user = u
            break
    
    if not user:
         raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    access_token = create_access_token(
        data={"user_id": user.id, "tenant_id": user.tenant_id, "role": user.role}
    )
    # We could also rotate the refresh token here
    new_refresh_token = create_refresh_token(
        data={"user_id": user.id}
    )
    
    return {
        "access_token": access_token, 
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/sso/login", response_model=Token)
@limiter.limit("5/minute")
async def sso_login(request: Request, sso_req: SSOLoginRequest):
    # Simulation of SSO handshake
    user = get_user_by_email(sso_req.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found for this SSO identity"
        )
    
    print(f"Verified {sso_req.email} via {sso_req.provider}")
    access_token = create_access_token(
        data={"user_id": user.id, "tenant_id": user.tenant_id, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"user_id": user.id}
    )
    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.get("/me")
async def read_users_me(current_user = Depends()):
    # This will be handled by the main app's dependency
    pass
