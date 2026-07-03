from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from auth.models import User
from auth.dependencies import get_current_active_user
from database import db

router = APIRouter(prefix="/integrations/custom", tags=["Custom Integrations"])

class CustomIntegrationConfig(BaseModel):
    name: str
    url: str
    method: str = "GET"
    auth_type: str = "none" # "none", "api_key", "bearer"
    auth_header: Optional[str] = "Authorization"
    auth_value: Optional[str] = None
    polling_interval: int = 60 # minutes
    enabled: bool = True
    mapping: Dict[str, str] # e.g. {"text": "message", "sender": "user.name"}
    urgency_triggers: List[Dict[str, Any]] = [] # e.g. [{"field": "status", "value": "critical", "boost": 0.2}]

@router.get("")
async def get_custom_integrations(current_user: User = Depends(get_current_active_user)):
    return db.get_custom_integrations(current_user.tenant_id)

@router.post("")
async def add_custom_integration(
    config: CustomIntegrationConfig,
    current_user: User = Depends(get_current_active_user)
):
    integration_id = db.add_custom_integration(current_user.tenant_id, config.dict())
    db.add_audit_log(current_user.id, "add_custom_integration", f"Added custom integration {config.name}")
    return {"id": integration_id, "status": "success"}

@router.patch("/{integration_id}")
async def update_custom_integration(
    integration_id: str,
    config: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    success = db.update_custom_integration(current_user.tenant_id, integration_id, config)
    if not success:
        raise HTTPException(status_code=404, detail="Integration not found")
    db.add_audit_log(current_user.id, "update_custom_integration", f"Updated custom integration {integration_id}")
    return {"status": "success"}

@router.delete("/{integration_id}")
async def delete_custom_integration(
    integration_id: str,
    current_user: User = Depends(get_current_active_user)
):
    success = db.delete_custom_integration(current_user.tenant_id, integration_id)
    if not success:
        raise HTTPException(status_code=404, detail="Integration not found")
    db.add_audit_log(current_user.id, "delete_custom_integration", f"Deleted custom integration {integration_id}")
    return {"status": "success"}
