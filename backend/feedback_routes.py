from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from auth.dependencies import get_current_active_user
from auth.models import User
from feedback_service import feedback_service
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/feedback", tags=["feedback"])
limiter = Limiter(key_func=get_remote_address)

class PriorityFeedbackRequest(BaseModel):
    item_id: str
    feedback_type: str # 'agree', 'correction'
    suggested_tier: Optional[str] = None # 'urgent', 'high', 'medium', 'low'

@router.post("/priority")
@limiter.limit("30/minute")
async def submit_priority_feedback(
    request: Request,
    feedback: PriorityFeedbackRequest,
    current_user: User = Depends(get_current_active_user)
):
    if feedback.feedback_type not in ["agree", "correction"]:
        raise HTTPException(status_code=400, detail="Invalid feedback type. Must be 'agree' or 'correction'.")
    
    if feedback.feedback_type == "correction" and not feedback.suggested_tier:
        raise HTTPException(status_code=400, detail="suggested_tier is required for corrections.")

    if feedback.suggested_tier and feedback.suggested_tier not in ["urgent", "high", "medium", "low"]:
        raise HTTPException(status_code=400, detail="Invalid suggested tier.")

    success = await feedback_service.process_feedback(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        item_id=feedback.item_id,
        feedback_type=feedback.feedback_type,
        suggested_tier=feedback.suggested_tier
    )

    if not success:
        raise HTTPException(status_code=404, detail="Item not found or feedback processing failed.")

    return {"status": "success", "message": "Feedback processed and weights updated."}
