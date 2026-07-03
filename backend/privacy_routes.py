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
    tenant_data = get_tenant_by_id(tenant_id)
    items = db.get_items(tenant_id)
    
    # Shared state from db
    archived = list(db.archived_items.get(tenant_id, set()))
    snoozed = db.snoozed_items.get(tenant_id, {})
    # Convert datetime to string for JSON serialization
    snoozed_serialized = {k: v.isoformat() if hasattr(v, "isoformat") else v for k, v in snoozed.items()}
    
    integrations = db.connected_integrations.get(tenant_id, {})
    
    export_payload = {
        "user": user_data,
        "tenant": tenant_data.dict() if tenant_data else None,
        "items": items,
        "archived_item_ids": archived,
        "snoozed_items": snoozed_serialized,
        "connected_integrations": list(integrations.keys()) # We don't export tokens for security, just providers
    }
    
    # Audit log
    db.add_audit_log(current_user.id, "DATA_EXPORT", f"Exported data for tenant {tenant_id}")
    
    return export_payload

@router.delete("/account")
@limiter.limit("1/minute")
async def delete_account(request: Request, current_user: User = Depends(get_current_active_user)):
    user_id = current_user.id
    tenant_id = current_user.tenant_id
    
    # Audit log first while we have user context
    db.add_audit_log(user_id, "ACCOUNT_DELETION", f"Deleted account and all data for tenant {tenant_id}")

    # 1. Delete items from MockDatabase
    db.delete_tenant_data(tenant_id)
    
    # 2. Clear archived and snoozed state
    if tenant_id in db.archived_items:
        del db.archived_items[tenant_id]
    if tenant_id in db.snoozed_items:
        del db.snoozed_items[tenant_id]
        
    # 3. Clear integrations
    if tenant_id in db.connected_integrations:
        del db.connected_integrations[tenant_id]
        
    # 4. Delete user from auth database
    delete_user(user_id)
    
    return {"status": "success", "message": "Account and all associated data have been permanently deleted."}

@router.get("/audit-logs")
@limiter.limit("10/minute")
async def get_my_audit_logs(request: Request, current_user: User = Depends(get_current_active_user)):
    # Optional: allow users to see their own privacy-related audit logs
    logs = db.get_audit_logs(current_user.id)
    return {"logs": logs}
