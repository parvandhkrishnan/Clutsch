from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any
from auth.dependencies import get_current_active_user
from auth.models import User
from database import db
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/preferences", tags=["preferences"])
limiter = Limiter(key_func=get_remote_address)

class ContactPriorityRequest(BaseModel):
    platform: str
    handle: str
    priority: str # 'high', 'medium', 'low'

@router.get("/contacts")
@limiter.limit("20/minute")
async def get_contact_priorities(request: Request, current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id
    return db.get_contact_priorities(tenant_id)

@router.post("/contacts")
@limiter.limit("20/minute")
async def set_contact_priority(
    request: Request,
    priority_data: ContactPriorityRequest,
    current_user: User = Depends(get_current_active_user)
):
    tenant_id = current_user.tenant_id
    if priority_data.priority.lower() not in ["high", "medium", "low"]:
        raise HTTPException(status_code=400, detail="Invalid priority level. Must be 'high', 'medium', or 'low'.")
    
    db.set_contact_priority(
        tenant_id, 
        priority_data.platform.lower(), 
        priority_data.handle, 
        priority_data.priority.lower()
    )
    db.add_audit_log(current_user.id, "set_contact_priority", f"Set {priority_data.platform}/{priority_data.handle} to {priority_data.priority}")
    return {"status": "success", "message": f"Priority set for {priority_data.handle}"}

@router.delete("/contacts/{platform}/{handle}")
@limiter.limit("20/minute")
async def delete_contact_priority(
    request: Request,
    platform: str,
    handle: str,
    current_user: User = Depends(get_current_active_user)
):
    tenant_id = current_user.tenant_id
    db.delete_contact_priority(tenant_id, platform.lower(), handle)
    db.add_audit_log(current_user.id, "delete_contact_priority", f"Deleted priority for {platform}/{handle}")
    return {"status": "success", "message": f"Priority deleted for {handle}"}

class CustomWeightsRequest(BaseModel):
    urgency: float
    importance: float
    sender_rank: float
    deadline: float

class SemanticWeightsRequest(BaseModel):
    weights: Dict[str, float]

@router.get("/weights")
@limiter.limit("20/minute")
async def get_custom_weights(request: Request, current_user: User = Depends(get_current_active_user)):
    return db.get_custom_weights(current_user.tenant_id)

@router.post("/weights")
@limiter.limit("20/minute")
async def set_custom_weights(
    request: Request,
    weights: CustomWeightsRequest, 
    current_user: User = Depends(get_current_active_user)
):
    db.set_custom_weights(current_user.tenant_id, weights.model_dump())
    db.add_audit_log(current_user.id, "set_custom_weights", "Updated custom priority weights")
    return {"status": "success"}

@router.get("/semantics")
@limiter.limit("20/minute")
async def get_semantic_weights(request: Request, current_user: User = Depends(get_current_active_user)):
    return db.get_semantic_weights(current_user.tenant_id)

@router.post("/semantics")
@limiter.limit("20/minute")
async def set_semantic_weights(
    request: Request,
    weights: SemanticWeightsRequest, 
    current_user: User = Depends(get_current_active_user)
):
    db.set_semantic_weights(current_user.tenant_id, weights.weights)
    db.add_audit_log(current_user.id, "set_semantic_weights", "Updated semantic weighting rules")
    return {"status": "success"}

class EntityPriorityRequest(BaseModel):
    entity_id: str
    priority: str # 'high', 'medium', 'low'

@router.get("/projects")
@limiter.limit("20/minute")
async def get_project_priorities(request: Request, current_user: User = Depends(get_current_active_user)):
    return db.get_project_priorities(current_user.tenant_id)

@router.post("/projects")
@limiter.limit("20/minute")
async def set_project_priority(
    request: Request,
    priority_data: EntityPriorityRequest,
    current_user: User = Depends(get_current_active_user)
):
    db.set_project_priority(current_user.tenant_id, priority_data.entity_id, priority_data.priority)
    db.add_audit_log(current_user.id, "set_project_priority", f"Set project {priority_data.entity_id} to {priority_data.priority}")
    return {"status": "success"}

@router.get("/clients")
@limiter.limit("20/minute")
async def get_client_priorities(request: Request, current_user: User = Depends(get_current_active_user)):
    return db.get_client_priorities(current_user.tenant_id)

@router.post("/clients")
@limiter.limit("20/minute")
async def set_client_priority(
    request: Request,
    priority_data: EntityPriorityRequest,
    current_user: User = Depends(get_current_active_user)
):
    db.set_client_priority(current_user.tenant_id, priority_data.entity_id, priority_data.priority)
    db.add_audit_log(current_user.id, "set_client_priority", f"Set client {priority_data.entity_id} to {priority_data.priority}")
    return {"status": "success"}
