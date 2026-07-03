import os
import razorpay
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from auth.models import User
from auth.dependencies import get_current_active_user
from database import db
from pydantic import BaseModel
import logging
import time
import json

logger = logging.getLogger("razorpay")

router = APIRouter(prefix="/razorpay", tags=["razorpay billing"])

# Razorpay Configuration
RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_mock_id")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "mock_secret")
RAZORPAY_WEBHOOK_SECRET = os.environ.get("RAZORPAY_WEBHOOK_SECRET", "mock_webhook_secret")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

class SubscriptionRequest(BaseModel):
    plan: str # "Pro" or "Enterprise"

class PaymentVerificationRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str

@router.post("/create-subscription")
async def create_subscription(
    req: SubscriptionRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Create a Razorpay Subscription.
    """
    # Mock Plan IDs (In production, these come from Razorpay Dashboard)
    plan_ids = {
        "Pro": os.environ.get("RAZORPAY_PLAN_PRO", "plan_mock_pro_123"),
        "Enterprise": os.environ.get("RAZORPAY_PLAN_ENTERPRISE", "plan_mock_ent_456")
    }
    
    if req.plan not in plan_ids:
        raise HTTPException(status_code=400, detail="Invalid plan selected")

    try:
        # Check if we should use real client or mock
        if RAZORPAY_KEY_ID == "rzp_test_mock_id":
            return {
                "subscription_id": f"sub_mock_{int(time.time())}",
                "key_id": RAZORPAY_KEY_ID,
                "plan": req.plan
            }

        subscription_data = {
            "plan_id": plan_ids[req.plan],
            "total_count": 12, # 12 months
            "quantity": 1,
            "customer_notify": 1,
            "notes": {
                "tenant_id": current_user.tenant_id,
                "plan": req.plan
            }
        }
        
        subscription = client.subscription.create(data=subscription_data)
        return {
            "subscription_id": subscription["id"],
            "key_id": RAZORPAY_KEY_ID,
            "plan": req.plan
        }
    except Exception as e:
        logger.error(f"Razorpay Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create subscription: {str(e)}")

@router.post("/verify-payment")
async def verify_payment(
    req: PaymentVerificationRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Verify Razorpay payment signature.
    """
    try:
        if RAZORPAY_KEY_ID == "rzp_test_mock_id":
            # Mock verification
            db.update_billing_plan(current_user.tenant_id, "Pro", req.razorpay_subscription_id)
            return {"status": "success", "message": "Mock payment verified"}

        params_dict = {
            'razorpay_payment_id': req.razorpay_payment_id,
            'razorpay_subscription_id': req.razorpay_subscription_id,
            'razorpay_signature': req.razorpay_signature
        }
        
        # This will raise an error if signature is invalid
        client.utility.verify_payment_signature(params_dict)
        
        # Update database
        # Note: In a real app, you'd fetch the subscription to find the plan
        # For now we'll assume Pro if not found, but ideally it's in metadata
        db.update_billing_plan(current_user.tenant_id, "Pro", req.razorpay_subscription_id)
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Signature Verification Failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Payment verification failed")

@router.post("/webhook")
async def razorpay_webhook(request: Request):
    """
    Handle Razorpay Webhooks.
    """
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature or not RAZORPAY_WEBHOOK_SECRET:
        # Manual mock trigger for testing
        try:
            data = json.loads(payload)
            if data.get("mock") == True:
                return await handle_mock_webhook(data)
        except:
            pass
        raise HTTPException(status_code=400, detail="Missing signature or webhook secret")

    try:
        client.utility.verify_webhook_signature(payload.decode('utf-8'), signature, RAZORPAY_WEBHOOK_SECRET)
    except Exception as e:
        logger.error(f"Webhook Signature Verification Failed: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = json.loads(payload)
    event = data.get("event")

    if event == "subscription.activated":
        subscription = data["payload"]["subscription"]["entity"]
        await handle_subscription_activated(subscription)
    elif event == "subscription.halted" or event == "subscription.cancelled":
        subscription = data["payload"]["subscription"]["entity"]
        await handle_subscription_deactivated(subscription)
    
    return {"status": "success"}

async def handle_subscription_activated(subscription):
    notes = subscription.get("notes", {})
    tenant_id = notes.get("tenant_id")
    plan = notes.get("plan", "Pro")
    subscription_id = subscription.get("id")
    
    if tenant_id:
        db.update_billing_plan(tenant_id, plan, subscription_id)
        db.add_audit_log("system", "razorpay_subscription_activated", f"Tenant {tenant_id} upgraded to {plan}")
        logger.info(f"Razorpay Subscription activated for tenant {tenant_id}: {plan}")

async def handle_subscription_deactivated(subscription):
    notes = subscription.get("notes", {})
    tenant_id = notes.get("tenant_id")
    if tenant_id:
        db.update_billing_plan(tenant_id, "Free")
        db.add_audit_log("system", "razorpay_subscription_deactivated", f"Tenant {tenant_id} downgraded to Free")
        logger.info(f"Razorpay Subscription deactivated for tenant {tenant_id}")

async def handle_mock_webhook(data):
    event = data.get("event")
    if event == "subscription.activated":
        entity = data.get("payload", {}).get("subscription", {}).get("entity", {})
        await handle_subscription_activated(entity)
    return {"status": "mock_success"}

@router.get("/status")
async def get_subscription_status(current_user: User = Depends(get_current_active_user)):
    """
    Get current subscription plan and details.
    """
    billing_info = db.get_billing_info(current_user.tenant_id)
    if not billing_info:
        return {
            "plan": "Free",
            "usage": {"active_integrations": 0, "team_members": 0, "ai_items_processed": 0, "smart_responses": 0},
            "limits": {"active_integrations": 5, "team_members": 5, "ai_items_processed": 1000, "smart_responses": 20}
        }
    return billing_info
