from fastapi import APIRouter, Depends, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from auth.models import User
from auth.dependencies import get_current_active_user
from database import db

router = APIRouter(prefix="/workflows", tags=["Workflows"])

class WorkflowAction(BaseModel):
    type: str # "archive", "snooze", "delegate"
    params: Dict[str, Any] = {} # e.g. {"hours": 24} or {"to_user_id": "u-2"}

class WorkflowCondition(BaseModel):
    field: str # "priorityScore", "source", "sender_handle", "priorityTier"
    operator: str # "gt", "lt", "eq", "contains"
    value: Any

class WorkflowCreate(BaseModel):
    name: str
    enabled: bool = True
    conditions: List[WorkflowCondition]
    actions: List[WorkflowAction]

@router.get("")
async def get_workflows(current_user: User = Depends(get_current_active_user)):
    return db.get_workflows(current_user.tenant_id)

@router.post("")
async def add_workflow(
    workflow: WorkflowCreate,
    current_user: User = Depends(get_current_active_user)
):
    workflow_id = db.add_workflow(current_user.tenant_id, workflow.dict())
    db.add_audit_log(current_user.id, "add_workflow", f"Added workflow {workflow.name}")
    return {"id": workflow_id, "status": "success"}

@router.patch("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    workflow: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_active_user)
):
    success = db.update_workflow(current_user.tenant_id, workflow_id, workflow)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.add_audit_log(current_user.id, "update_workflow", f"Updated workflow {workflow_id}")
    return {"status": "success"}

@router.delete("/{workflow_id}")
async def delete_workflow(
    workflow_id: str,
    current_user: User = Depends(get_current_active_user)
):
    success = db.delete_workflow(current_user.tenant_id, workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.add_audit_log(current_user.id, "delete_workflow", f"Deleted workflow {workflow_id}")
    return {"status": "success"}
