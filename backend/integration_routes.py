import datetime
import asyncio
import logging
import uuid
import os
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Request, Body
from slowapi import Limiter
from slowapi.util import get_remote_address

from auth.dependencies import get_current_active_user
from auth.models import User
from database import db
from security import encrypt_secret, decrypt_secret
from utils.retries import async_retry_with_backoff
from worker import background_worker
from adapters.gmail import GmailAdapter
from adapters.slack import SlackAdapter
from adapters.whatsapp import WhatsAppAdapter
from adapters.outlook import OutlookAdapter
from adapters.teams import TeamsAdapter
from adapters.jira import JiraAdapter
from adapters.custom import CustomAdapter
from realtime_routes import notify_new_items
from workflow_service import workflow_service
from services import scoring_service

logger = logging.getLogger("priorityflow")
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/integrations", tags=["integrations"])

# Integration Mappings
ADAPTERS = {
    "gmail": GmailAdapter(),
    "slack": SlackAdapter(),
    "whatsapp": WhatsAppAdapter(),
    "outlook": OutlookAdapter(),
    "teams": TeamsAdapter(),
    "jira": JiraAdapter()
}

class ConnectRequest(BaseModel):
    token: str

class CodeExchangeRequest(BaseModel):
    code: str
    state: Optional[str] = None

class IntegrationSettings(BaseModel):
    enabled: Optional[bool] = None
    sync_frequency: Optional[int] = None # in minutes
    priority_threshold: Optional[int] = None

@router.get("")
@limiter.limit("20/minute")
async def list_integrations(request: Request, current_user: User = Depends(get_current_active_user)):
    tenant_id = current_user.tenant_id
    tenant_integrations = await db.get_connected_integrations(tenant_id)
    
    connected_list = []
    for provider, config in tenant_integrations.items():
        connected_list.append({
            "provider": provider,
            "connected_at": config.get("connected_at"),
            "settings": config.get("settings", {
                "enabled": True,
                "sync_frequency": 60,
                "priority_threshold": 50
            })
        })
        
    return {
        "available": list(ADAPTERS.keys()),
        "connected": connected_list
    }

@router.post("/{provider}/connect")
@limiter.limit("10/minute")
async def connect_integration(
    request: Request,
    provider: str,
    connect_req: ConnectRequest,
    current_user: User = Depends(get_current_active_user)
):
    if provider not in ADAPTERS:
        raise HTTPException(status_code=404, detail="Provider not found")
    tenant_id = current_user.tenant_id
    
    encrypted_token = encrypt_secret(connect_req.token)
    
    # Initialize with default settings
    config = {
        "connected_at": datetime.datetime.now().isoformat(),
        "token": encrypted_token,
        "settings": {
            "enabled": True,
            "sync_frequency": 60,
            "priority_threshold": 50
        }
    }
    
    await db.connect_integration(tenant_id, provider, config)

    # Audit log
    await db.add_audit_log(current_user.id, "connect_integration", f"Connected {provider} via token")
    return {"message": f"Connected to {provider}", "status": "success"}

@router.post("/{provider}/exchange")
@limiter.limit("10/minute")
async def exchange_code(
    request: Request,
    provider: str,
    exchange_req: CodeExchangeRequest,
    current_user: User = Depends(get_current_active_user)
):
    if provider not in ["gmail", "outlook"]:
         raise HTTPException(status_code=400, detail="OAuth exchange not supported for this provider")
    
    tenant_id = current_user.tenant_id
    
    try:
        tokens = await exchange_code_for_tokens(provider, exchange_req.code)
        
        # Encrypt tokens before storing
        config = {
            "connected_at": datetime.datetime.now().isoformat(),
            "access_token": encrypt_secret(tokens["access_token"]),
            "refresh_token": encrypt_secret(tokens["refresh_token"]) if tokens.get("refresh_token") else None,
            "token_expiry": (datetime.datetime.now() + datetime.timedelta(seconds=tokens["expires_in"])).isoformat(),
            "settings": {
                "enabled": True,
                "sync_frequency": 60,
                "priority_threshold": 50
            }
        }
        
        await db.connect_integration(tenant_id, provider, config)
        await db.add_audit_log(current_user.id, "oauth_exchange", f"Exchanged code for {provider}")
        
        return {"message": "Exchange successful", "provider": provider}
    except Exception as e:
        logger.error(f"Exchange error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{provider}/auth-url")
@limiter.limit("10/minute")
async def get_auth_url(
    provider: str,
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    if provider not in ["gmail", "outlook"]:
        raise HTTPException(status_code=400, detail="OAuth not supported for this provider")
    
    client_id = os.environ.get(f"{provider.upper()}_CLIENT_ID", f"mock-{provider}-client-id")
    redirect_uri = os.environ.get(f"{provider.upper()}_REDIRECT_URI", f"http://localhost:3000/integrations/{provider}/callback")
    
    if provider == "gmail":
        auth_base = "https://accounts.google.com/o/oauth2/v2/auth"
        scopes = "https://www.googleapis.com/auth/gmail.readonly"
    else: # outlook
        auth_base = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        scopes = "https://graph.microsoft.com/Mail.Read"
        
    state = str(uuid.uuid4())
    # In production, store 'state' in a cache/db to verify on callback
    
    auth_url = f"{auth_base}?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}&state={state}&access_type=offline&prompt=consent"
    
    return {"url": auth_url, "state": state}

@router.get("/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str,
    state: str,
):
    # This is normally reached by a redirect from the provider.
    # In a real SPA, this would redirect back to the frontend with the code.
    logger.info(f"Received OAuth callback for {provider} with code: {code[:10]}...")
    
    return {
        "message": "OAuth authorized. Please send this code to /exchange to complete setup.",
        "provider": provider,
        "code": code,
        "state": state
    }

@router.patch("/{provider}/settings")
@limiter.limit("20/minute")
async def update_integration_settings(
    request: Request,
    provider: str,
    settings: IntegrationSettings,
    current_user: User = Depends(get_current_active_user)
):
    tenant_id = current_user.tenant_id
    settings_dict = {k: v for k, v in settings.dict().items() if v is not None}

    if not await db.update_integration_settings(tenant_id, provider, settings_dict):
        raise HTTPException(status_code=404, detail="Integration not found or not connected")

    await db.add_audit_log(current_user.id, "update_integration_settings", f"Updated settings for {provider}: {settings_dict}")
    return {"message": f"Updated settings for {provider}", "status": "success"}

@router.delete("/{provider}")
@limiter.limit("10/minute")
async def disconnect_integration(
    request: Request,
    provider: str,
    current_user: User = Depends(get_current_active_user)
):
    tenant_id = current_user.tenant_id

    if not await db.disconnect_integration(tenant_id, provider):
        raise HTTPException(status_code=404, detail="Integration not found or not connected")

    await db.add_audit_log(current_user.id, "disconnect_integration", f"Disconnected {provider}")
    return {"message": f"Disconnected {provider}", "status": "success"}

@router.post("/sync")
@limiter.limit("5/minute")
async def trigger_sync(
    request: Request,
    current_user: User = Depends(get_current_active_user)
):
    tenant_id = current_user.tenant_id
    task_id = background_worker.enqueue(sync_all_integrations_sync, tenant_id)

    await db.add_audit_log(current_user.id, "trigger_sync", "Triggered manual sync")
    return {"message": "Sync triggered", "status": "processing", "task_id": task_id}

# Helper Functions
async def exchange_code_for_tokens(provider: str, code: str) -> Dict[str, Any]:
    # Robust simulation of OAuth token exchange
    await asyncio.sleep(0.5) 
    if not code:
        raise ValueError("Invalid authorization code")
        
    return {
        "access_token": f"at-{provider}-{uuid.uuid4().hex[:12]}",
        "refresh_token": f"rt-{provider}-{uuid.uuid4().hex[:12]}",
        "expires_in": 3600,
        "token_type": "Bearer",
        "scope": "gmail.readonly" if provider == "gmail" else "Mail.Read"
    }

async def refresh_provider_token(provider: str, refresh_token: str) -> Dict[str, Any]:
    # Robust simulation of OAuth token refresh
    await asyncio.sleep(0.4)
    return {
        "access_token": f"at-{provider}-refreshed-{uuid.uuid4().hex[:12]}",
        "expires_in": 3600,
        "token_type": "Bearer"
    }

async def sync_all_integrations(tenant_id: str):
    tenant_integrations = await db.get_connected_integrations(tenant_id)
    all_items = []
    
    for provider, config in tenant_integrations.items():
        settings = config.get("settings", {})
        if not settings.get("enabled", True):
            logger.info(f"Sync skipped for {provider} (disabled) for tenant {tenant_id}")
            continue
            
        adapter = ADAPTERS.get(provider)
        if adapter:
            try:
                # Handle token decryption and possible refresh
                access_token_enc = config.get("access_token") or config.get("token")
                refresh_token_enc = config.get("refresh_token")
                expiry_str = config.get("token_expiry")
                
                token = decrypt_secret(access_token_enc) if access_token_enc else None
                
                # Check if token expired
                if expiry_str and refresh_token_enc:
                    expiry = datetime.datetime.fromisoformat(expiry_str)
                    if datetime.datetime.now() > expiry - datetime.timedelta(minutes=5):
                        logger.info(f"Refreshing token for {provider}/{tenant_id}")
                        refresh_token = decrypt_secret(refresh_token_enc)
                        new_tokens = await refresh_provider_token(provider, refresh_token)
                        token = new_tokens["access_token"]
                        
                        # Update DB with new token
                        await db.save_integration_tokens(tenant_id, provider, {
                            "access_token": encrypt_secret(token),
                            "token_expiry": (datetime.datetime.now() + datetime.timedelta(seconds=new_tokens["expires_in"])).isoformat()
                        })

                retryable_fetch = async_retry_with_backoff()(adapter.fetch_items)
                normalized_items = await retryable_fetch(token)
                for item in normalized_items:
                    item_dict = item.dict()
                    item_dict["tenant_id"] = tenant_id
                    item_dict["sender_handle"] = item.sender.get("handle", "unknown")
                    all_items.append(item_dict)
            except Exception as e:
                logger.error(f"SYNC_ERROR: {provider} for {tenant_id}: {e}")
    
    # --- Sync Custom Integrations ---
    custom_integrations = await db.get_custom_integrations(tenant_id)  # list of dicts, each with an "id"
    all_custom_items = []
    for config in custom_integrations:
        if not config.get("enabled", True):
            continue

        try:
            adapter = CustomAdapter(config)
            items = await adapter.fetch_items()
            for item in items:
                item_dict = item.dict()
                item_dict["tenant_id"] = tenant_id
                item_dict["sender_handle"] = item.sender.get("handle", "unknown")
                all_custom_items.append(item_dict)
        except Exception as e:
            logger.error(f"CUSTOM_SYNC_ERROR: {config.get('name')} for {tenant_id}: {e}")

    total_items = all_items + all_custom_items
    if total_items:
        # 1. Fetch dependencies for scoring
        contact_priorities = await db.get_contact_priorities(tenant_id)

        # 2. Score items
        scored_items = await scoring_service.process_items(
            tenant_id,
            total_items,
            set(), # Don't filter out archived yet, we want to run workflows on them or they are new anyway
            {},    # Don't filter snoozed
            contact_priorities
        )

        # 3. Save to DB first — workflow actions (archive_item/snooze_item/
        # delegate_item) update an EXISTING Item row's own columns now
        # (is_archived/is_snoozed/etc, see models.py), unlike the old
        # separate archived-ids-set that didn't require the row to exist
        # yet. Running workflows before the row exists silently no-ops
        # every action.
        await db.upsert_items(scored_items)

        # 4. Run Workflows
        await workflow_service.run_workflows_for_items(tenant_id, scored_items)
        logger.info(f"SYNC_COMPLETE: {len(scored_items)} items prioritized and workflow-processed for tenant {tenant_id}")

    # Notify via WebSocket if any new items were found
    if total_items:
        await notify_new_items(tenant_id, len(total_items))

def sync_all_integrations_sync(tenant_id: str):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(sync_all_integrations(tenant_id))
    loop.close()
