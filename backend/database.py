import time
import logging
import uuid
import json
import os
from typing import List, Dict, Any, Optional
from security import encrypt_secret, decrypt_secret
from threading import Lock

logger = logging.getLogger("database")

# Persistence
DATA_DIR = os.environ.get("CLUTSCH_DATA_DIR", "/home/team/shared/data")
DB_FILE = os.path.join(DATA_DIR, "database.json")

class MockDatabase:
    def __init__(self):
        self._items = []
        self._lock = Lock()
        self.failed_login_attempts = {}
        self.locked_accounts = {}
        self.audit_logs = []
        self.archived_items = {} # tenant_id -> set of item_ids
        self.snoozed_items = {} # tenant_id -> {item_id: until}
        self.delegations = {} # item_id -> {assigned_to: user_id, note: str, assigned_by: user_id, timestamp: float}
        self.presence = {} # item_id -> {user_id: timestamp}
        self.focus_scores = {} # tenant_id -> score
        self.team_metrics = {} # tenant_id -> metrics_dict
        self.custom_weights = {} # tenant_id -> {factor -> weight}
        self.semantic_weights = {} # tenant_id -> {concept -> boost}
        self.contact_priorities = {} # tenant_id -> {platform -> {handle -> priority}}
        self.project_priorities = {} # tenant_id -> {project_id -> priority}
        self.client_priorities = {} # tenant_id -> {client_id -> priority}
        self.custom_integrations = {} # tenant_id -> {integration_id: config_dict}
        self.workflows = {} # tenant_id -> {workflow_id: workflow_dict}
        self.tenants_billing = {
            "t-acme": {
                "plan": "Pro",
                "subscription_id": "sub_mock_pro",
                "customer_id": "cus_mock_acme",
                "usage": {
                    "active_integrations": 4,
                    "team_members": 8,
                    "ai_items_processed": 1250,
                    "smart_responses": 45
                },
                "limits": {
                    "active_integrations": 10,
                    "team_members": 20,
                    "ai_items_processed": 5000,
                    "smart_responses": 100
                }
            }
        }
        
        # Multi-tenancy: tenant_id -> { provider_name -> config }
        self.connected_integrations = {
            "t-acme": {
                "slack": {
                    "enabled": True,
                    "sync_frequency": 15,
                    "priority_threshold": 50,
                    "token": "mock-slack-token-123"
                }
            }
        }
        
        # MFA storage
        self.mfa_secrets = {}  # user_id -> totp_secret
        self.mfa_pending_secrets = {}  # user_id -> pending_totp_secret (before verification)
        self.mfa_recovery_codes = {}  # user_id -> [hashed_recovery_codes]
        
        # Load persisted state from disk
        self._load_from_disk()

    def upsert_items(self, items: List[Dict[str, Any]]):
        with self._lock:
            for item in items:
                # Ensure item has a unique ID if not present
                if "id" not in item:
                    item["id"] = str(uuid.uuid4())
                
                # Basic upsert based on source and external_id
                found = False
                for i, existing in enumerate(self._items):
                    if (existing.get("source") == item.get("source") and 
                        existing.get("external_id") == item.get("external_id") and
                        existing.get("tenant_id") == item.get("tenant_id")):
                        self._items[i] = item
                        found = True
                        break
                
                if not found:
                    self._items.append(item)
            return len(items)

    def get_items(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            if tenant_id:
                return [i for i in self._items if i.get("tenant_id") == tenant_id]
            return self._items

    def delete_item(self, item_id: str, tenant_id: str):
        with self._lock:
            initial_len = len(self._items)
            self._items = [i for i in self._items if not (i.get("id") == item_id and i.get("tenant_id") == tenant_id)]
            return len(self._items) < initial_len

    def add_audit_log(self, user_id: str, action: str, details: str):
        log_entry = {
            "timestamp": time.time(),
            "user_id": user_id,
            "action": action,
            "details": details
        }
        with self._lock:
            self.audit_logs.append(log_entry)
            logger.info(f"Audit Log: {action} by {user_id}")

    def connect_integration(self, tenant_id: str, provider: str, config: Dict[str, Any]):
        with self._lock:
            if tenant_id not in self.connected_integrations:
                self.connected_integrations[tenant_id] = {}
            self.connected_integrations[tenant_id][provider] = config
            logger.info(f"Connected integration: {tenant_id}/{provider}")

    def disconnect_integration(self, tenant_id: str, provider: str):
        with self._lock:
            if tenant_id in self.connected_integrations and provider in self.connected_integrations[tenant_id]:
                del self.connected_integrations[tenant_id][provider]
                logger.info(f"Disconnected integration: {tenant_id}/{provider}")
                return True
            return False

    def save_integration_tokens(self, tenant_id: str, provider: str, tokens: Dict[str, Any]):
        with self._lock:
            if tenant_id not in self.connected_integrations:
                self.connected_integrations[tenant_id] = {}
            
            if provider not in self.connected_integrations[tenant_id]:
                self.connected_integrations[tenant_id][provider] = {
                    "enabled": True,
                    "sync_frequency": 30,
                    "priority_threshold": 0
                }
            
            # Encrypt sensitive token fields at rest
            encrypted_tokens = {}
            for key, value in tokens.items():
                if key.lower() in ('token', 'secret', 'refresh_token', 'access_token', 'api_key', 'password'):
                    encrypted_tokens[key] = encrypt_secret(str(value))
                else:
                    encrypted_tokens[key] = value
            
            self.connected_integrations[tenant_id][provider].update(encrypted_tokens)
            logger.info(f"Saved OAuth tokens for {tenant_id}/{provider}")
            return True

    def update_integration_settings(self, tenant_id: str, provider: str, settings: Dict[str, Any]):
        with self._lock:
            if tenant_id in self.connected_integrations and provider in self.connected_integrations[tenant_id]:
                self.connected_integrations[tenant_id][provider].update(settings)
                logger.info(f"Updated integration settings: {tenant_id}/{provider} -> {settings}")
                return True
            return False

    def get_integration_config(self, tenant_id: str, provider: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            if tenant_id not in self.connected_integrations:
                return None
            config = self.connected_integrations[tenant_id].get(provider)
            if not config:
                return None
            # Decrypt sensitive fields on read
            decrypted = {}
            for key, value in config.items():
                if key.lower() in ('token', 'secret', 'refresh_token', 'access_token', 'api_key', 'password'):
                    decrypted[key] = decrypt_secret(str(value))
                else:
                    decrypted[key] = value
            return decrypted

    def enforce_retention_policy(self, days: int = 30):
        cutoff = time.time() - (days * 24 * 60 * 60)
        with self._lock:
            initial_count = len(self._items)
            self._items = [i for i in self._items if i.get("timestamp", time.time()) > cutoff]
            deleted = initial_count - len(self._items)
            if deleted > 0:
                logger.info(f"Retention Policy: Deleted {deleted} items older than {days} days.")
            return deleted

    def delegate_item(self, item_id: str, tenant_id: str, to_user_id: str, assigned_by: str, note: str = ""):
        with self._lock:
            # Verify item exists and belongs to tenant
            item_exists = any(i["id"] == item_id and i.get("tenant_id") == tenant_id for i in self._items)
            if not item_exists:
                return False
            
            self.delegations[item_id] = {
                "assigned_to": to_user_id,
                "assigned_by": assigned_by,
                "note": note,
                "timestamp": time.time()
            }
            return True

    def get_delegation(self, item_id: str):
        with self._lock:
            return self.delegations.get(item_id)

    def update_presence(self, item_id: str, user_id: str, action: str = "viewing"):
        with self._lock:
            if item_id not in self.presence:
                self.presence[item_id] = {}
            self.presence[item_id][user_id] = {
                "action": action,
                "timestamp": time.time()
            }
            # Cleanup old presence (TTL 1 minute)
            now = time.time()
            self.presence[item_id] = {u: data for u, data in self.presence[item_id].items() if now - data["timestamp"] < 60}

    def get_presence(self, item_id: str):
        with self._lock:
            if item_id not in self.presence:
                return {}
            # Cleanup old presence (TTL 1 minute)
            now = time.time()
            self.presence[item_id] = {u: data for u, data in self.presence[item_id].items() if now - data["timestamp"] < 60}
            return self.presence[item_id]

    def get_contact_priorities(self, tenant_id: str):
        with self._lock:
            return self.contact_priorities.get(tenant_id, {})

    def set_contact_priority(self, tenant_id: str, platform: str, handle: str, priority: str):
        with self._lock:
            if tenant_id not in self.contact_priorities:
                self.contact_priorities[tenant_id] = {}
            if platform not in self.contact_priorities[tenant_id]:
                self.contact_priorities[tenant_id][platform] = {}
            self.contact_priorities[tenant_id][platform][handle] = priority
            return True

    def delete_contact_priority(self, tenant_id: str, platform: str, handle: str):
        with self._lock:
            if tenant_id in self.contact_priorities and platform in self.contact_priorities[tenant_id]:
                if handle in self.contact_priorities[tenant_id][platform]:
                    del self.contact_priorities[tenant_id][platform][handle]
                    return True
            return False

    def delete_contact_priority(self, tenant_id: str, platform: str, handle: str):
        with self._lock:
            if tenant_id in self.contact_priorities and platform in self.contact_priorities[tenant_id]:
                if handle in self.contact_priorities[tenant_id][platform]:
                    del self.contact_priorities[tenant_id][platform][handle]
                    return True
            return False

    def get_project_priorities(self, tenant_id: str):
        with self._lock:
            return self.project_priorities.get(tenant_id, {})

    def set_project_priority(self, tenant_id: str, project_id: str, priority: str):
        with self._lock:
            if tenant_id not in self.project_priorities:
                self.project_priorities[tenant_id] = {}
            self.project_priorities[tenant_id][project_id] = priority
            return True

    def get_client_priorities(self, tenant_id: str):
        with self._lock:
            return self.client_priorities.get(tenant_id, {})

    def set_client_priority(self, tenant_id: str, client_id: str, priority: str):
        with self._lock:
            if tenant_id not in self.client_priorities:
                self.client_priorities[tenant_id] = {}
            self.client_priorities[tenant_id][client_id] = priority
            return True

    def get_custom_integrations(self, tenant_id: str):
        with self._lock:
            return self.custom_integrations.get(tenant_id, {})

    def add_custom_integration(self, tenant_id: str, config: Dict[str, Any]):
        integration_id = str(uuid.uuid4())
        config["id"] = integration_id
        with self._lock:
            if tenant_id not in self.custom_integrations:
                self.custom_integrations[tenant_id] = {}
            self.custom_integrations[tenant_id][integration_id] = config
            return integration_id

    def update_custom_integration(self, tenant_id: str, integration_id: str, config: Dict[str, Any]):
        with self._lock:
            if tenant_id in self.custom_integrations and integration_id in self.custom_integrations[tenant_id]:
                self.custom_integrations[tenant_id][integration_id].update(config)
                return True
            return False

    def delete_custom_integration(self, tenant_id: str, integration_id: str):
        with self._lock:
            if tenant_id in self.custom_integrations and integration_id in self.custom_integrations[tenant_id]:
                del self.custom_integrations[tenant_id][integration_id]
                return True
            return False

    def get_workflows(self, tenant_id: str):
        with self._lock:
            return self.workflows.get(tenant_id, {})

    def add_workflow(self, tenant_id: str, workflow: Dict[str, Any]):
        workflow_id = str(uuid.uuid4())
        workflow["id"] = workflow_id
        with self._lock:
            if tenant_id not in self.workflows:
                self.workflows[tenant_id] = {}
            self.workflows[tenant_id][workflow_id] = workflow
            return workflow_id

    def update_workflow(self, tenant_id: str, workflow_id: str, workflow: Dict[str, Any]):
        with self._lock:
            if tenant_id in self.workflows and workflow_id in self.workflows[tenant_id]:
                self.workflows[tenant_id][workflow_id].update(workflow)
                return True
            return False

    def delete_workflow(self, tenant_id: str, workflow_id: str):
        with self._lock:
            if tenant_id in self.workflows and workflow_id in self.workflows[tenant_id]:
                del self.workflows[tenant_id][workflow_id]
                return True
            return False

    def get_audit_logs(self, tenant_id: str):
        # In a real app, users and tenants are linked. 
        # Here we filter audit logs by finding users belonging to the tenant.
        from auth.models import get_users_db
        tenant_user_ids = {u.id for u in get_users_db() if u.tenant_id == tenant_id}
        with self._lock:
            return [log for log in self.audit_logs if log["user_id"] in tenant_user_ids]

    def add_item(self, item: Dict[str, Any]):
        with self._lock:
            self._items.append(item)
            return item["id"]

    def get_billing_info(self, tenant_id: str):
        with self._lock:
            return self.tenants_billing.get(tenant_id)

    # Per-plan limits aligned with the Clutsch business plan tiers.
    # Free: individual, up to 2 integrations and 50 messages/month.
    # Pro: individual, full integrations + AI priority scoring.
    # SME: small business, up to 20 users, team collaboration.
    # Enterprise: 20+ users, advanced analytics, SSO, dedicated support.
    PLAN_LIMITS = {
        "Free": {"active_integrations": 2, "team_members": 1, "ai_items_processed": 50, "smart_responses": 5},
        "Pro": {"active_integrations": 10, "team_members": 1, "ai_items_processed": 5000, "smart_responses": 100},
        "SME": {"active_integrations": 25, "team_members": 20, "ai_items_processed": 25000, "smart_responses": 1000},
        "Enterprise": {"active_integrations": 100, "team_members": 1000, "ai_items_processed": 100000, "smart_responses": 5000},
    }

    def update_billing_plan(self, tenant_id: str, plan: str, subscription_id: str = None, customer_id: str = None):
        with self._lock:
            # Normalize/validate plan; default unknown plans to Free.
            if plan not in self.PLAN_LIMITS:
                plan = "Free"

            if tenant_id not in self.tenants_billing:
                self.tenants_billing[tenant_id] = {
                    "usage": {"active_integrations": 0, "team_members": 0, "ai_items_processed": 0, "smart_responses": 0},
                    "limits": dict(self.PLAN_LIMITS["Free"])
                }
            self.tenants_billing[tenant_id]["plan"] = plan
            if subscription_id:
                self.tenants_billing[tenant_id]["subscription_id"] = subscription_id
            if customer_id:
                self.tenants_billing[tenant_id]["customer_id"] = customer_id

            # Update limits based on plan (all 4 tiers)
            self.tenants_billing[tenant_id]["limits"] = dict(self.PLAN_LIMITS[plan])
            return True

    def get_custom_weights(self, tenant_id: str):
        with self._lock:
            return self.custom_weights.get(tenant_id, {
                'urgency': 0.3,
                'importance': 0.3,
                'sender_rank': 0.2,
                'deadline': 0.2
            })

    def set_custom_weights(self, tenant_id: str, weights: Dict[str, float]):
        with self._lock:
            self.custom_weights[tenant_id] = weights
            return True

    def get_semantic_weights(self, tenant_id: str):
        with self._lock:
            return self.semantic_weights.get(tenant_id, {
                'financial_impact': 0.2,
                'technical_debt': 0.15,
                'customer_success': 0.2,
                'compliance': 0.1
            })

    def set_semantic_weights(self, tenant_id: str, weights: Dict[str, float]):
        with self._lock:
            self.semantic_weights[tenant_id] = weights
            return True

    # --- MFA methods ---
    def set_mfa_pending_secret(self, user_id: str, secret: str):
        with self._lock:
            self.mfa_pending_secrets[user_id] = secret

    def get_mfa_pending_secret(self, user_id: str) -> Optional[str]:
        with self._lock:
            return self.mfa_pending_secrets.get(user_id)

    def clear_mfa_pending_secret(self, user_id: str):
        with self._lock:
            self.mfa_pending_secrets.pop(user_id, None)

    def set_mfa_secret(self, user_id: str, secret: str):
        with self._lock:
            self.mfa_secrets[user_id] = secret

    def get_mfa_secret(self, user_id: str) -> Optional[str]:
        with self._lock:
            return self.mfa_secrets.get(user_id)

    def clear_mfa_secret(self, user_id: str):
        with self._lock:
            self.mfa_secrets.pop(user_id, None)

    def set_mfa_recovery_codes(self, user_id: str, codes: List[str]):
        with self._lock:
            self.mfa_recovery_codes[user_id] = codes

    def get_mfa_recovery_codes(self, user_id: str) -> Optional[List[str]]:
        with self._lock:
            return self.mfa_recovery_codes.get(user_id)

    def clear_mfa_recovery_codes(self, user_id: str):
        with self._lock:
            self.mfa_recovery_codes.pop(user_id, None)

    # --- Consent & DPDP methods ---
    def record_consent(self, user_id: str, consent: Dict[str, Any]):
        with self._lock:
            if not hasattr(self, 'consent_records'):
                self.consent_records = {}
            if user_id not in self.consent_records:
                self.consent_records[user_id] = []
            record = {**consent, "timestamp": time.time()}
            self.consent_records[user_id].append(record)

    def get_consents(self, user_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            if not hasattr(self, 'consent_records'):
                return []
            return self.consent_records.get(user_id, [])

    # Granular per-purpose consent preferences (DPDP + GDPR)
    def get_consent_preferences(self, user_id: str) -> Dict[str, bool]:
        if not hasattr(self, 'consent_preferences'):
            self.consent_preferences = {}
        return self.consent_preferences.get(user_id, {})

    def set_consent_preferences(self, user_id: str, prefs: Dict[str, bool]):
        with self._lock:
            if not hasattr(self, 'consent_preferences'):
                self.consent_preferences = {}
            self.consent_preferences[user_id] = prefs

    def set_nominee(self, user_id: str, nominee: Dict[str, str]):
        with self._lock:
            if not hasattr(self, 'nominees'):
                self.nominees = {}
            self.nominees[user_id] = nominee

    def get_nominee(self, user_id: str) -> Optional[Dict[str, str]]:
        with self._lock:
            if not hasattr(self, 'nominees'):
                return None
            return self.nominees.get(user_id)

    def add_grievance(self, grievance: Dict[str, Any]):
        with self._lock:
            if not hasattr(self, 'grievance_logs'):
                self.grievance_logs = []
            grievance["id"] = str(uuid.uuid4())
            self.grievance_logs.append(grievance)

    def get_grievances(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            if not hasattr(self, 'grievance_logs'):
                return []
            if user_id:
                return [g for g in self.grievance_logs if g.get("user_id") == user_id]
            return self.grievance_logs

    def clear(self):
        with self._lock:
            self._items.clear()
            self.audit_logs.clear()
            self.archived_items.clear()
            self.snoozed_items.clear()
            self.delegations.clear()
            self.presence.clear()
            self.custom_weights.clear()
            self.semantic_weights.clear()
            self.contact_priorities.clear()
            self.custom_integrations.clear()
            self.workflows.clear()

    # --- Persistence Layer ---
    def _serialize(self) -> dict:
        """Serialize database state to a JSON-serializable dict."""
        return {
            "items": self._items,
            "audit_logs": self.audit_logs,
            "archived_items": {k: list(v) for k, v in self.archived_items.items()},
            "snoozed_items": self.snoozed_items,
            "delegations": self.delegations,
            "custom_weights": self.custom_weights,
            "semantic_weights": self.semantic_weights,
            "contact_priorities": self.contact_priorities,
            "project_priorities": self.project_priorities,
            "client_priorities": self.client_priorities,
            "custom_integrations": self.custom_integrations,
            "workflows": self.workflows,
            "tenants_billing": self.tenants_billing,
            "connected_integrations": self.connected_integrations,
            "focus_scores": self.focus_scores,
            "team_metrics": self.team_metrics,
        }

    def _deserialize(self, data: dict):
        """Restore database state from a dict."""
        self._items = data.get("items", [])
        self.audit_logs = data.get("audit_logs", [])
        self.archived_items = {k: set(v) for k, v in data.get("archived_items", {}).items()}
        self.snoozed_items = data.get("snoozed_items", {})
        self.delegations = data.get("delegations", {})
        self.custom_weights = data.get("custom_weights", {})
        self.semantic_weights = data.get("semantic_weights", {})
        self.contact_priorities = data.get("contact_priorities", {})
        self.project_priorities = data.get("project_priorities", {})
        self.client_priorities = data.get("client_priorities", {})
        self.custom_integrations = data.get("custom_integrations", {})
        self.workflows = data.get("workflows", {})
        self.tenants_billing = data.get("tenants_billing", {})
        self.connected_integrations = data.get("connected_integrations", {})
        self.focus_scores = data.get("focus_scores", {})
        self.team_metrics = data.get("team_metrics", {})

    def save_to_disk(self):
        """Persist current database state to JSON file."""
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            state = self._serialize()
            with open(DB_FILE, "w") as f:
                json.dump(state, f, indent=2, default=str)
            logger.info(f"Database saved to {DB_FILE}")
        except Exception as e:
            logger.error(f"Failed to save database: {e}")

    def _load_from_disk(self):
        """Load database state from JSON file on startup."""
        if not os.path.exists(DB_FILE):
            logger.info(f"No saved database found at {DB_FILE}, starting fresh")
            return
        try:
            with open(DB_FILE, "r") as f:
                state = json.load(f)
            self._deserialize(state)
            logger.info(f"Database loaded from {DB_FILE} ({len(self._items)} items)")
        except Exception as e:
            logger.error(f"Failed to load database: {e}")

db = MockDatabase()
