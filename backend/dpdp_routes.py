"""
DPDP Compliance Routes (India).
Extends the existing pattern with granular per-purpose consent (replacing the 
single toggle), plus all existing DPDP rights.

Granular consent purposes (mapped to Clutsch's actual data uses):
  - "ai_priority_scoring"       — AI analysis of message content for priority ranking
  - "credential_storage"        — Storing OAuth tokens / passwords for connected accounts
  - "marketing_communications"  — Product update and marketing emails
  - "analytics_improvement"     — Usage analytics to improve the product
  - "data_sharing_partners"     — Sharing data with third-party partners (also used by CCPA)
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from typing import List, Optional, Dict, Any
import time
from auth.models import User
from auth.dependencies import get_current_active_user, get_admin_user
from database import db
from limiter import limiter
from compliance_audit import log_compliance_event

router = APIRouter(prefix="/dpdp", tags=["DPDP (India) Compliance"])

# All defined consent purposes for Clutsch
CONSENT_PURPOSES = {
    "ai_priority_scoring": {
        "title": "AI Priority Scoring",
        "description": "Analyze message content to determine priority and urgency scores",
        "required_for_service": True,
        "default": True
    },
    "credential_storage": {
        "title": "Credential Storage",
        "description": "Store OAuth tokens and credentials for connected accounts (email, Slack, etc.)",
        "required_for_service": True,
        "default": True
    },
    "marketing_communications": {
        "title": "Marketing Communications",
        "description": "Send product updates, feature announcements, and promotional content",
        "required_for_service": False,
        "default": False
    },
    "analytics_improvement": {
        "title": "Analytics & Improvement",
        "description": "Collect usage analytics to improve the product experience",
        "required_for_service": True,
        "default": True
    },
    "data_sharing_partners": {
        "title": "Data Sharing with Partners",
        "description": "Share personal data with third-party service partners (also used for CCPA Do Not Sell)",
        "required_for_service": False,
        "default": False
    }
}


# ============================================================================
# PRIVACY NOTICE
# ============================================================================
@router.get("/notice")
@limiter.limit("10/minute")
async def get_privacy_notice(request: Request):
    """
    Retrieve the current privacy notice as required by DPDP.
    """
    return {
        "version": "1.3",
        "last_updated": "2026-07-10",
        "content": (
            "Clutsch collects your messages, emails, and task data to provide "
            "AI-driven prioritization. Your data is encrypted and stored for "
            "30 days by default. Below are the specific purposes for which we "
            "process your data — you can control each independently."
        ),
        "rights": [
            "Right to Access",
            "Right to Correction",
            "Right to Erasure",
            "Right to Nominate",
            "Right to Grievance Redressal"
        ],
        "purposes": CONSENT_PURPOSES
    }


# ============================================================================
# GRANULAR PER-PURPOSE CONSENT
# ============================================================================
@router.post("/consent")
@limiter.limit("10/minute")
async def record_consent(
    request: Request,
    consent: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Record granular per-purpose consent preferences.
    
    Example body:
    {
      "ai_priority_scoring": true,
      "credential_storage": true,
      "marketing_communications": false,
      "analytics_improvement": true,
      "data_sharing_partners": false
    }
    
    Each purpose is independently toggleable. Only the purposes included in the
    request body are updated; omitted purposes keep their current value.
    
    Returns the full set of current preferences after applying the update.
    """
    # Validate that all provided keys are known purposes
    unknown = [k for k in consent if k not in CONSENT_PURPOSES]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown consent purpose(s): {unknown}. Valid: {list(CONSENT_PURPOSES.keys())}"
        )

    # Ensure all values are booleans
    for k, v in consent.items():
        if not isinstance(v, bool):
            raise HTTPException(
                status_code=400,
                detail=f"Consent for '{k}' must be a boolean, got {type(v).__name__}"
            )

    # Get existing preferences
    current_prefs = await db.get_consent_preferences(current_user.id)

    # Apply updates — only the keys sent in the request
    changed = []
    for purpose, value in consent.items():
        old = current_prefs.get(purpose)
        if old != value:
            changed.append(purpose)
        current_prefs[purpose] = value

    # Persist
    await db.set_consent_preferences(current_user.id, current_prefs)

    # Log each changed purpose individually
    for purpose in changed:
        log_compliance_event(
            current_user.id, "DPDP", "CONSENT_CHANGE", "fulfilled",
            details=f"Purpose '{purpose}' set to {current_prefs[purpose]}"
        )

    await db.add_audit_log(
        current_user.id, "RECORD_CONSENT",
        f"Updated {len(changed)} consent purpose(s): {changed}"
    )

    # Build full preferences response: show all purposes with current values
    full_prefs = {}
    for purpose_id, meta in CONSENT_PURPOSES.items():
        full_prefs[purpose_id] = current_prefs.get(purpose_id, meta["default"])

    return {
        "status": "success",
        "message": "Consent preferences updated",
        "updated_purposes": changed,
        "current_preferences": full_prefs
    }


@router.get("/consent")
@limiter.limit("10/minute")
async def get_consent_status(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the current granular consent preferences for the authenticated user.
    Returns all defined purposes with their current value and metadata.
    """
    prefs = await db.get_consent_preferences(current_user.id)

    result = {}
    for purpose_id, meta in CONSENT_PURPOSES.items():
        result[purpose_id] = {
            "title": meta["title"],
            "description": meta["description"],
            "required_for_service": meta["required_for_service"],
            "enabled": prefs.get(purpose_id, meta["default"])
        }

    return {
        "user_id": current_user.id,
        "consent_purposes": result
    }


# ============================================================================
# RIGHT TO NOMINATE
# ============================================================================
@router.post("/nominate")
@limiter.limit("2/minute")
async def nominate_person(
    request: Request,
    nominee: Dict[str, str] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Right to Nominate: Allows users to nominate someone in case of death or incapacity.
    Example body: {"name": "John Doe", "email": "john@example.com", "relationship": "Legal Heir"}
    """
    required = ["name", "email", "relationship"]
    if not all(k in nominee for k in required):
        raise HTTPException(status_code=400, detail=f"Required fields: {required}")

    clean_nominee = {k: nominee[k] for k in required}
    await db.set_nominee(current_user.id, clean_nominee)

    log_compliance_event(current_user.id, "DPDP", "NOMINATE", "fulfilled")
    await db.add_audit_log(current_user.id, "SET_NOMINEE", f"User nominated {clean_nominee['name']}")
    return {"status": "success", "message": "Nominee registered successfully"}


@router.get("/nominee")
@limiter.limit("10/minute")
async def get_nominee(request: Request, current_user: User = Depends(get_current_active_user)):
    """Get the registered nominee for the current user."""
    nominee = await db.get_nominee(current_user.id)
    return {"status": "success", "nominee": nominee}


# ============================================================================
# GRIEVANCE REDRESSAL
# ============================================================================
@router.post("/grievance")
@limiter.limit("2/minute")
async def log_grievance(
    request: Request,
    grievance: Dict[str, str] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """Log a privacy-related concern."""
    if "subject" not in grievance or "description" not in grievance:
        raise HTTPException(status_code=400, detail="Subject and description are required")

    grievance_data = {
        "user_id": current_user.id,
        "tenant_id": current_user.tenant_id,
        "subject": grievance["subject"],
        "description": grievance["description"],
        "status": "open"
    }
    await db.add_grievance(grievance_data)

    log_compliance_event(current_user.id, "DPDP", "GRIEVANCE", "pending",
                         details=grievance['subject'])
    await db.add_audit_log(current_user.id, "LOG_GRIEVANCE", f"User logged a grievance: {grievance['subject']}")
    return {
        "status": "success",
        "message": "Grievance logged successfully. Our Data Protection Officer will review it."
    }


@router.get("/grievances")
@limiter.limit("10/minute")
async def get_my_grievances(request: Request, current_user: User = Depends(get_current_active_user)):
    """Get all grievances logged by the current user."""
    grievances = await db.get_grievances(current_user.id)
    return {"status": "success", "grievances": grievances}


# ============================================================================
# ADMIN: Grievance Redressal
# ============================================================================
@router.get("/admin/grievances")
@limiter.limit("10/minute")
async def admin_get_all_grievances(request: Request, admin: User = Depends(get_admin_user)):
    """Retrieve all grievances for the Data Protection Officer."""
    return {"status": "success", "grievances": await db.get_grievances()}


@router.post("/admin/grievances/{grievance_id}/resolve")
@limiter.limit("10/minute")
async def admin_resolve_grievance(
    request: Request,
    grievance_id: str,
    admin: User = Depends(get_admin_user)
):
    """Mark a grievance as resolved."""
    success = await db.resolve_grievance(grievance_id)
    if not success:
        raise HTTPException(status_code=404, detail="Grievance not found")
    await db.add_audit_log(admin.id, "RESOLVE_GRIEVANCE", f"Admin resolved grievance {grievance_id}")
    return {"status": "success", "message": f"Grievance {grievance_id} marked as resolved."}


# ============================================================================
# ADMIN: View DPDP audit trail  
# ============================================================================
@router.get("/admin/audit")
@limiter.limit("10/minute")
async def dpdp_admin_audit(
    request: Request,
    admin: User = Depends(get_admin_user)
):
    """View DPDP compliance audit log (admin only)."""
    from compliance_audit import get_compliance_audit_log, get_audit_stats
    audit = get_compliance_audit_log(regulation="DPDP")
    stats = get_audit_stats()
    return {
        "status": "success",
        "audit_entries": audit,
        "stats": stats
    }