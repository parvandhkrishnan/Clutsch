from fastapi import APIRouter, Depends, HTTPException, Request
from auth.dependencies import get_current_active_user
from auth.models import User, delete_user, get_tenant_by_id
from database import db
from typing import Dict, Any
from slowapi import Limiter
from slowapi.util import get_remote_address
import json

router = APIRouter(prefix="/privacy", tags=["privacy"])
limiter = Limiter(key_func=get_remote_address)

@router.get("/export")
@limiter.limit("1/minute")
async def export_data(request: Request, current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id

    # Gather data
    user_data = current_user.dict(exclude={"hashed_password"})
    tenant_data = await get_tenant_by_id(tenant_id)
    items = await db.get_items(tenant_id)

    # Archived/snoozed state now lives on each item's own columns
    archived = [i["id"] for i in items if i.get("is_archived")]
    snoozed_serialized = {
        i["id"]: i["snoozed_until"].isoformat() if hasattr(i["snoozed_until"], "isoformat") else i["snoozed_until"]
        for i in items
        if i.get("is_snoozed") and i.get("snoozed_until")
    }

    integrations = await db.get_connected_integrations(tenant_id)

    export_payload = {
        "user": user_data,
        "tenant": tenant_data.dict() if tenant_data else None,
        "items": items,
        "archived_item_ids": archived,
        "snoozed_items": snoozed_serialized,
        "connected_integrations": list(integrations.keys()) # We don't export tokens for security, just providers
    }

    # Audit log
    await db.add_audit_log(current_user.id, "DATA_EXPORT", f"Exported data for tenant {tenant_id}")

    return export_payload

@router.delete("/account")
@limiter.limit("1/minute")
async def delete_account(request: Request, current_user: User = Depends(get_current_active_user)):
    user_id = current_user.id
    tenant_id = current_user.tenant_id

    # Audit log first while we have user context
    await db.add_audit_log(user_id, "ACCOUNT_DELETION", f"Deleted account and personal data for user {user_id}")

    # 1. Delete this user's own data (consent, grievances, MFA, audit trail,
    #    delegations, presence). NOTE: deliberately NOT delete_tenant_data —
    #    that erases every user's items/integrations/settings for the whole
    #    tenant, which would wipe out teammates' data when only one person
    #    asks to delete their own account. Items/integrations/priorities are
    #    tenant-owned (shared team data), not this individual's to erase.
    await db.delete_user_data(user_id)

    # 2. Delete user from auth database
    await delete_user(user_id)

    return {"status": "success", "message": "Your account and personal data have been permanently deleted."}

@router.get("/audit-logs")
@limiter.limit("10/minute")
async def get_my_audit_logs(request: Request, current_user: User = Depends(get_current_active_user)):
    # Optional: allow users to see their own privacy-related audit logs
    logs = await db.get_audit_logs(current_user.id)
    return {"logs": logs}
