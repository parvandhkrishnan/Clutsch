import os
import asyncio
import datetime
import uuid
import logging
import time
import json
from typing import List, Optional, Dict, Set, Any
from pydantic import BaseModel
from fastapi import FastAPI, Body, HTTPException, Query, Depends, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Load environment variables from .env file
load_dotenv()

from prioritizer import PriorityEngine
from ai_analyzer import AIAnalyzer
from scoring_service import ScoringService
from security import encrypt_secret, decrypt_secret, sanitize_pii
from adapters.gmail import GmailAdapter
from adapters.slack import SlackAdapter
from adapters.whatsapp import WhatsAppAdapter
from adapters.outlook import OutlookAdapter
from adapters.teams import TeamsAdapter
from adapters.jira import JiraAdapter
from utils.cache import config_cache, integration_cache
from worker import background_worker
from utils.retries import async_retry_with_backoff

# Auth Imports
from auth_routes import router as auth_router
from privacy_routes import router as privacy_router
from preference_routes import router as preference_router
from dpdp_routes import router as dpdp_router
from auth.models import User, Token, get_user_by_username, verify_password, tenants_db
from auth.dependencies import get_current_active_user, get_admin_user
from database import db

# Configure Structured Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("priorityflow")

# Initialize Rate Limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="PriorityFlow API", version="0.2.0")
app.state.limiter = limiter
if os.environ.get("ENFORCE_HTTPS") == "true":
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allow_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background task for DPDP retention policy
async def periodic_retention_policy():
    while True:
        # Enforce retention policy every 24 hours
        db.enforce_retention_policy(days=30)
        await asyncio.sleep(24 * 60 * 60)

def validate_secrets():
    required_secrets = [
        "JWT_SECRET_KEY",
        "ENCRYPTION_KEY",
        "ADMIN_PASSWORD",
        "JOHN_PASSWORD",
        "SARAH_PASSWORD"
    ]
    missing = [s for s in required_secrets if not os.environ.get(s)]
    if missing:
        error_msg = f"CRITICAL: Missing required environment variables: {', '.join(missing)}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

@app.on_event("startup")
async def startup_event():
    # Validate secrets
    validate_secrets()
    # Start retention policy task
    asyncio.create_task(periodic_retention_policy())

# Custom Middleware for Structured Monitoring & Anomaly Detection
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Extract client info
    client_host = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    
    # Anomaly detection: track repeated failures (simulated with a simple dict for now)
    # In production, use Redis or similar.
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    status_code = response.status_code
    
    log_data = {
        "request_id": request_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "method": method,
        "path": path,
        "status_code": status_code,
        "latency_ms": process_time * 1000,
        "client": client_host
    }
    
    # Structured log
    logger.info(json.dumps(log_data))
    
    # Anomaly Logging
    if status_code == 401 or status_code == 403:
        logger.warning(f"SECURITY_ANOMALY: Unauthorized access attempt to {path} from {client_host}")
    elif status_code == 429:
        logger.warning(f"SECURITY_ANOMALY: Rate limit exceeded for {path} from {client_host}")
    
    return response

# Include Routers
app.include_router(auth_router)
app.include_router(privacy_router)
app.include_router(preference_router)
app.include_router(dpdp_router)
from integration_routes import router as integration_router
app.include_router(integration_router)
from team_routes import router as team_router
app.include_router(team_router)
from analytics_routes import router as analytics_router
app.include_router(analytics_router)
from razorpay_routes import router as razorpay_router
app.include_router(razorpay_router)
from custom_integration_routes import router as custom_integration_router
app.include_router(custom_integration_router)
from realtime_routes import router as realtime_router
app.include_router(realtime_router)
from workflow_routes import router as workflow_router
app.include_router(workflow_router)
from feedback_routes import router as feedback_router
app.include_router(feedback_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/ready")
async def readiness_check():
    checks = {}
    
    # Check database connectivity
    try:
        db.get_items("t-acme")  # quick ping
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
    
    # Check background worker
    checks["background_worker"] = "ok" if background_worker._thread.is_alive() else "down"
    
    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503
    
    return JSONResponse(
        content={"status": "ready" if all_ok else "not_ready", "checks": checks},
        status_code=status_code
    )

# Data Models
class ConnectRequest(BaseModel):
    token: str

class ItemCreate(BaseModel):
    text: str
    source: str = "manual"
    deadline: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.post("/items")
@limiter.limit("20/minute")
async def create_item(request: Request, item: ItemCreate, current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id
    item_id = str(uuid.uuid4())
    item_data = {
        "id": item_id,
        "tenant_id": tenant_id,
        "text": item.text,
        "source": item.source,
        "deadline": item.deadline,
        "metadata": item.metadata or {},
        "timestamp": time.time()
    }
    db.add_item(item_data)
    await notify_new_items(tenant_id, 1)
    return item_data

# Scoring Service Setup
from services import scoring_service, archived_items, snoozed_items

def _verify_item_ownership(item_id: str, tenant_id: str):
    items = db.get_items(tenant_id)
    if not any(i["id"] == item_id for i in items):
        # Log anomaly: attempt to access data from another tenant
        logger.error(f"TENANT_LEAK_ATTEMPT: Attempt to access item {item_id} across tenant boundaries")
        raise HTTPException(status_code=403, detail="Not authorized to access this item")

@app.get("/")
async def root():
    return {"message": "PriorityFlow Backend API is running"}

@app.get("/items")
@limiter.limit("100/minute")
async def get_items(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    tenant_id = current_user.tenant_id
    items = db.get_items(tenant_id)
    
    # Filter out archived and snoozed
    now = datetime.datetime.now()
    tenant_archived = archived_items.get(tenant_id, set())
    tenant_snoozed = snoozed_items.get(tenant_id, {})
    
    active_items = []
    for item in items:
        if item["id"] in tenant_archived:
            continue
        if item["id"] in tenant_snoozed and tenant_snoozed[item["id"]] > now:
            continue
        active_items.append(item)
    
    return active_items

@app.get("/priorities/feed")
@limiter.limit("50/minute")
async def get_priority_feed(
    request: Request,
    tier: Optional[str] = Query(None, pattern="^(urgent|high|medium|low)$"),
    current_user: User = Depends(get_current_active_user)
):
    tenant_id = current_user.tenant_id
    items = db.get_items(tenant_id)
    
    contact_priorities = db.get_contact_priorities(tenant_id)
    tenant_archived = archived_items.get(tenant_id, set())
    tenant_snoozed = snoozed_items.get(tenant_id, {})
    
    scored_items = scoring_service.process_items(
        tenant_id,
        items, 
        tenant_archived, 
        tenant_snoozed, 
        contact_priorities
    )
    
    if tier:
        scored_items = [i for i in scored_items if i["priorityTier"] == tier]
    
    return scored_items

@app.post("/items/{item_id}/archive")
@limiter.limit("30/minute")
async def archive_item(request: Request, item_id: str, current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id
    _verify_item_ownership(item_id, tenant_id)
    if tenant_id not in archived_items:
        archived_items[tenant_id] = set()
    archived_items[tenant_id].add(item_id)
    
    # Audit log
    db.add_audit_log(current_user.id, "archive_item", f"Archived item {item_id}")
    return {"status": "success", "message": f"Item {item_id} archived"}

@app.post("/items/{item_id}/snooze")
@limiter.limit("30/minute")
async def snooze_item(
    request: Request,
    item_id: str, 
    hours: int = Body(..., embed=True),
    current_user: User = Depends(get_current_active_user)
):
    tenant_id = current_user.tenant_id
    _verify_item_ownership(item_id, tenant_id)
    if tenant_id not in snoozed_items:
        snoozed_items[tenant_id] = {}
    
    until = datetime.datetime.now() + datetime.timedelta(hours=hours)
    snoozed_items[tenant_id][item_id] = until
    
    # Audit log
    db.add_audit_log(current_user.id, "snooze_item", f"Snoozed item {item_id} for {hours}h")
    return {"status": "success", "message": f"Item {item_id} snoozed until {until}"}

@app.post("/items/{item_id}/unsnooze")
@limiter.limit("30/minute")
async def unsnooze_item(request: Request, item_id: str, current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id
    _verify_item_ownership(item_id, tenant_id)
    if tenant_id in snoozed_items and item_id in snoozed_items[tenant_id]:
        del snoozed_items[tenant_id][item_id]
        # Audit log
        db.add_audit_log(current_user.id, "unsnooze_item", f"Unsnoozed item {item_id}")
    return {"status": "success", "message": f"Item {item_id} unsnoozed"}

@app.get("/stats")
@limiter.limit("20/minute")
async def get_stats(request: Request, current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id
    now = datetime.datetime.now()
    tenant_archived = archived_items.get(tenant_id, set())
    tenant_snoozed = snoozed_items.get(tenant_id, {})
    active_snoozed = [id for id, until in tenant_snoozed.items() if until > now]
    return {
        "archived_count": len(tenant_archived),
        "snoozed_count": len(active_snoozed)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
