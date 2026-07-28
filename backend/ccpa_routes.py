"""
CCPA/CPRA Compliance Routes (California, US).
Implements:
- "Do Not Sell or Share My Info" standalone toggle
- Data access/export request
- Deletion request
- Opt-out confirmation

Per CCPA requirements, the "Do Not Sell or Share" control must be:
- A standalone toggle (NOT bundled into general consent)
- Easily accessible (within 2 clicks from Settings)
- Off by default (opt-out model — selling/sharing is opt-in pre-checked)
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Request
from typing import Optional, Dict, Any
import time
from auth.models import User
from auth.dependencies import get_current_active_user, get_admin_user
from database import db
from limiter import limiter
from compliance_audit import log_compliance_event

router = APIRouter(prefix="/ccpa", tags=["CCPA/CPRA (California) Compliance"])

# ============================================================================
# 1. CCPA PRIVACY NOTICE
# ============================================================================
@router.get("/notice")
@limiter.limit("10/minute")
async def ccpa_notice(request: Request):
    """
    CCPA Privacy Notice — describes categories of personal info collected,
    purposes, and rights under California law.
    """
    return {
        "regulation": "CCPA/CPRA",
        "version": "1.0",
        "last_updated": "2026-07-10",
        "notice": [
            {
                "category": "Identifiers",
                "collected": True,
                "examples": ["Name", "Email address", "IP address"],
                "purpose": "Account management, service delivery",
                "sold_or_shared": False
            },
            {
                "category": "Commercial information",
                "collected": True,
                "examples": ["Subscription tier", "Payment history"],
                "purpose": "Billing, plan management",
                "sold_or_shared": False
            },
            {
                "category": "Internet/electronic activity",
                "collected": True,
                "examples": ["Messages synced via integrations", "Dashboard interactions"],
                "purpose": "AI priority scoring, service personalization",
                "sold_or_shared": False
            },
            {
                "category": "Professional/employment information",
                "collected": False,
                "examples": [],
                "purpose": "N/A",
                "sold_or_shared": False
            },
            {
                "category": "Inferences drawn from above",
                "collected": True,
                "examples": ["Priority score", "Productivity patterns"],
                "purpose": "AI-driven priority ranking",
                "sold_or_shared": False
            }
        ],
        "rights": [
            "Right to Know (access)",
            "Right to Delete",
            "Right to Opt-Out of Sale/Sharing",
            "Right to Correct",
            "Right to Limit Use of Sensitive Personal Information",
            "Right to Non-Discrimination"
        ],
        "note": "Clutsch does NOT sell or share personal data with third parties. "
                "The 'Do Not Sell or Share' toggle below is provided as a CCPA-compliant "
                "control and defaults to off (prohibiting any future sale/sharing)."
    }


# ============================================================================
# 2. "DO NOT SELL OR SHARE MY INFO" — Standalone Toggle
# ============================================================================
@router.get("/do-not-sell")
@limiter.limit("10/minute")
async def get_do_not_sell_status(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the current "Do Not Sell or Share My Info" preference.
    Off by default (CCPA opt-out model — the user must choose to opt out).
    """
    if not hasattr(db, 'do_not_sell'):
        db.do_not_sell = {}

    preference = db.do_not_sell.get(current_user.id, {
        "do_not_sell_or_share": True,  # True = don't sell (opt-out default)
        "updated_at": None
    })

    return {
        "regulation": "CCPA/CPRA",
        "right": "opt_out",
        "status": "opted_out" if preference["do_not_sell_or_share"] else "selling_allowed",
        "meaning": {
            "opted_out": "Your data will NOT be sold or shared with any third party.",
            "selling_allowed": "Your data MAY be sold or shared with third parties."
        },
        "preference": preference
    }


@router.post("/do-not-sell")
@limiter.limit("5/minute")
async def set_do_not_sell(
    request: Request,
    preference: Dict[str, bool] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Set "Do Not Sell or Share My Info" preference.
    
    Send {"do_not_sell_or_share": true} to opt out of ALL sale/sharing.
    Send {"do_not_sell_or_share": false} to allow sale/sharing.
    
    Per CCPA: this must be a standalone control, not bundled into general consent.
    Off by default (true = customer is opted out until they say otherwise).
    """
    if "do_not_sell_or_share" not in preference:
        raise HTTPException(
            status_code=400,
            detail="Must provide 'do_not_sell_or_share' boolean field"
        )

    if not hasattr(db, 'do_not_sell'):
        db.do_not_sell = {}

    value = bool(preference["do_not_sell_or_share"])
    db.do_not_sell[current_user.id] = {
        "do_not_sell_or_share": value,
        "updated_at": time.time()
    }

    outcome = "fulfilled"
    status_text = "opted_out" if value else "selling_allowed"

    log_compliance_event(
        current_user.id, "CCPA", "DO_NOT_SELL", outcome,
        details=f"Set do_not_sell_or_share={value}"
    )
    await db.add_audit_log(
        current_user.id, "CCPA_DO_NOT_SELL",
        f"CCPA Do Not Sell/Share set to {value}"
    )

    return {
        "regulation": "CCPA/CPRA",
        "right": "opt_out",
        "action": "set_preference",
        "status": status_text,
        "message": "Your 'Do Not Sell or Share My Info' preference has been saved.",
        "note": "Clutsch does not currently sell or share personal data with third parties. "
                "This control ensures that remains the case for your account regardless of future changes."
    }


# ============================================================================
# 3. CCPA RIGHT TO KNOW (ACCESS)
# ============================================================================
@router.get("/access")
@limiter.limit("5/minute")
async def ccpa_access(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    CCPA Right to Know: Categories and specific pieces of personal info collected.
    """
    from gdpr_routes import _collect_all_user_data
    data = await _collect_all_user_data(current_user.id, current_user.tenant_id)

    # CCPA requires categories of sources and business purpose
    categories = {
        "identifiers": {
            "collected": bool(data.get("user_info")),
            "sources": ["User registration form", "SSO provider"],
            "business_purpose": "Account creation and authentication"
        },
        "commercial_info": {
            "collected": bool(data.get("user_info")),
            "sources": ["Subscription billing"],
            "business_purpose": "Plan management and payment processing"
        },
        "electronic_activity": {
            "collected": len(data.get("items", [])) > 0,
            "sources": ["Connected integrations (email, Slack, etc.)"],
            "business_purpose": "AI priority scoring and dashboard display"
        }
    }

    log_compliance_event(current_user.id, "CCPA", "DATA_ACCESS", "fulfilled")
    await db.add_audit_log(current_user.id, "CCPA_ACCESS", "User accessed data via CCPA Right to Know")

    return {
        "regulation": "CCPA/CPRA",
        "right": "right_to_know",
        "categories": categories,
        "specific_pieces": {
            "user_info": data.get("user_info"),
            "consent_history": data.get("consent_records"),
            "items_count": len(data.get("items", []))
        },
        "third_parties": [],
        "note": "Clutsch does not sell or share personal data with third parties."
    }


# ============================================================================
# 4. CCPA RIGHT TO DELETE
# ============================================================================
@router.delete("/delete")
@limiter.limit("3/minute")
async def ccpa_delete(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    """
    CCPA Right to Delete: Full cascade deletion.
    Reuses the GDPR erasure logic since the underlying data operations are identical.
    """
    from gdpr_routes import gdpr_erase
    # We reuse the full cascade from GDPR; the audit log distinguishes the regulation.
    result = await gdpr_erase(request, current_user)
    # Overwrite the regulation tag in the response
    result["regulation"] = "CCPA/CPRA"
    result["right"] = "right_to_delete"
    return result


# ============================================================================
# 5. CCPA RIGHT TO CORRECT
# ============================================================================
@router.put("/correct")
@limiter.limit("5/minute")
async def ccpa_correct(
    request: Request,
    updates: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    CCPA Right to Correct: Correct inaccurate personal information.
    Reuses GDPR rectification logic.
    """
    from gdpr_routes import gdpr_rectify
    result = await gdpr_rectify(request, updates, current_user)
    result["regulation"] = "CCPA/CPRA"
    result["right"] = "right_to_correct"
    return result


# ============================================================================
# ADMIN: View CCPA audit trail
# ============================================================================
@router.get("/admin/audit")
@limiter.limit("10/minute")
async def ccpa_admin_audit(
    request: Request,
    admin: User = Depends(get_admin_user)
):
    """View CCPA compliance audit log (admin only)."""
    from compliance_audit import get_compliance_audit_log, get_audit_stats
    audit = get_compliance_audit_log(regulation="CCPA")
    stats = get_audit_stats()
    return {
        "status": "success",
        "audit_entries": audit,
        "stats": stats
    }