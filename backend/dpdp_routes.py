from fastapi import APIRouter, Depends, HTTPException, Body, Request
from typing import List, Optional, Dict, Any
import time
from auth.models import User
from auth.dependencies import get_current_active_user, get_admin_user
from database import db
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/dpdp", tags=["DPDP (India) Compliance"])
limiter = Limiter(key_func=get_remote_address)

class ConsentRecord(Dict):
    version: str
    purpose: str
    timestamp: float

@router.get("/notice")
@limiter.limit("5/minute")
async def get_privacy_notice(request: Request):
    """
    Retrieve the current privacy notice as required by DPDP.
    """
    return {
        "version": "1.2",
        "last_updated": "2023-10-27",
        "content": "PriorityFlow collects your email and messages to provide AI-driven prioritization. Your data is encrypted and stored for 30 days by default.",
        "rights": [
            "Right to Access",
            "Right to Correction",
            "Right to Erasure",
            "Right to Nominate",
            "Right to Grievance Redressal"
        ]
    }

@router.post("/consent")
@limiter.limit("5/minute")
async def record_consent(
    request: Request,
    consent: Dict[str, str] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Record a new version of verifiable consent.
    Example body: {"version": "1.1", "purpose": "AI prioritization and data aggregation"}
    """
    if "version" not in consent or "purpose" not in consent:
        raise HTTPException(status_code=400, detail="Version and purpose are required")
    
    # Data Minimization: only store version and purpose
    clean_consent = {
        "version": consent["version"],
        "purpose": consent["purpose"]
    }
    
    db.record_consent(current_user.id, clean_consent)
    db.add_audit_log(current_user.id, "RECORD_CONSENT", f"User recorded consent version {consent['version']}")
    return {"status": "success", "message": "Consent recorded successfully"}

@router.get("/consent")
@limiter.limit("10/minute")
async def get_consent_history(request: Request, current_user: User = Depends(get_current_active_user)):
    """
    Retrieve the consent history for the current user.
    """
    consents = db.get_consents(current_user.id)
    return {"user_id": current_user.id, "consent_history": consents}

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
    
    # Data Minimization: only store required fields
    clean_nominee = {k: nominee[k] for k in required}
    
    db.set_nominee(current_user.id, clean_nominee)
    db.add_audit_log(current_user.id, "SET_NOMINEE", f"User nominated {clean_nominee['name']}")
    return {"status": "success", "message": "Nominee registered successfully"}

@router.get("/nominee")
@limiter.limit("10/minute")
async def get_nominee(request: Request, current_user: User = Depends(get_current_active_user)):
    """
    Get the registered nominee for the current user.
    """
    nominee = db.get_nominee(current_user.id)
    if not nominee:
        return {"status": "success", "nominee": None}
    return {"status": "success", "nominee": nominee}

@router.post("/grievance")
@limiter.limit("2/minute")
async def log_grievance(
    request: Request,
    grievance: Dict[str, str] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Grievance Redressal: Log a privacy-related concern.
    Example body: {"subject": "Data Access", "description": "I cannot see my full export history."}
    """
    if "subject" not in grievance or "description" not in grievance:
        raise HTTPException(status_code=400, detail="Subject and description are required")
    
    grievance_data = {
        "user_id": current_user.id,
        "tenant_id": current_user.tenant_id,
        "subject": grievance["subject"],
        "description": grievance["description"],
        "status": "open"
    }
    db.add_grievance(grievance_data)
    db.add_audit_log(current_user.id, "LOG_GRIEVANCE", f"User logged a grievance: {grievance['subject']}")
    return {"status": "success", "message": "Grievance logged successfully. Our Data Protection Officer will review it."}

@router.get("/grievances")
@limiter.limit("10/minute")
async def get_my_grievances(request: Request, current_user: User = Depends(get_current_active_user)):
    """
    Get all grievances logged by the current user.
    """
    grievances = db.get_grievances(current_user.id)
    return {"status": "success", "grievances": grievances}

# Admin Endpoints for Grievance Redressal
@router.get("/admin/grievances")
@limiter.limit("10/minute")
async def admin_get_all_grievances(request: Request, admin: User = Depends(get_admin_user)):
    """
    Retrieve all grievances for the Data Protection Officer.
    """
    return {"status": "success", "grievances": db.get_grievances()}

@router.post("/admin/grievances/{grievance_id}/resolve")
@limiter.limit("10/minute")
async def admin_resolve_grievance(
    request: Request,
    grievance_id: str,
    admin: User = Depends(get_admin_user)
):
    """
    Mark a grievance as resolved.
    """
    with db._lock:
        for g in db.grievance_logs:
            if g.get("id") == grievance_id:
                g["status"] = "resolved"
                db.add_audit_log(admin.id, "RESOLVE_GRIEVANCE", f"Admin resolved grievance {grievance_id}")
                return {"status": "success", "message": f"Grievance {grievance_id} marked as resolved."}
    
    raise HTTPException(status_code=404, detail="Grievance not found")
