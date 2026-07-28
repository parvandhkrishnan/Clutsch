import html
import re
import os
import asyncio
import datetime
import uuid
import logging
import time
import json
from typing import List, Optional, Dict, Set, Any
from contextlib import asynccontextmanager
from pydantic import BaseModel
from fastapi import FastAPI, Body, HTTPException, Query, Depends, BackgroundTasks, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Structured logging
from log_config import setup_logging, LogContext, JSONFormatter
setup_logging()
logger = logging.getLogger("priorityflow")

# Strips HTML tags from user input to prevent XSS
def sanitize_text(text: str) -> str:
    if not text:
        return text
    return html.escape(text.strip())

# Rate Limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from limiter import limiter

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
from auth.models import User, Token, seed_initial_data
from auth.dependencies import get_current_active_user, get_admin_user
from database import db
from db_engine import init_db

# Configure Structured Logging — now done via log_config.setup_logging()
logger = logging.getLogger("priorityflow")

# Initialize Rate Limiter (shared instance from limiter.py)
app = FastAPI(
    title="PriorityFlow API",
    version="0.2.0",
    lifespan="auto"
)
app.state.limiter = limiter
if os.environ.get("ENFORCE_HTTPS") == "true":
    app.add_middleware(HTTPSRedirectMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' https://checkout.razorpay.com 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'"
    return response

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
        await db.enforce_retention_policy(days=30)
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: validate secrets, ensure schema exists, seed demo data, start background tasks
    validate_secrets()
    await init_db()
    await seed_initial_data()
    asyncio.create_task(periodic_retention_policy())
    logger.info(json.dumps({"event": "app_startup", "status": "started"}))
    yield
    # Shutdown: wait for background tasks to finish
    logger.info(json.dumps({"event": "app_shutdown", "status": "shutting_down"}))
    background_worker.stop()
    logger.info(json.dumps({"event": "app_shutdown", "status": "completed"}))

app.router.lifespan_context = lifespan

# Custom Middleware for Structured Monitoring & Anomaly Detection
@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Set request_id in the log context for this request
    LogContext.set_request_id(request_id)
    
    # Extract client info
    client_host = request.client.host if request.client else "unknown"
    method = request.method
    path = request.url.path
    
    # Add request_id to response headers for tracing
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    process_time = time.time() - start_time
    status_code = response.status_code
    
    log_data = {
        "request_id": request_id,
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "method": method,
        "path": path,
        "status_code": status_code,
        "latency_ms": round(process_time * 1000, 2),
        "client": client_host
    }
    
    # Structured log
    logger.info(json.dumps(log_data))
    
    # Anomaly Logging
    if status_code == 401 or status_code == 403:
        logger.warning(json.dumps({**log_data, "event": "unauthorized_access"}))
    elif status_code == 429:
        logger.warning(json.dumps({**log_data, "event": "rate_limit_exceeded"}))
    
    LogContext.clear()
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
from mfa_routes import router as mfa_router
app.include_router(mfa_router)

# Compliance routes — DPDP (India), GDPR (EU), CCPA/CPRA (California)
from gdpr_routes import router as gdpr_router
app.include_router(gdpr_router)
from ccpa_routes import router as ccpa_router
app.include_router(ccpa_router)

@app.get("/.well-known/security.txt")
async def security_txt():
    return Response(
        content="Contact: mailto:security@clutsch.com\nExpires: 2027-07-03T00:00:00.000Z\nPreferred-Languages: en\n",
        media_type="text/plain",
        headers={"Content-Disposition": "inline"}
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.datetime.utcnow().isoformat()}

@app.get("/ready")
async def readiness_check():
    checks = {}
    
    # Check database connectivity
    try:
        await db.get_items("t-acme")  # quick ping
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


@app.get("/dpa")
async def get_dpa():
    """
    Serve the Data Processing Agreement (DPA) template document.
    This is a static document for enterprise customers.
    """
    import json
    with open("dpa_template.json") as f:
        dpa = json.load(f)
    return dpa


@app.get("/dpa/subprocessors")
async def get_subprocessors():
    """
    Return the current list of subprocessors handling user data.
    """
    import json
    with open("dpa_template.json") as f:
        dpa = json.load(f)
    return {
        "subprocessors": dpa["dpa"]["subprocessors"],
        "updated_at": dpa["dpa"]["effective_date"]
    }

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
        "text": sanitize_text(item.text),
        "source": html.escape(item.source.strip()),
        "deadline": item.deadline,
        "metadata": item.metadata or {},
        "timestamp": time.time()
    }
    await db.add_item(item_data)
    await notify_new_items(tenant_id, 1)
    return item_data

# Scoring Service Setup
from services import scoring_service, split_archived_snoozed

async def _verify_item_ownership(item_id: str, tenant_id: str):
    items = await db.get_items(tenant_id)
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
    items = await db.get_items(tenant_id)

    # Filter out archived and snoozed, based on each item's own columns
    now = datetime.datetime.now()
    active_items = []
    for item in items:
        if item.get("is_archived"):
            continue
        if item.get("is_snoozed") and item.get("snoozed_until") and item["snoozed_until"] > now:
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
    items = await db.get_items(tenant_id)

    contact_priorities = await db.get_contact_priorities(tenant_id)
    tenant_archived, tenant_snoozed = split_archived_snoozed(items)

    scored_items = await scoring_service.process_items(
        tenant_id,
        items,
        tenant_archived,
        tenant_snoozed,
        contact_priorities
    )

    if tier:
        scored_items = [i for i in scored_items if i["priorityTier"] == tier]

    return scored_items

class BulkItemIds(BaseModel):
    item_ids: List[str]

class BulkSnoozeRequest(BaseModel):
    item_ids: List[str]
    hours: int

# NOTE: these two bulk routes must be registered BEFORE
# /items/{item_id}/archive and /items/{item_id}/snooze below — otherwise
# FastAPI's path matching would treat the literal segment "bulk" as an
# {item_id} value and route bulk requests into the single-item handlers.
@app.post("/items/bulk/archive")
@limiter.limit("20/minute")
async def bulk_archive_items(request: Request, body: BulkItemIds, current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id

    # Verify tenant ownership per-id, skipping (not failing the whole batch on) any id
    # that doesn't belong to this tenant.
    valid_ids = []
    for item_id in body.item_ids:
        try:
            await _verify_item_ownership(item_id, tenant_id)
            valid_ids.append(item_id)
        except HTTPException:
            continue

    archived_ids = await db.bulk_archive_items(tenant_id, valid_ids) if valid_ids else []

    # One audit log entry for the whole batch, not one per item.
    if archived_ids:
        await db.add_audit_log(current_user.id, "bulk_archive_items", f"Archived {len(archived_ids)} items")

    return {
        "status": "success",
        "message": f"Archived {len(archived_ids)} items",
        "archived_count": len(archived_ids),
        "item_ids": archived_ids,
    }

@app.post("/items/bulk/snooze")
@limiter.limit("20/minute")
async def bulk_snooze_items(
    request: Request,
    body: BulkSnoozeRequest,
    current_user: User = Depends(get_current_active_user)
):
    tenant_id = current_user.tenant_id

    valid_ids = []
    for item_id in body.item_ids:
        try:
            await _verify_item_ownership(item_id, tenant_id)
            valid_ids.append(item_id)
        except HTTPException:
            continue

    until = datetime.datetime.now() + datetime.timedelta(hours=body.hours)
    snoozed_ids = await db.bulk_snooze_items(tenant_id, valid_ids, until) if valid_ids else []

    # One audit log entry for the whole batch, not one per item.
    if snoozed_ids:
        await db.add_audit_log(current_user.id, "bulk_snooze_items", f"Snoozed {len(snoozed_ids)} items for {body.hours}h")

    return {
        "status": "success",
        "message": f"Snoozed {len(snoozed_ids)} items until {until}",
        "snoozed_count": len(snoozed_ids),
        "item_ids": snoozed_ids,
        "snoozed_until": until.isoformat(),
    }

@app.post("/items/{item_id}/archive")
@limiter.limit("30/minute")
async def archive_item(request: Request, item_id: str, current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id
    await _verify_item_ownership(item_id, tenant_id)
    await db.archive_item(tenant_id, item_id)

    # Audit log
    await db.add_audit_log(current_user.id, "archive_item", f"Archived item {item_id}")
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
    await _verify_item_ownership(item_id, tenant_id)

    until = datetime.datetime.now() + datetime.timedelta(hours=hours)
    await db.snooze_item(tenant_id, item_id, until)

    # Audit log
    await db.add_audit_log(current_user.id, "snooze_item", f"Snoozed item {item_id} for {hours}h")
    return {"status": "success", "message": f"Item {item_id} snoozed until {until}"}

@app.post("/items/{item_id}/unsnooze")
@limiter.limit("30/minute")
async def unsnooze_item(request: Request, item_id: str, current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id
    await _verify_item_ownership(item_id, tenant_id)
    was_snoozed = await db.unsnooze_item(tenant_id, item_id)
    if was_snoozed:
        # Audit log
        await db.add_audit_log(current_user.id, "unsnooze_item", f"Unsnoozed item {item_id}")
    return {"status": "success", "message": f"Item {item_id} unsnoozed"}

@app.get("/stats")
@limiter.limit("20/minute")
async def get_stats(request: Request, current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id
    now = datetime.datetime.now()
    items = await db.get_items(tenant_id)
    archived_count = sum(1 for i in items if i.get("is_archived"))
    snoozed_count = sum(
        1 for i in items
        if i.get("is_snoozed") and i.get("snoozed_until") and i["snoozed_until"] > now
    )
    return {
        "archived_count": archived_count,
        "snoozed_count": snoozed_count
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3000)
