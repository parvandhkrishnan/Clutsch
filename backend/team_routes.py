from fastapi import APIRouter, Depends, HTTPException, Body, Request
from typing import List, Optional, Dict, Any
from auth.models import User, get_users_db
from auth.dependencies import get_current_active_user
from database import db
from pydantic import BaseModel
from realtime_routes import notify_delegation
import time

router = APIRouter(prefix="/team", tags=["team collaboration"])

class DelegationRequest(BaseModel):
    item_id: str
    to_user_id: str
    note: Optional[str] = ""

class PresenceUpdate(BaseModel):
    action: str = "viewing" # viewing, acting, replying

@router.get("/members")
async def get_team_members(current_user: User = Depends(get_current_active_user)):
    """Get list of members in the same tenant."""
    users = get_users_db()
    team_members = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            # Mock availability and workload for now as seen in frontend
            "availability": "Available", 
            "workload": len([d for d in db.delegations.values() if d["assigned_to"] == u.id]),
            "avatar": u.username[:2].upper()
        }
        for u in users if u.tenant_id == current_user.tenant_id
    ]
    return team_members

@router.post("/delegate")
async def delegate_item(
    req: DelegationRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Delegate an item to another team member."""
    # Verify the recipient belongs to the same tenant
    users = get_users_db()
    recipient = next((u for u in users if u.id == req.to_user_id and u.tenant_id == current_user.tenant_id), None)
    
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found in your team")
    
    success = db.delegate_item(
        item_id=req.item_id,
        tenant_id=current_user.tenant_id,
        to_user_id=req.to_user_id,
        assigned_by=current_user.id,
        note=req.note
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Item not found or access denied")
    
    db.add_audit_log(current_user.id, "delegate_item", f"Delegated item {req.item_id} to {req.to_user_id}")
    
    # Notify real-time
    await notify_delegation(current_user.tenant_id, req.to_user_id, req.item_id, current_user.username)
    
    return {"status": "success", "message": f"Item delegated to {recipient.username}"}

@router.get("/items/{item_id}/presence")
async def get_item_presence(item_id: str, current_user: User = Depends(get_current_active_user)):
    """Get current active users on an item."""
    presence_data = db.get_presence(item_id)
    # Map user_id to username for better UI
    users = {u.id: u.username for u in get_users_db() if u.tenant_id == current_user.tenant_id}
    
    result = []
    for user_id, data in presence_data.items():
        if user_id in users:
            result.append({
                "user_id": user_id,
                "username": users[user_id],
                "action": data["action"],
                "timestamp": data["timestamp"]
            })
    return result

@router.post("/items/{item_id}/presence")
async def update_item_presence(
    item_id: str,
    update: PresenceUpdate,
    current_user: User = Depends(get_current_active_user)
):
    """Update current user's presence on an item."""
    db.update_presence(item_id, current_user.id, update.action)
    return {"status": "success"}

@router.get("/feed")
async def get_team_feed(current_user: User = Depends(get_current_active_user)):
    """
    Get the shared team feed. 
    Returns high-priority items with delegation and presence info.
    """
    # This would normally call scoring_service, but we can reuse the logic in main.py
    # For now, let's just return items with extra team metadata
    from services import scoring_service, archived_items, snoozed_items
    
    items = db.get_items(current_user.tenant_id)
    contact_priorities = db.get_contact_priorities(current_user.tenant_id)
    tenant_archived = archived_items.get(current_user.tenant_id, set())
    tenant_snoozed = snoozed_items.get(current_user.tenant_id, {})
    
    scored_items = scoring_service.process_items(
        current_user.tenant_id,
        items, 
        tenant_archived, 
        tenant_snoozed, 
        contact_priorities
    )
    
    # Enrich with delegation and presence
    for item in scored_items:
        item["delegation"] = db.get_delegation(item["id"])
        item["presence"] = await get_item_presence(item["id"], current_user)
        
    # Sort by priority score
    scored_items.sort(key=lambda x: x.get("priorityScore", 0), reverse=True)
    
    return scored_items
