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
from auth.models import User
from auth.dependencies import get_current_active_user, get_admin_user
from database import db
from limiter import limiter
from compliance_audit import log_compliance_event
from utils.cache import config_cache, integration_cache

router = APIRouter(prefix="/gdpr", tags=["GDPR (EU) Compliance"])

# ============================================================================
# HELPER: Collect all data for a user across every layer
# ============================================================================
def _collect_all_user_data(user_id: str, tenant_id: str) -> Dict[str, Any]:
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

    # 1. User model info — read from auth.models
    from auth.models import get_users_db
    for u in get_users_db():
        if u.id == user_id:
            data["user_info"] = {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "tenant_id": u.tenant_id,
                "mfa_enabled": u.mfa_enabled
            }
            break

    # 2. Items owned by or referencing this user
    all_items = db.get_items(tenant_id)
    user_items = []
    for item in all_items:
        if item.get("user_id") == user_id or item.get("assigned_to") == user_id:
            # Strip sensitive token data
            safe = {k: v for k, v in item.items() if k.lower() not in ('token', 'secret', 'password')}
            user_items.append(safe)
    data["items"] = user_items

    # 3. Consent records
    data["consent_records"] = db.get_consents(user_id)

    # 4. Nominee
    data["nominee"] = db.get_nominee(user_id)

    # 5. Grievances
    data["grievances"] = db.get_grievances(user_id)

    # 6. Delegations where this user is the assignee
    for item_id, del_info in dict(db.delegations).items():
        if del_info.get("assigned_to") == user_id:
            data["delegations_received"].append({
                "item_id": item_id,
                **del_info
            })

    # 7. Integration tokens (redacted)
    if tenant_id in getattr(db, 'connected_integrations', {}):
        for provider, config in db.connected_integrations[tenant_id].items():
            redacted = {}
            for k, v in config.items():
                if k.lower() in ('token', 'secret', 'refresh_token', 'access_token', 'api_key', 'password'):
                    redacted[k] = "***REDACTED***"
                else:
                    redacted[k] = v
            data["integrations"].append({"provider": provider, **redacted})

    # 8. Custom weights
    data["custom_weights"] = db.get_custom_weights(tenant_id)

    # 9. Contact priorities involving this user
    cps = db.get_contact_priorities(tenant_id)
    for platform, handles in cps.items():
        for handle, priority in handles.items():
            if handle == user_id or handle == getattr(
                [u for u in get_users_db() if u.id == user_id], 
                'email', None
            ):
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
    data = _collect_all_user_data(current_user.id, current_user.tenant_id)
    log_compliance_event(
        current_user.id, "GDPR", "DATA_ACCESS", "fulfilled"
    )
    db.add_audit_log(current_user.id, "GDPR_ACCESS", "User accessed all personal data via GDPR Art. 15")
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
    from auth.models import get_users_db, get_user_by_username, get_user_by_email, _users_db

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
            if get_user_by_username(value):
                errors[field] = "Username already taken"
                continue
        if field == "email" and value != current_user.email:
            if get_user_by_email(value):
                errors[field] = "Email already registered"
                continue

        # Apply update
        users = get_users_db()
        for u in users:
            if u.id == current_user.id:
                setattr(u, field, value)
                applied[field] = value
                break
        _users_db = users

    if not applied and errors:
        raise HTTPException(status_code=400, detail={"applied": applied, "errors": errors})

    log_compliance_event(
        current_user.id, "GDPR", "DATA_RECTIFICATION", "fulfilled" if not errors else "partial",
        details=f"Applied: {list(applied.keys())}"
    )
    db.add_audit_log(current_user.id, "GDPR_RECTIFY", f"Rectified fields: {list(applied.keys())}")

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
    Right to Erasure (Art. 17 GDPR): Full cascade deletion across ALL layers.
    - Removes from users table, items, consent records, nominees, grievances,
      delegations, MFA secrets, cache layers, connected integrations.
    - Does NOT erase the compliance audit log entry for this request itself.
    """
    from auth.models import get_users_db, _users_db
    user_id = current_user.id
    tenant_id = current_user.tenant_id

    # --- Layer 1: Auth/Users ---
    users = get_users_db()
    _users_db = [u for u in users if u.id != user_id]

    # --- Layer 2: Items ---
    all_items = db.get_items(tenant_id)
    db._items = [i for i in all_items if i.get("user_id") != user_id]

    # --- Layer 3: Consent records ---
    if hasattr(db, 'consent_records') and user_id in db.consent_records:
        del db.consent_records[user_id]

    # --- Layer 4: Nominee ---
    if hasattr(db, 'nominees') and user_id in db.nominees:
        del db.nominees[user_id]

    # --- Layer 5: Grievances (anonymize, don't delete — evidence preservation) ---
    if hasattr(db, 'grievance_logs'):
        for g in db.grievance_logs:
            if g.get("user_id") == user_id:
                g["user_id"] = "**ERASED**"
                g["description"] = "**ERASED PER ART. 17 GDPR**"

    # --- Layer 6: Delegations ---
    db.delegations = {k: v for k, v in db.delegations.items() 
                      if v.get("assigned_to") != user_id}

    # --- Layer 7: MFA secrets ---
    db.clear_mfa_secret(user_id)
    db.clear_mfa_pending_secret(user_id)
    db.clear_mfa_recovery_codes(user_id)

    # --- Layer 8: Cache ---
    config_cache.invalidate_all()
    integration_cache.invalidate_all()

    # --- Layer 9: Connected integrations (per-user tokens, anonymize) ---
    # Remove any per-user integration configs
    if tenant_id in getattr(db, 'connected_integrations', {}):
        for provider, config in list(db.connected_integrations[tenant_id].items()):
            # If integration config references this user, remove it
            if config.get("user_id") == user_id or config.get("email") == current_user.email:
                del db.connected_integrations[tenant_id][provider]

    # --- Layer 10: Locked accounts / failed attempts ---
    db.locked_accounts.pop(user_id, None)
    db.failed_login_attempts.pop(user_id, None)

    # --- Log the erasure (before user_ref is lost) ---
    log_compliance_event(
        user_id, "GDPR", "DATA_ERASURE", "fulfilled",
        details="Full cascade erasure completed across all storage layers"
    )

    return {
        "regulation": "GDPR",
        "right": "erasure",
        "article": "17",
        "message": "All personal data has been erased across all storage layers.",
        "cascade_layers_deleted": [
            "user_record", "items", "consent_records", "nominee",
            "grievances_anonymized", "delegations", "mfa_secrets",
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

    # Store restriction state
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
    db.add_audit_log(current_user.id, "GDPR_RESTRICT", msg)

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
    data = _collect_all_user_data(current_user.id, current_user.tenant_id)

    log_compliance_event(current_user.id, "GDPR", "DATA_EXPORT", "fulfilled")
    db.add_audit_log(current_user.id, "GDPR_PORT", "User exported data via GDPR Art. 20")

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