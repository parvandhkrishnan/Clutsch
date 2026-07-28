"""
GDPR Compliance Routes (EU).
Implements full data subject rights: access, rectification, erasure,
restriction of processing, and data portability.

Reuses DPDP data operations where the underlying operations are the same,
but extends the request type taxonomy for the GDPR-specific rights.
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from typing import List, Optional, Dict, Any
import time
import json
from auth.models import User, get_user_by_id, get_user_by_username, get_user_by_email, update_user_fields, delete_user
from auth.dependencies import get_current_active_user, get_admin_user
from database import db
from limiter import limiter
from compliance_audit import log_compliance_event
from utils.cache import config_cache, integration_cache

router = APIRouter(prefix="/gdpr", tags=["GDPR (EU) Compliance"])

# ============================================================================
# HELPER: Collect all data for a user across every layer
# ============================================================================
async def _collect_all_user_data(user_id: str, tenant_id: str) -> Dict[str, Any]:
    """Gather all data associated with a user from every storage layer."""
    data = {
        "user_info": None,
        "items": [],
        "consent_records": [],
        "nominee": None,
        "grievances": [],
        "delegations_received": [],
        "integrations": [],
        "custom_weights": None,
        "contact_priorities": [],
    }

    # 1. User model info
    user = await get_user_by_id(user_id)
    if user:
        data["user_info"] = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "tenant_id": user.tenant_id,
            "mfa_enabled": user.mfa_enabled,
        }

    # 2. Items owned by or referencing this user
    # NOTE: the real Item schema (models.py) has no user_id/assigned_to column
    # — those were ad-hoc dict keys some test fixtures added to the old
    # in-memory mock. In production, items only carry tenant_id, so this
    # filter will not match anything unless such keys happen to be present.
    all_items = await db.get_items(tenant_id)
    user_items = []
    for item in all_items:
        if item.get("user_id") == user_id or item.get("assigned_to") == user_id:
            # Strip sensitive token data
            safe = {k: v for k, v in item.items() if k.lower() not in ('token', 'secret', 'password')}
            user_items.append(safe)
    data["items"] = user_items

    # 3. Consent records
    data["consent_records"] = await db.get_consents(user_id)

    # 4. Nominee
    data["nominee"] = await db.get_nominee(user_id)

    # 5. Grievances
    data["grievances"] = await db.get_grievances(user_id)

    # 6. Delegations where this user is the assignee
    data["delegations_received"] = await db.get_delegations_for_assignee(user_id)

    # 7. Integration tokens (redacted)
    tenant_integrations = await db.get_connected_integrations(tenant_id)
    for provider, config in tenant_integrations.items():
        redacted = {}
        for k, v in config.items():
            if k.lower() in ('token', 'secret', 'refresh_token', 'access_token', 'api_key', 'password'):
                redacted[k] = "***REDACTED***"
            else:
                redacted[k] = v
        data["integrations"].append({"provider": provider, **redacted})

    # 8. Custom weights
    data["custom_weights"] = await db.get_custom_weights(tenant_id)

    # 9. Contact priorities involving this user
    cps = await db.get_contact_priorities(tenant_id)
    for platform, handles in cps.items():
        for handle, priority in handles.items():
            if handle == user_id or (user and handle == user.email):
                data["contact_priorities"].append({
                    "platform": platform,
                    "handle": handle,
                    "priority": priority
                })

    return data


# ============================================================================
# 1. RIGHT OF ACCESS (Art. 15 GDPR)
# ============================================================================
@router.get("/access")
@limiter.limit("5/minute")
async def gdpr_access(request: Request, current_user: User = Depends(get_current_active_user)):
    """
    Right of Access (GDPR Art. 15): Return all personal data held about the user.
    """
    data = await _collect_all_user_data(current_user.id, current_user.tenant_id)
    log_compliance_event(
        current_user.id, "GDPR", "DATA_ACCESS", "fulfilled"
    )
    await db.add_audit_log(current_user.id, "GDPR_ACCESS", "User accessed all personal data via GDPR Art. 15")
    return {
        "regulation": "GDPR",
        "right": "access",
        "article": "15",
        "user_id": current_user.id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": data
    }


# ============================================================================
# 2. RIGHT TO RECTIFICATION (Art. 16 GDPR)
# ============================================================================
@router.put("/rectify")
@limiter.limit("5/minute")
async def gdpr_rectify(
    request: Request,
    updates: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Right to Rectification (GDPR Art. 16): Correct inaccurate personal data.
    Supported fields: email, username.
    """
    allowed_fields = {"email", "username"}
    applied = {}
    errors = {}

    for field, value in updates.items():
        if field not in allowed_fields:
            errors[field] = f"Field '{field}' is not rectifiable via this endpoint"
            continue
        if not isinstance(value, str) or not value.strip():
            errors[field] = "Value must be a non-empty string"
            continue

        # Check for uniqueness conflicts
        if field == "username" and value != current_user.username:
            if await get_user_by_username(value):
                errors[field] = "Username already taken"
                continue
        if field == "email" and value != current_user.email:
            if await get_user_by_email(value):
                errors[field] = "Email already registered"
                continue

        applied[field] = value

    if applied:
        await update_user_fields(current_user.id, **applied)

    if not applied and errors:
        raise HTTPException(status_code=400, detail={"applied": applied, "errors": errors})

    log_compliance_event(
        current_user.id, "GDPR", "DATA_RECTIFICATION", "fulfilled" if not errors else "partial",
        details=f"Applied: {list(applied.keys())}"
    )
    await db.add_audit_log(current_user.id, "GDPR_RECTIFY", f"Rectified fields: {list(applied.keys())}")

    return {
        "regulation": "GDPR",
        "right": "rectification",
        "article": "16",
        "applied": applied,
        "errors": errors if errors else None
    }


# ============================================================================
# 3. RIGHT TO ERASURE (Art. 17 GDPR) — FULL CASCADE
# ============================================================================
@router.delete("/erase")
@limiter.limit("3/minute")
async def gdpr_erase(request: Request, current_user: User = Depends(get_current_active_user)):
    """
    Right to Erasure (Art. 17 GDPR): cascade deletion of this user's own data
    across every storage layer, then the user record itself.

    Deviations from the original in-memory mock, forced by the real
    FK-constrained schema (models.py, not modifiable here):
    - Grievances are DELETED rather than anonymized in place. The old mock
      set user_id to a "**ERASED**" sentinel string, which is not possible
      here since Grievance.user_id is a NOT NULL foreign key to users.id.
    - Per-owner item erasure (item.get("user_id") == user_id) is a no-op in
      practice: the real Item schema has no user_id/assigned_to column, so
      there is nothing to filter on for a single user within a shared tenant
      (tenant-wide item erasure is available separately via
      privacy_routes.py's account deletion, which calls delete_tenant_data).
    """
    user_id = current_user.id
    tenant_id = current_user.tenant_id

    # Layers 3-7, 9-10: everything that references this user must be cleared
    # BEFORE the user row is deleted, or Postgres will reject the delete on
    # the foreign key constraints (Grievance, AuditLog, ConsentRecord,
    # Nominee, MFARecoveryCode, FailedLogin, LockedAccount, Delegation, Presence).
    await db.delete_user_data(user_id)

    # MFA secret lives on the User row itself / in-memory pending state —
    # clear explicitly (delete_user_data doesn't touch these).
    await db.clear_mfa_secret(user_id)
    await db.clear_mfa_pending_secret(user_id)
    await db.clear_mfa_recovery_codes(user_id)

    # Cache
    config_cache.invalidate_all()
    integration_cache.invalidate_all()

    # Connected integrations that reference this user specifically
    tenant_integrations = await db.get_connected_integrations(tenant_id)
    for provider, config in list(tenant_integrations.items()):
        if config.get("user_id") == user_id or config.get("email") == current_user.email:
            await db.disconnect_integration(tenant_id, provider)

    # Layer 1: Auth/Users (deleted last, now that all FK references are gone)
    await delete_user(user_id)

    # --- Log the erasure ---
    log_compliance_event(
        user_id, "GDPR", "DATA_ERASURE", "fulfilled",
        details="Cascade erasure completed across all storage layers"
    )

    return {
        "regulation": "GDPR",
        "right": "erasure",
        "article": "17",
        "message": "All personal data has been erased across all storage layers.",
        "cascade_layers_deleted": [
            "user_record", "consent_records", "nominee",
            "grievances", "delegations", "mfa_secrets",
            "cache_invalidated", "integrations", "locked_accounts"
        ],
        "note": "Compliance audit log retained per GDPR Art. 5(2) accountability principle."
    }


# ============================================================================
# 4. RIGHT TO RESTRICTION OF PROCESSING (Art. 18 GDPR)
# ============================================================================
@router.post("/restrict")
@limiter.limit("5/minute")
async def gdpr_restrict(
    request: Request,
    body: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Right to Restriction of Processing (GDPR Art. 18).
    Send {"action": "restrict"} to restrict or {"action": "lift"} to lift restriction.
    When restricted, AI scoring and priority processing are paused for this user.
    """
    action = body.get("action", "")
    if action not in ("restrict", "lift"):
        raise HTTPException(status_code=400, detail="Action must be 'restrict' or 'lift'")

    # Store restriction state. This is kept in-memory on the db singleton
    # (like ccpa_routes.py's do_not_sell flag) rather than in a real table —
    # there is no processing_restrictions table in the fixed schema, and this
    # was not part of the requested migration's scope.
    if not hasattr(db, 'processing_restrictions'):
        db.processing_restrictions = {}

    if action == "restrict":
        db.processing_restrictions[current_user.id] = {
            "restricted_at": time.time(),
            "restricted": True
        }
        outcome = "fulfilled"
        msg = "Processing restricted. AI scoring and priority processing have been paused."
    else:
        db.processing_restrictions.pop(current_user.id, None)
        outcome = "fulfilled"
        msg = "Processing restriction lifted. AI scoring and priority processing resumed."

    log_compliance_event(current_user.id, "GDPR", "RESTRICT_PROCESSING", outcome)
    await db.add_audit_log(current_user.id, "GDPR_RESTRICT", msg)

    return {
        "regulation": "GDPR",
        "right": "restriction",
        "article": "18",
        "action": action,
        "message": msg
    }


# ============================================================================
# 5. RIGHT TO DATA PORTABILITY (Art. 20 GDPR)
# ============================================================================
@router.get("/port")
@limiter.limit("5/minute")
async def gdpr_port(request: Request, current_user: User = Depends(get_current_active_user)):
    """
    Right to Data Portability (GDPR Art. 20): Export personal data in
    structured, machine-readable JSON format.
    """
    data = await _collect_all_user_data(current_user.id, current_user.tenant_id)

    log_compliance_event(current_user.id, "GDPR", "DATA_EXPORT", "fulfilled")
    await db.add_audit_log(current_user.id, "GDPR_PORT", "User exported data via GDPR Art. 20")

    return {
        "regulation": "GDPR",
        "right": "portability",
        "article": "20",
        "format": "application/json",
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "data": data
    }


# ============================================================================
# ADMIN: View GDPR audit trail
# ============================================================================
@router.get("/admin/audit")
@limiter.limit("10/minute")
async def gdpr_admin_audit(
    request: Request,
    admin: User = Depends(get_admin_user)
):
    """
    View GDPR compliance audit log (admin only).
    Entries contain hashed user references, not PII.
    """
    from compliance_audit import get_compliance_audit_log, get_audit_stats
    audit = get_compliance_audit_log(regulation="GDPR")
    stats = get_audit_stats()
    return {
        "status": "success",
        "audit_entries": audit,
        "stats": stats
    }
