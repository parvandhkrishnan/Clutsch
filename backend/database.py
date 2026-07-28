import time
import logging
import uuid
import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy import select, delete, update
from security import encrypt_secret, decrypt_secret
from db_engine import AsyncSessionLocal
from models import (
    Item, Integration, Delegation, Presence, ContactPriority, ProjectPriority,
    ClientPriority, CustomWeight, SemanticWeight, ConsentRecord, Grievance,
    Nominee, AuditLog, Billing, CustomIntegration, Workflow, MFARecoveryCode,
    FailedLogin, LockedAccount, User,
)

logger = logging.getLogger("database")

_EPOCH = datetime.datetime(1970, 1, 1)


def _to_epoch(dt: Optional[datetime.datetime]) -> float:
    """Naive-UTC datetime -> epoch seconds, without relying on datetime.timestamp()
    (which assumes local time for naive datetimes)."""
    if dt is None:
        return time.time()
    return (dt - _EPOCH).total_seconds()


def _parse_timestamp(value: Any) -> Optional[datetime.datetime]:
    """Best-effort parse of a caller-supplied 'timestamp' (epoch float or ISO-8601
    string) into a naive UTC datetime for the Item.created_at column."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.datetime.utcfromtimestamp(value)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        try:
            v = value.replace("Z", "+00:00")
            dt = datetime.datetime.fromisoformat(v)
            if dt.tzinfo is not None:
                dt = dt.astimezone(datetime.timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            return None
    return None


def _item_fields_from_dict(item: Dict[str, Any]) -> Dict[str, Any]:
    """Map an incoming free-form item dict (as produced by adapters or manual
    item creation) onto the fixed Item ORM columns."""
    sender = item.get("sender") or {}
    sender_name = item.get("sender_name") or sender.get("name")
    sender_handle = item.get("sender_handle") or sender.get("handle")
    text = item.get("text") or item.get("content") or ""
    return {
        "tenant_id": item.get("tenant_id"),
        "external_id": item.get("external_id"),
        "source": item.get("source") or "manual",
        "text": text,
        "sender_name": sender_name,
        "sender_handle": sender_handle,
        "recipient": item.get("recipient"),
        "subject": item.get("subject"),
        "thread_id": item.get("thread_id"),
        "priority_score": item.get("priorityScore", item.get("priority_score")),
        "priority_tier": item.get("priorityTier", item.get("priority_tier")),
        "ai_summary": item.get("ai_summary"),
        "explanation": item.get("explanation"),
        "urgency": item.get("urgency"),
        "importance": item.get("importance"),
        "action_suggested": item.get("action_suggested"),
        "deadline": item.get("deadline"),
        "source_url": item.get("source_url"),
        "item_metadata": item.get("metadata") or {},
        "is_archived": item.get("is_archived", False),
        "is_snoozed": item.get("is_snoozed", False),
        "snoozed_until": item.get("snoozed_until"),
    }


def _item_to_dict(row: Item) -> Dict[str, Any]:
    """Convert an Item ORM row back into the plain dict shape that route code
    throughout the app expects (item.get("id"), item.get("metadata"), etc)."""
    return {
        "id": row.id,
        "tenant_id": row.tenant_id,
        "external_id": row.external_id,
        "source": row.source,
        "text": row.text,
        "sender_name": row.sender_name,
        "sender_handle": row.sender_handle,
        "sender": {"name": row.sender_name, "handle": row.sender_handle},
        "recipient": row.recipient,
        "subject": row.subject,
        "thread_id": row.thread_id,
        "priorityScore": row.priority_score,
        "priorityTier": row.priority_tier,
        "ai_summary": row.ai_summary,
        "explanation": row.explanation,
        "urgency": row.urgency,
        "importance": row.importance,
        "action_suggested": row.action_suggested,
        "deadline": row.deadline,
        "source_url": row.source_url,
        "metadata": row.item_metadata or {},
        "is_archived": row.is_archived,
        "is_snoozed": row.is_snoozed,
        "snoozed_until": row.snoozed_until,
        "timestamp": _to_epoch(row.created_at),
    }


_SENSITIVE_KEYS = ("token", "secret", "refresh_token", "access_token", "api_key", "password")


def _integration_row_to_dict(row: Integration) -> Dict[str, Any]:
    """Reconstruct the free-form integration config dict (as originally stored
    directly in the in-memory connected_integrations dict) from the fixed
    Integration ORM columns. Values here are still ENCRYPTED at rest — callers
    that need plaintext must decrypt (see get_integration_config)."""
    cfg: Dict[str, Any] = dict(row.config or {})
    if row.token:
        cfg["token"] = row.token
        cfg["access_token"] = row.token
    if row.refresh_token:
        cfg["refresh_token"] = row.refresh_token
    if row.api_key:
        cfg["api_key"] = row.api_key
    cfg["settings"] = {
        "enabled": row.enabled,
        "sync_frequency": row.sync_frequency,
        "priority_threshold": row.priority_threshold,
    }
    return cfg


class MockDatabase:
    """SQL-backed database layer (name kept for backward compatibility with
    `from database import db` used throughout the app).

    NOTE ON TRANSACTION SCOPE: each method below opens and closes its own
    `AsyncSessionLocal()` session rather than sharing one session per HTTP
    request. This is a deliberate simplification for this migration pass — it
    sacrifices cross-call transactional atomicity within a single request
    (e.g. two db calls in the same route are NOT part of one transaction) but
    keeps every individual operation correct, and avoids threading a
    `Depends(get_db)` session parameter through every route signature.
    """

    # Per-plan limits aligned with the Clutsch business plan tiers.
    PLAN_LIMITS = {
        "Free": {"active_integrations": 2, "team_members": 1, "ai_items_processed": 50, "smart_responses": 5},
        "Pro": {"active_integrations": 10, "team_members": 1, "ai_items_processed": 5000, "smart_responses": 100},
        "SME": {"active_integrations": 25, "team_members": 20, "ai_items_processed": 25000, "smart_responses": 1000},
        "Enterprise": {"active_integrations": 100, "team_members": 1000, "ai_items_processed": 100000, "smart_responses": 5000},
    }

    DEFAULT_CUSTOM_WEIGHTS = {
        'urgency': 0.3,
        'importance': 0.3,
        'sender_rank': 0.2,
        'deadline': 0.2,
    }

    DEFAULT_SEMANTIC_WEIGHTS = {
        'financial_impact': 0.2,
        'technical_debt': 0.15,
        'customer_success': 0.2,
        'compliance': 0.1,
    }

    def __init__(self):
        # MFA "pending" secrets (the period between /auth/mfa/setup and
        # /auth/mfa/verify) have no dedicated column in the fixed schema
        # (models.py only has User.mfa_secret for the CONFIRMED secret), so
        # they're kept in-memory only. This is an intentional, narrow
        # simplification — losing an in-progress (unverified) MFA setup on
        # process restart is low-impact since it hasn't been confirmed yet.
        self._mfa_pending_secrets: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Items
    # ------------------------------------------------------------------
    async def upsert_items(self, items: List[Dict[str, Any]]) -> int:
        async with AsyncSessionLocal() as session:
            for item in items:
                if "id" not in item:
                    item["id"] = str(uuid.uuid4())
                fields = _item_fields_from_dict(item)
                # Only look up an existing row when there's a real external_id
                # to match on. `Item.external_id == None` compiles to `IS
                # NULL`, which would match ANY prior item from the same
                # source/tenant that also has no external_id — silently
                # collapsing unrelated items (e.g. manually created ones)
                # into a single overwritten row instead of inserting each
                # one distinctly.
                existing = None
                if fields["external_id"] is not None:
                    result = await session.execute(
                        select(Item).where(
                            Item.source == fields["source"],
                            Item.external_id == fields["external_id"],
                            Item.tenant_id == fields["tenant_id"],
                        )
                    )
                    existing = result.scalar_one_or_none()
                ts = _parse_timestamp(item.get("timestamp"))
                if existing:
                    for key, value in fields.items():
                        setattr(existing, key, value)
                    if ts:
                        existing.created_at = ts
                else:
                    row = Item(id=item["id"], **fields)
                    if ts:
                        row.created_at = ts
                    session.add(row)
            await session.commit()
            return len(items)

    async def get_items(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(Item)
            if tenant_id:
                stmt = stmt.where(Item.tenant_id == tenant_id)
            result = await session.execute(stmt)
            return [_item_to_dict(r) for r in result.scalars().all()]

    async def delete_item(self, item_id: str, tenant_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(Item).where(Item.id == item_id, Item.tenant_id == tenant_id)
            )
            await session.commit()
            return result.rowcount > 0

    async def add_item(self, item: Dict[str, Any]) -> str:
        async with AsyncSessionLocal() as session:
            item_id = item.get("id") or str(uuid.uuid4())
            fields = _item_fields_from_dict(item)
            ts = _parse_timestamp(item.get("timestamp"))
            row = Item(id=item_id, **fields)
            if ts:
                row.created_at = ts
            session.add(row)
            await session.commit()
            return item_id

    async def enforce_retention_policy(self, days: int = 30) -> int:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=days)
        async with AsyncSessionLocal() as session:
            result = await session.execute(delete(Item).where(Item.created_at < cutoff))
            await session.commit()
            deleted = result.rowcount or 0
            if deleted > 0:
                logger.info(f"Retention Policy: Deleted {deleted} items older than {days} days.")
            return deleted

    async def archive_item(self, tenant_id: str, item_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Item).where(Item.id == item_id, Item.tenant_id == tenant_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return False
            row.is_archived = True
            await session.commit()
            return True

    async def snooze_item(self, tenant_id: str, item_id: str, until: datetime.datetime) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Item).where(Item.id == item_id, Item.tenant_id == tenant_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return False
            row.is_snoozed = True
            row.snoozed_until = until
            await session.commit()
            return True

    async def unsnooze_item(self, tenant_id: str, item_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Item).where(Item.id == item_id, Item.tenant_id == tenant_id)
            )
            row = result.scalar_one_or_none()
            if not row or not row.is_snoozed:
                return False
            row.is_snoozed = False
            row.snoozed_until = None
            await session.commit()
            return True

    async def bulk_archive_items(self, tenant_id: str, item_ids: List[str]) -> List[str]:
        """Archive many items in a single UPDATE statement instead of looping
        archive_item() N times. Returns the subset of item_ids that actually
        exist under this tenant (and were therefore archived)."""
        if not item_ids:
            return []
        async with AsyncSessionLocal() as session:
            existing_result = await session.execute(
                select(Item.id).where(Item.tenant_id == tenant_id, Item.id.in_(item_ids))
            )
            existing_ids = [r[0] for r in existing_result.all()]
            if not existing_ids:
                return []
            await session.execute(
                update(Item)
                .where(Item.tenant_id == tenant_id, Item.id.in_(existing_ids))
                .values(is_archived=True)
            )
            await session.commit()
            return existing_ids

    async def bulk_snooze_items(self, tenant_id: str, item_ids: List[str], until: datetime.datetime) -> List[str]:
        """Snooze many items in a single UPDATE statement instead of looping
        snooze_item() N times. Returns the subset of item_ids that actually
        exist under this tenant (and were therefore snoozed)."""
        if not item_ids:
            return []
        async with AsyncSessionLocal() as session:
            existing_result = await session.execute(
                select(Item.id).where(Item.tenant_id == tenant_id, Item.id.in_(item_ids))
            )
            existing_ids = [r[0] for r in existing_result.all()]
            if not existing_ids:
                return []
            await session.execute(
                update(Item)
                .where(Item.tenant_id == tenant_id, Item.id.in_(existing_ids))
                .values(is_snoozed=True, snoozed_until=until)
            )
            await session.commit()
            return existing_ids

    # ------------------------------------------------------------------
    # Audit log
    # ------------------------------------------------------------------
    async def add_audit_log(self, user_id: Optional[str], action: str, details: str) -> None:
        # user_id may be None for system-generated entries (automated
        # workflow actions, payment webhooks) — see AuditLog.user_id in
        # models.py, which is nullable for exactly this reason.
        async with AsyncSessionLocal() as session:
            session.add(AuditLog(user_id=user_id, action=action, details=details, timestamp=time.time()))
            await session.commit()
            logger.info(f"Audit Log: {action} by {user_id}")

    async def get_audit_logs(self, tenant_id: str) -> List[Dict[str, Any]]:
        # Preserves original semantics: filter audit logs by finding users
        # belonging to the given tenant_id, then matching their user ids.
        async with AsyncSessionLocal() as session:
            user_ids_result = await session.execute(select(User.id).where(User.tenant_id == tenant_id))
            user_ids = [r[0] for r in user_ids_result.all()]
            if not user_ids:
                return []
            result = await session.execute(
                select(AuditLog).where(AuditLog.user_id.in_(user_ids)).order_by(AuditLog.timestamp.asc())
            )
            rows = result.scalars().all()
            return [
                {"timestamp": r.timestamp, "user_id": r.user_id, "action": r.action, "details": r.details}
                for r in rows
            ]

    # ------------------------------------------------------------------
    # Integrations
    # ------------------------------------------------------------------
    async def get_connected_integrations(self, tenant_id: str) -> Dict[str, Dict[str, Any]]:
        """Raw (still-encrypted) per-provider config for a tenant, keyed by
        provider name — matches the shape of the old in-memory
        `connected_integrations[tenant_id]` dict that several routes accessed
        directly."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Integration).where(Integration.tenant_id == tenant_id))
            rows = result.scalars().all()
            return {r.provider: _integration_row_to_dict(r) for r in rows}

    async def connect_integration(self, tenant_id: str, provider: str, config: Dict[str, Any]) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Integration).where(Integration.tenant_id == tenant_id, Integration.provider == provider)
            )
            row = result.scalar_one_or_none()
            settings = config.get("settings") or {}
            token = config.get("token") or config.get("access_token")
            refresh_token = config.get("refresh_token")
            api_key = config.get("api_key")
            extra = {k: v for k, v in config.items() if k not in ("token", "access_token", "refresh_token", "api_key", "settings")}
            if row:
                row.enabled = settings.get("enabled", True)
                row.sync_frequency = settings.get("sync_frequency", 30)
                row.priority_threshold = settings.get("priority_threshold", 0)
                row.token = token
                row.refresh_token = refresh_token
                row.api_key = api_key
                row.config = extra
            else:
                session.add(Integration(
                    tenant_id=tenant_id,
                    provider=provider,
                    enabled=settings.get("enabled", True),
                    sync_frequency=settings.get("sync_frequency", 30),
                    priority_threshold=settings.get("priority_threshold", 0),
                    token=token,
                    refresh_token=refresh_token,
                    api_key=api_key,
                    config=extra,
                ))
            await session.commit()
            logger.info(f"Connected integration: {tenant_id}/{provider}")

    async def disconnect_integration(self, tenant_id: str, provider: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(Integration).where(Integration.tenant_id == tenant_id, Integration.provider == provider)
            )
            await session.commit()
            if result.rowcount > 0:
                logger.info(f"Disconnected integration: {tenant_id}/{provider}")
                return True
            return False

    async def save_integration_tokens(self, tenant_id: str, provider: str, tokens: Dict[str, Any]) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Integration).where(Integration.tenant_id == tenant_id, Integration.provider == provider)
            )
            row = result.scalar_one_or_none()
            if not row:
                row = Integration(
                    tenant_id=tenant_id, provider=provider,
                    enabled=True, sync_frequency=30, priority_threshold=0, config={},
                )
                session.add(row)

            extra = dict(row.config or {})
            for key, value in tokens.items():
                enc_value = encrypt_secret(str(value)) if key.lower() in _SENSITIVE_KEYS else value
                lower_key = key.lower()
                if lower_key in ("token", "access_token"):
                    row.token = enc_value
                elif lower_key == "refresh_token":
                    row.refresh_token = enc_value
                elif lower_key == "api_key":
                    row.api_key = enc_value
                else:
                    extra[key] = enc_value
            row.config = extra
            await session.commit()
            logger.info(f"Saved OAuth tokens for {tenant_id}/{provider}")
            return True

    async def update_integration_settings(self, tenant_id: str, provider: str, settings: Dict[str, Any]) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Integration).where(Integration.tenant_id == tenant_id, Integration.provider == provider)
            )
            row = result.scalar_one_or_none()
            if not row:
                return False
            if "enabled" in settings:
                row.enabled = settings["enabled"]
            if "sync_frequency" in settings:
                row.sync_frequency = settings["sync_frequency"]
            if "priority_threshold" in settings:
                row.priority_threshold = settings["priority_threshold"]
            await session.commit()
            logger.info(f"Updated integration settings: {tenant_id}/{provider} -> {settings}")
            return True

    async def get_integration_config(self, tenant_id: str, provider: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Integration).where(Integration.tenant_id == tenant_id, Integration.provider == provider)
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            raw = _integration_row_to_dict(row)
            decrypted = {}
            for key, value in raw.items():
                if key.lower() in _SENSITIVE_KEYS and value:
                    decrypted[key] = decrypt_secret(str(value))
                else:
                    decrypted[key] = value
            return decrypted

    # ------------------------------------------------------------------
    # Delegation & presence
    # ------------------------------------------------------------------
    async def delegate_item(self, item_id: str, tenant_id: str, to_user_id: str, assigned_by: str, note: str = "") -> bool:
        async with AsyncSessionLocal() as session:
            item_check = await session.execute(
                select(Item.id).where(Item.id == item_id, Item.tenant_id == tenant_id)
            )
            if item_check.first() is None:
                return False

            result = await session.execute(select(Delegation).where(Delegation.item_id == item_id))
            row = result.scalar_one_or_none()
            now = time.time()
            if row:
                row.assigned_to = to_user_id
                row.assigned_by = assigned_by
                row.note = note
                row.tenant_id = tenant_id
                row.timestamp = now
            else:
                session.add(Delegation(
                    item_id=item_id, tenant_id=tenant_id, assigned_to=to_user_id,
                    assigned_by=assigned_by, note=note, timestamp=now,
                ))
            await session.commit()
            return True

    async def get_delegation(self, item_id: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Delegation).where(Delegation.item_id == item_id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            return {
                "assigned_to": row.assigned_to,
                "assigned_by": row.assigned_by,
                "note": row.note,
                "timestamp": row.timestamp,
            }

    async def get_delegations_for_assignee(self, user_id: str) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Delegation).where(Delegation.assigned_to == user_id))
            rows = result.scalars().all()
            return [
                {"item_id": r.item_id, "assigned_to": r.assigned_to, "assigned_by": r.assigned_by,
                 "note": r.note, "timestamp": r.timestamp}
                for r in rows
            ]

    async def update_presence(self, item_id: str, user_id: str, action: str = "viewing") -> None:
        async with AsyncSessionLocal() as session:
            cutoff = time.time() - 60
            await session.execute(delete(Presence).where(Presence.item_id == item_id, Presence.timestamp < cutoff))
            result = await session.execute(
                select(Presence).where(Presence.item_id == item_id, Presence.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            now = time.time()
            if row:
                row.action = action
                row.timestamp = now
            else:
                session.add(Presence(item_id=item_id, user_id=user_id, action=action, timestamp=now))
            await session.commit()

    async def get_presence(self, item_id: str) -> Dict[str, Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            cutoff = time.time() - 60
            await session.execute(delete(Presence).where(Presence.item_id == item_id, Presence.timestamp < cutoff))
            await session.commit()
            result = await session.execute(select(Presence).where(Presence.item_id == item_id))
            rows = result.scalars().all()
            return {r.user_id: {"action": r.action, "timestamp": r.timestamp} for r in rows}

    # ------------------------------------------------------------------
    # Contact / project / client priorities
    # ------------------------------------------------------------------
    async def get_contact_priorities(self, tenant_id: str) -> Dict[str, Dict[str, str]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ContactPriority).where(ContactPriority.tenant_id == tenant_id))
            out: Dict[str, Dict[str, str]] = {}
            for r in result.scalars().all():
                out.setdefault(r.platform, {})[r.handle] = r.priority
            return out

    async def set_contact_priority(self, tenant_id: str, platform: str, handle: str, priority: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ContactPriority).where(
                    ContactPriority.tenant_id == tenant_id,
                    ContactPriority.platform == platform,
                    ContactPriority.handle == handle,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                row.priority = priority
            else:
                session.add(ContactPriority(tenant_id=tenant_id, platform=platform, handle=handle, priority=priority))
            await session.commit()
            return True

    async def delete_contact_priority(self, tenant_id: str, platform: str, handle: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(ContactPriority).where(
                    ContactPriority.tenant_id == tenant_id,
                    ContactPriority.platform == platform,
                    ContactPriority.handle == handle,
                )
            )
            await session.commit()
            return result.rowcount > 0

    async def get_project_priorities(self, tenant_id: str) -> Dict[str, str]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ProjectPriority).where(ProjectPriority.tenant_id == tenant_id))
            return {r.project_id: r.priority for r in result.scalars().all()}

    async def set_project_priority(self, tenant_id: str, project_id: str, priority: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ProjectPriority).where(ProjectPriority.tenant_id == tenant_id, ProjectPriority.project_id == project_id)
            )
            row = result.scalar_one_or_none()
            if row:
                row.priority = priority
            else:
                session.add(ProjectPriority(tenant_id=tenant_id, project_id=project_id, priority=priority))
            await session.commit()
            return True

    async def get_client_priorities(self, tenant_id: str) -> Dict[str, str]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ClientPriority).where(ClientPriority.tenant_id == tenant_id))
            return {r.client_id: r.priority for r in result.scalars().all()}

    async def set_client_priority(self, tenant_id: str, client_id: str, priority: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ClientPriority).where(ClientPriority.tenant_id == tenant_id, ClientPriority.client_id == client_id)
            )
            row = result.scalar_one_or_none()
            if row:
                row.priority = priority
            else:
                session.add(ClientPriority(tenant_id=tenant_id, client_id=client_id, priority=priority))
            await session.commit()
            return True

    # ------------------------------------------------------------------
    # Custom integrations (bug fix: GET /integrations/custom must return a
    # LIST, not a dict — the frontend calls .map() on it)
    # ------------------------------------------------------------------
    async def get_custom_integrations(self, tenant_id: str) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(CustomIntegration).where(CustomIntegration.tenant_id == tenant_id))
            rows = result.scalars().all()
            return [{"id": r.id, "name": r.name, **(r.config or {})} for r in rows]

    async def add_custom_integration(self, tenant_id: str, config: Dict[str, Any]) -> str:
        async with AsyncSessionLocal() as session:
            row = CustomIntegration(tenant_id=tenant_id, name=config.get("name", ""), config=config)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.id

    async def update_custom_integration(self, tenant_id: str, integration_id: str, config: Dict[str, Any]) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(CustomIntegration).where(CustomIntegration.tenant_id == tenant_id, CustomIntegration.id == integration_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return False
            merged = dict(row.config or {})
            merged.update(config)
            row.config = merged
            if "name" in config:
                row.name = config["name"]
            await session.commit()
            return True

    async def delete_custom_integration(self, tenant_id: str, integration_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(CustomIntegration).where(CustomIntegration.tenant_id == tenant_id, CustomIntegration.id == integration_id)
            )
            await session.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Workflows (shape unchanged: {workflow_id: workflow_dict})
    # ------------------------------------------------------------------
    async def get_workflows(self, tenant_id: str) -> Dict[str, Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Workflow).where(Workflow.tenant_id == tenant_id))
            return {r.id: {**(r.config or {}), "id": r.id} for r in result.scalars().all()}

    async def add_workflow(self, tenant_id: str, workflow: Dict[str, Any]) -> str:
        async with AsyncSessionLocal() as session:
            row = Workflow(tenant_id=tenant_id, config=workflow)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.id

    async def update_workflow(self, tenant_id: str, workflow_id: str, workflow: Dict[str, Any]) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Workflow).where(Workflow.tenant_id == tenant_id, Workflow.id == workflow_id)
            )
            row = result.scalar_one_or_none()
            if not row:
                return False
            merged = dict(row.config or {})
            merged.update(workflow)
            row.config = merged
            await session.commit()
            return True

    async def delete_workflow(self, tenant_id: str, workflow_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                delete(Workflow).where(Workflow.tenant_id == tenant_id, Workflow.id == workflow_id)
            )
            await session.commit()
            return result.rowcount > 0

    # ------------------------------------------------------------------
    # Billing
    # ------------------------------------------------------------------
    async def get_billing_info(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Billing).where(Billing.tenant_id == tenant_id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            return {
                "plan": row.plan,
                "subscription_id": row.subscription_id,
                "customer_id": row.customer_id,
                "usage": {
                    "active_integrations": row.usage_active_integrations,
                    "team_members": row.usage_team_members,
                    "ai_items_processed": row.usage_ai_items_processed,
                    "smart_responses": row.usage_smart_responses,
                },
                "limits": {
                    "active_integrations": row.limits_active_integrations,
                    "team_members": row.limits_team_members,
                    "ai_items_processed": row.limits_ai_items_processed,
                    "smart_responses": row.limits_smart_responses,
                },
            }

    async def update_billing_plan(self, tenant_id: str, plan: str, subscription_id: str = None, customer_id: str = None) -> bool:
        if plan not in self.PLAN_LIMITS:
            plan = "Free"
        limits = self.PLAN_LIMITS[plan]
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Billing).where(Billing.tenant_id == tenant_id))
            row = result.scalar_one_or_none()
            if not row:
                row = Billing(
                    tenant_id=tenant_id, plan=plan,
                    usage_active_integrations=0, usage_team_members=0,
                    usage_ai_items_processed=0, usage_smart_responses=0,
                )
                session.add(row)
            row.plan = plan
            if subscription_id:
                row.subscription_id = subscription_id
            if customer_id:
                row.customer_id = customer_id
            row.limits_active_integrations = limits["active_integrations"]
            row.limits_team_members = limits["team_members"]
            row.limits_ai_items_processed = limits["ai_items_processed"]
            row.limits_smart_responses = limits["smart_responses"]
            await session.commit()
            return True

    # ------------------------------------------------------------------
    # Custom / semantic weights
    # ------------------------------------------------------------------
    async def get_custom_weights(self, tenant_id: str) -> Dict[str, float]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(CustomWeight).where(CustomWeight.tenant_id == tenant_id))
            row = result.scalar_one_or_none()
            return dict(row.weights) if row else dict(self.DEFAULT_CUSTOM_WEIGHTS)

    async def set_custom_weights(self, tenant_id: str, weights: Dict[str, float]) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(CustomWeight).where(CustomWeight.tenant_id == tenant_id))
            row = result.scalar_one_or_none()
            if row:
                row.weights = weights
            else:
                session.add(CustomWeight(tenant_id=tenant_id, weights=weights))
            await session.commit()
            return True

    async def get_semantic_weights(self, tenant_id: str) -> Dict[str, float]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SemanticWeight).where(SemanticWeight.tenant_id == tenant_id))
            row = result.scalar_one_or_none()
            return dict(row.weights) if row else dict(self.DEFAULT_SEMANTIC_WEIGHTS)

    async def set_semantic_weights(self, tenant_id: str, weights: Dict[str, float]) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(SemanticWeight).where(SemanticWeight.tenant_id == tenant_id))
            row = result.scalar_one_or_none()
            if row:
                row.weights = weights
            else:
                session.add(SemanticWeight(tenant_id=tenant_id, weights=weights))
            await session.commit()
            return True

    # ------------------------------------------------------------------
    # MFA
    # ------------------------------------------------------------------
    async def set_mfa_pending_secret(self, user_id: str, secret: str) -> None:
        self._mfa_pending_secrets[user_id] = secret

    async def get_mfa_pending_secret(self, user_id: str) -> Optional[str]:
        return self._mfa_pending_secrets.get(user_id)

    async def clear_mfa_pending_secret(self, user_id: str) -> None:
        self._mfa_pending_secrets.pop(user_id, None)

    async def set_mfa_secret(self, user_id: str, secret: str) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            row = result.scalar_one_or_none()
            if row:
                row.mfa_secret = secret
                await session.commit()

    async def get_mfa_secret(self, user_id: str) -> Optional[str]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            row = result.scalar_one_or_none()
            return row.mfa_secret if row else None

    async def clear_mfa_secret(self, user_id: str) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            row = result.scalar_one_or_none()
            if row:
                row.mfa_secret = None
                await session.commit()

    async def set_mfa_recovery_codes(self, user_id: str, codes: List[str]) -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(MFARecoveryCode).where(MFARecoveryCode.user_id == user_id))
            for code in codes:
                session.add(MFARecoveryCode(user_id=user_id, hashed_code=code, used=False))
            await session.commit()

    async def get_mfa_recovery_codes(self, user_id: str) -> Optional[List[str]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MFARecoveryCode).where(MFARecoveryCode.user_id == user_id, MFARecoveryCode.used == False)  # noqa: E712
            )
            rows = result.scalars().all()
            if not rows:
                any_result = await session.execute(
                    select(MFARecoveryCode.id).where(MFARecoveryCode.user_id == user_id).limit(1)
                )
                if any_result.first() is None:
                    return None
                return []
            return [r.hashed_code for r in rows]

    async def clear_mfa_recovery_codes(self, user_id: str) -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(MFARecoveryCode).where(MFARecoveryCode.user_id == user_id))
            await session.commit()

    # ------------------------------------------------------------------
    # Failed logins / account lockout
    # ------------------------------------------------------------------
    async def get_lockout_expiry(self, user_id: str) -> Optional[float]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(LockedAccount).where(LockedAccount.user_id == user_id))
            row = result.scalar_one_or_none()
            return row.locked_until if row else None

    async def record_failed_login(self, user_id: str) -> None:
        async with AsyncSessionLocal() as session:
            session.add(FailedLogin(user_id=user_id, attempted_at=time.time()))
            await session.commit()

    async def count_recent_failed_logins(self, user_id: str, since_ts: float) -> int:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(FailedLogin).where(FailedLogin.user_id == user_id, FailedLogin.attempted_at > since_ts)
            )
            return len(result.scalars().all())

    async def lock_account(self, user_id: str, until_ts: float) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(LockedAccount).where(LockedAccount.user_id == user_id))
            row = result.scalar_one_or_none()
            if row:
                row.locked_until = until_ts
            else:
                session.add(LockedAccount(user_id=user_id, locked_until=until_ts))
            await session.commit()

    async def clear_failed_logins(self, user_id: str) -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(FailedLogin).where(FailedLogin.user_id == user_id))
            await session.commit()

    async def clear_lockout(self, user_id: str) -> None:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(LockedAccount).where(LockedAccount.user_id == user_id))
            await session.commit()

    # ------------------------------------------------------------------
    # Consent (event log) & DPDP granular preferences
    # ------------------------------------------------------------------
    async def record_consent(self, user_id: str, consent: Dict[str, Any]) -> None:
        async with AsyncSessionLocal() as session:
            session.add(ConsentRecord(
                user_id=user_id,
                version=str(consent.get("version", "")),
                purpose=str(consent.get("purpose", "")),
            ))
            await session.commit()

    async def get_consents(self, user_id: str) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ConsentRecord).where(ConsentRecord.user_id == user_id).order_by(ConsentRecord.timestamp.asc())
            )
            return [{"version": r.version, "purpose": r.purpose, "timestamp": r.timestamp} for r in result.scalars().all()]

    # Granular per-purpose consent preferences (DPDP + GDPR).
    #
    # ConsentRecord has no boolean "granted" column (its schema is
    # user_id/version/purpose/timestamp — an append-only consent event log).
    # To back the boolean per-purpose toggle without touching models.py, each
    # preference change is recorded as its own ConsentRecord row with
    # `purpose` = the consent purpose id (e.g. "ai_priority_scoring") and
    # `version` used as a state marker: "granted" or "revoked". The *current*
    # value of a purpose is the state marker of the most recent row for that
    # (user_id, purpose) pair. This intentionally shares the same table as
    # record_consent()/get_consents() above — a GDPR export via get_consents()
    # will show both kinds of rows, which is reasonable since both are
    # legitimately consent-related history for the user.
    async def get_consent_preferences(self, user_id: str) -> Dict[str, bool]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(ConsentRecord).where(ConsentRecord.user_id == user_id).order_by(ConsentRecord.timestamp.asc())
            )
            prefs: Dict[str, bool] = {}
            for row in result.scalars().all():
                if row.version in ("granted", "revoked"):
                    prefs[row.purpose] = (row.version == "granted")
            return prefs

    async def set_consent_preferences(self, user_id: str, prefs: Dict[str, bool]) -> None:
        async with AsyncSessionLocal() as session:
            for purpose, value in prefs.items():
                session.add(ConsentRecord(
                    user_id=user_id,
                    version="granted" if value else "revoked",
                    purpose=purpose,
                ))
            await session.commit()

    # ------------------------------------------------------------------
    # Nominee
    # ------------------------------------------------------------------
    async def set_nominee(self, user_id: str, nominee: Dict[str, str]) -> None:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Nominee).where(Nominee.user_id == user_id))
            row = result.scalar_one_or_none()
            if row:
                row.name = nominee["name"]
                row.email = nominee["email"]
                row.relationship = nominee["relationship"]
            else:
                session.add(Nominee(
                    user_id=user_id, name=nominee["name"], email=nominee["email"],
                    relationship=nominee["relationship"],
                ))
            await session.commit()

    async def get_nominee(self, user_id: str) -> Optional[Dict[str, str]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Nominee).where(Nominee.user_id == user_id))
            row = result.scalar_one_or_none()
            if not row:
                return None
            return {"name": row.name, "email": row.email, "relationship": row.relationship}

    # ------------------------------------------------------------------
    # Grievances
    # ------------------------------------------------------------------
    async def add_grievance(self, grievance: Dict[str, Any]) -> None:
        async with AsyncSessionLocal() as session:
            row = Grievance(
                user_id=grievance["user_id"],
                tenant_id=grievance["tenant_id"],
                subject=grievance["subject"],
                description=grievance["description"],
                status=grievance.get("status", "open"),
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            grievance["id"] = row.id

    async def get_grievances(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            stmt = select(Grievance)
            if user_id:
                stmt = stmt.where(Grievance.user_id == user_id)
            result = await session.execute(stmt)
            return [
                {
                    "id": r.id, "user_id": r.user_id, "tenant_id": r.tenant_id,
                    "subject": r.subject, "description": r.description, "status": r.status,
                }
                for r in result.scalars().all()
            ]

    async def resolve_grievance(self, grievance_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Grievance).where(Grievance.id == grievance_id))
            row = result.scalar_one_or_none()
            if not row:
                return False
            row.status = "resolved"
            await session.commit()
            return True

    # ------------------------------------------------------------------
    # GDPR/DPDP/CCPA erasure
    # ------------------------------------------------------------------
    async def delete_tenant_data(self, tenant_id: str) -> None:
        """Full cascade erasure of everything scoped to a tenant (bug fix:
        this method was called by privacy_routes.py but never existed).

        Deletes rows across every tenant-scoped table, plus every row keyed
        on user_id for users belonging to this tenant. Does NOT delete the
        Tenant row or any User rows — privacy_routes.py handles removing the
        specific requesting user separately via auth.models.delete_user().
        """
        async with AsyncSessionLocal() as session:
            user_ids_result = await session.execute(select(User.id).where(User.tenant_id == tenant_id))
            user_ids = [r[0] for r in user_ids_result.all()]

            item_ids_result = await session.execute(select(Item.id).where(Item.tenant_id == tenant_id))
            item_ids = [r[0] for r in item_ids_result.all()]

            # Tenant-scoped tables
            await session.execute(delete(Item).where(Item.tenant_id == tenant_id))
            await session.execute(delete(Integration).where(Integration.tenant_id == tenant_id))
            await session.execute(delete(Delegation).where(Delegation.tenant_id == tenant_id))
            await session.execute(delete(ContactPriority).where(ContactPriority.tenant_id == tenant_id))
            await session.execute(delete(ProjectPriority).where(ProjectPriority.tenant_id == tenant_id))
            await session.execute(delete(ClientPriority).where(ClientPriority.tenant_id == tenant_id))
            await session.execute(delete(CustomWeight).where(CustomWeight.tenant_id == tenant_id))
            await session.execute(delete(SemanticWeight).where(SemanticWeight.tenant_id == tenant_id))
            await session.execute(delete(CustomIntegration).where(CustomIntegration.tenant_id == tenant_id))
            await session.execute(delete(Workflow).where(Workflow.tenant_id == tenant_id))
            await session.execute(delete(Grievance).where(Grievance.tenant_id == tenant_id))

            if item_ids:
                await session.execute(delete(Presence).where(Presence.item_id.in_(item_ids)))
            if user_ids:
                await session.execute(delete(Presence).where(Presence.user_id.in_(user_ids)))
                await session.execute(delete(ConsentRecord).where(ConsentRecord.user_id.in_(user_ids)))
                await session.execute(delete(Nominee).where(Nominee.user_id.in_(user_ids)))
                await session.execute(delete(MFARecoveryCode).where(MFARecoveryCode.user_id.in_(user_ids)))
                await session.execute(delete(FailedLogin).where(FailedLogin.user_id.in_(user_ids)))
                await session.execute(delete(LockedAccount).where(LockedAccount.user_id.in_(user_ids)))
                await session.execute(delete(AuditLog).where(AuditLog.user_id.in_(user_ids)))

            await session.commit()

    async def delete_user_data(self, user_id: str) -> None:
        """Erase every row that references a single user (GDPR Art. 17
        individual erasure), as opposed to delete_tenant_data's tenant-wide
        cascade. Must run BEFORE auth.models.delete_user(user_id), because
        several tables have a NOT NULL foreign key to users.id (Grievance,
        AuditLog, MFARecoveryCode, FailedLogin, LockedAccount, ConsentRecord,
        Nominee, Delegation.assigned_by, Presence.user_id) — Postgres will
        reject the User delete while those rows still reference it.

        NOTE: unlike the old in-memory mock, this DELETES grievances rather
        than anonymizing them ("**ERASED**" sentinel user_id). Grievance.user_id
        is a NOT NULL foreign key in the real schema, so it cannot hold a
        placeholder string the way a free-form in-memory dict could.
        """
        async with AsyncSessionLocal() as session:
            await session.execute(delete(ConsentRecord).where(ConsentRecord.user_id == user_id))
            await session.execute(delete(Grievance).where(Grievance.user_id == user_id))
            await session.execute(delete(Nominee).where(Nominee.user_id == user_id))
            await session.execute(delete(MFARecoveryCode).where(MFARecoveryCode.user_id == user_id))
            await session.execute(delete(FailedLogin).where(FailedLogin.user_id == user_id))
            await session.execute(delete(LockedAccount).where(LockedAccount.user_id == user_id))
            await session.execute(delete(AuditLog).where(AuditLog.user_id == user_id))
            await session.execute(delete(Delegation).where(Delegation.assigned_by == user_id))
            await session.execute(delete(Delegation).where(Delegation.assigned_to == user_id))
            await session.execute(delete(Presence).where(Presence.user_id == user_id))
            await session.commit()

    # ------------------------------------------------------------------
    # Test/dev helper (out-of-scope test suites call this synchronously —
    # expected to break until the tests are migrated to async, per plan)
    # ------------------------------------------------------------------
    async def clear(self) -> None:
        async with AsyncSessionLocal() as session:
            for model in (
                Presence, Delegation, Item, Integration, ContactPriority, ProjectPriority,
                ClientPriority, CustomWeight, SemanticWeight, CustomIntegration, Workflow,
                ConsentRecord, Grievance, Nominee, MFARecoveryCode, FailedLogin,
                LockedAccount, AuditLog, Billing,
            ):
                await session.execute(delete(model))
            await session.commit()
        self._mfa_pending_secrets.clear()


db = MockDatabase()
