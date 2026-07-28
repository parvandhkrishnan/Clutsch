"""MFA routes for TOTP setup, verification, and recovery codes."""
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from auth.models import User, get_user_by_id, set_mfa_enabled
from auth.dependencies import get_current_active_user
from auth.jwt_handler import create_access_token, create_refresh_token
from database import db
from limiter import limiter
from mfa import (
    generate_totp_secret, get_totp_uri, verify_totp,
    generate_recovery_codes, hash_recovery_code
)
from typing import Dict, List

router = APIRouter(prefix="/auth/mfa", tags=["MFA"])


@router.post("/setup")
@limiter.limit("5/minute")
async def mfa_setup(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """Generate a TOTP secret and return the provisioning URI for QR code setup."""
    secret = generate_totp_secret()
    # Store the pending secret (not yet verified)
    await db.set_mfa_pending_secret(current_user.id, secret)
    uri = get_totp_uri(secret, current_user.email)
    return {
        "secret": secret,
        "uri": uri,
        "message": "Scan this QR code with your authenticator app, then call /verify to confirm."
    }


@router.post("/verify")
@limiter.limit("10/minute")
async def mfa_verify(
    request: Request,
    code: str = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user)
):
    """Verify a TOTP code to enable MFA for the user."""
    pending_secret = await db.get_mfa_pending_secret(current_user.id)
    if not pending_secret:
        raise HTTPException(status_code=400, detail="No pending MFA setup. Call /setup first.")

    if not verify_totp(pending_secret, code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code. Try again.")

    # Enable MFA and store the secret
    await db.set_mfa_secret(current_user.id, pending_secret)
    await db.clear_mfa_pending_secret(current_user.id)

    # Generate recovery codes
    recovery_codes = generate_recovery_codes()
    hashed_codes = [hash_recovery_code(c) for c in recovery_codes]
    await db.set_mfa_recovery_codes(current_user.id, hashed_codes)

    # Update user model
    await set_mfa_enabled(current_user.id, True)

    await db.add_audit_log(current_user.id, "MFA_ENABLED", "User enabled TOTP MFA")

    return {
        "status": "success",
        "message": "MFA has been enabled successfully.",
        "recovery_codes": recovery_codes,
        "warning": "Save these recovery codes securely. Each can only be used once."
    }


@router.post("/login")
@limiter.limit("10/minute")
async def mfa_login(
    request: Request,
    user_id: str = Body(...),
    code: str = Body(...)
):
    """
    Complete MFA step during login.
    Called after successful password verification when the user has MFA enabled.
    Returns a JWT token on success.
    """
    user = await get_user_by_id(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.mfa_enabled:
        raise HTTPException(status_code=400, detail="MFA is not enabled for this user")

    # Check recovery codes first
    mfa_secret = await db.get_mfa_secret(user.id)
    recovery_codes = await db.get_mfa_recovery_codes(user.id)

    if mfa_secret and verify_totp(mfa_secret, code):
        # Valid TOTP code
        pass
    elif recovery_codes:
        # Check if it's a recovery code
        from mfa import hash_recovery_code
        hashed = hash_recovery_code(code)
        if hashed in recovery_codes:
            # Consume the recovery code (remove it)
            recovery_codes.remove(hashed)
            await db.set_mfa_recovery_codes(user.id, recovery_codes)
            await db.add_audit_log(user.id, "MFA_RECOVERY_USED", "User used a recovery code to log in")
        else:
            raise HTTPException(status_code=401, detail="Invalid TOTP code or recovery code")
    else:
        raise HTTPException(status_code=401, detail="Invalid TOTP code or recovery code")

    # Generate final token
    access_token = create_access_token(
        data={"user_id": user.id, "tenant_id": user.tenant_id, "role": user.role}
    )
    refresh_token = create_refresh_token(
        data={"user_id": user.id}
    )

    await db.add_audit_log(user.id, "MFA_LOGIN_SUCCESS", "User completed MFA and logged in")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/disable")
@limiter.limit("3/minute")
async def mfa_disable(
    request: Request,
    code: str = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user)
):
    """Disable MFA for the current user (requires valid TOTP code)."""
    mfa_secret = await db.get_mfa_secret(current_user.id)
    if not mfa_secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled")

    if not verify_totp(mfa_secret, code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    await db.clear_mfa_secret(current_user.id)
    await db.clear_mfa_recovery_codes(current_user.id)

    await set_mfa_enabled(current_user.id, False)

    await db.add_audit_log(current_user.id, "MFA_DISABLED", "User disabled MFA")

    return {"status": "success", "message": "MFA has been disabled."}


@router.get("/status")
async def mfa_status(
    current_user: User = Depends(get_current_active_user)
):
    """Check whether MFA is enabled for the current user."""
    return {
        "mfa_enabled": current_user.mfa_enabled,
        "user_id": current_user.id
    }
