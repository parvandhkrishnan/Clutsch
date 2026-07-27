"""SQLAlchemy ORM models for Clutsch."""
import uuid
import time
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, 
    ForeignKey, JSON, UniqueConstraint, Index, BigInteger, Enum as SAEnum
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY


class Base(DeclarativeBase):
    pass


def gen_uuid():
    return str(uuid.uuid4())


def gen_ts():
    return time.time()


# ----- Users & Tenants -----

class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="tenant")
    billing = relationship("Billing", uselist=False, back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    username = Column(String(100), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="user")
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    mfa_secret = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
    )

    tenant = relationship("Tenant", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")
    consent_records = relationship("ConsentRecord", back_populates="user")
    grievances = relationship("Grievance", back_populates="user")


# ----- Items / Communications -----

class Item(Base):
    __tablename__ = "items"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    external_id = Column(String(255), nullable=True)
    source = Column(String(50), nullable=False, index=True)
    text = Column(Text, nullable=False)
    sender_name = Column(String(255), nullable=True)
    sender_handle = Column(String(255), nullable=True)
    recipient = Column(String(255), nullable=True)
    subject = Column(String(500), nullable=True)
    thread_id = Column(String(255), nullable=True)
    priority_score = Column(Float, nullable=True)
    priority_tier = Column(String(20), nullable=True)
    ai_summary = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    urgency = Column(Float, nullable=True)
    importance = Column(Float, nullable=True)
    action_suggested = Column(String(500), nullable=True)
    deadline = Column(String(100), nullable=True)
    source_url = Column(Text, nullable=True)
    item_metadata = Column("item_metadata", JSONB, nullable=True, default=dict)
    is_archived = Column(Boolean, nullable=False, default=False)
    is_snoozed = Column(Boolean, nullable=False, default=False)
    snoozed_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_items_tenant_source", "tenant_id", "source"),
        Index("ix_items_tenant_priority", "tenant_id", "priority_score"),
    )


# ----- Integrations -----

class Integration(Base):
    __tablename__ = "integrations"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    sync_frequency = Column(Integer, nullable=False, default=30)
    priority_threshold = Column(Integer, nullable=False, default=0)
    token = Column(Text, nullable=True)  # encrypted at rest
    refresh_token = Column(Text, nullable=True)
    api_key = Column(Text, nullable=True)
    config = Column(JSONB, nullable=True, default=dict)
    last_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uq_tenant_provider"),
    )


# ----- Delegations & Presence -----

class Delegation(Base):
    __tablename__ = "delegations"

    id = Column(String, primary_key=True, default=gen_uuid)
    item_id = Column(String, ForeignKey("items.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    assigned_to = Column(String(255), nullable=False)
    assigned_by = Column(String, ForeignKey("users.id"), nullable=False)
    note = Column(Text, nullable=True)
    timestamp = Column(BigInteger, nullable=False, default=gen_ts)

    __table_args__ = (
        UniqueConstraint("item_id", name="uq_delegation_item"),
    )


class Presence(Base):
    __tablename__ = "presence"

    id = Column(String, primary_key=True, default=gen_uuid)
    item_id = Column(String, ForeignKey("items.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False, default="viewing")
    timestamp = Column(BigInteger, nullable=False, default=gen_ts)

    __table_args__ = (
        Index("ix_presence_item_user", "item_id", "user_id"),
    )


# ----- Contact / Project / Client Priorities -----

class ContactPriority(Base):
    __tablename__ = "contact_priorities"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    handle = Column(String(255), nullable=False)
    priority = Column(String(20), nullable=False, default="medium")

    __table_args__ = (
        UniqueConstraint("tenant_id", "platform", "handle", name="uq_contact_priority"),
    )


class ProjectPriority(Base):
    __tablename__ = "project_priorities"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    project_id = Column(String(255), nullable=False)
    priority = Column(String(20), nullable=False, default="medium")

    __table_args__ = (
        UniqueConstraint("tenant_id", "project_id", name="uq_project_priority"),
    )


class ClientPriority(Base):
    __tablename__ = "client_priorities"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    client_id = Column(String(255), nullable=False)
    priority = Column(String(20), nullable=False, default="medium")

    __table_args__ = (
        UniqueConstraint("tenant_id", "client_id", name="uq_client_priority"),
    )


# ----- Scoring & Preferences -----

class CustomWeight(Base):
    __tablename__ = "custom_weights"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    weights = Column(JSONB, nullable=False, default=dict)


class SemanticWeight(Base):
    __tablename__ = "semantic_weights"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    weights = Column(JSONB, nullable=False, default=dict)


# ----- Consent & DPDP Compliance -----

class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    version = Column(String(20), nullable=False)
    purpose = Column(String(255), nullable=False)
    timestamp = Column(BigInteger, nullable=False, default=gen_ts)

    user = relationship("User", back_populates="consent_records")


class Grievance(Base):
    __tablename__ = "grievances"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="grievances")


class Nominee(Base):
    __tablename__ = "nominees"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    relationship = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ----- Audit Log -----

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    timestamp = Column(BigInteger, nullable=False, default=gen_ts)

    user = relationship("User", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_user_action", "user_id", "action"),
        Index("ix_audit_logs_timestamp", "timestamp"),
    )


# ----- Billing / Subscriptions -----

class Billing(Base):
    __tablename__ = "billing"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, unique=True, index=True)
    plan = Column(String(50), nullable=False, default="Free")
    subscription_id = Column(String(255), nullable=True)
    customer_id = Column(String(255), nullable=True)
    usage_active_integrations = Column(Integer, nullable=False, default=0)
    usage_team_members = Column(Integer, nullable=False, default=1)
    usage_ai_items_processed = Column(Integer, nullable=False, default=0)
    usage_smart_responses = Column(Integer, nullable=False, default=0)
    limits_active_integrations = Column(Integer, nullable=False, default=2)
    limits_team_members = Column(Integer, nullable=False, default=1)
    limits_ai_items_processed = Column(Integer, nullable=False, default=50)
    limits_smart_responses = Column(Integer, nullable=False, default=5)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="billing")


# ----- Custom Integrations -----

class CustomIntegration(Base):
    __tablename__ = "custom_integrations"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    config = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ----- Workflows -----

class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String, primary_key=True, default=gen_uuid)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    config = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ----- MFA Recovery Codes -----

class MFARecoveryCode(Base):
    __tablename__ = "mfa_recovery_codes"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    hashed_code = Column(String(255), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_mfa_codes_user", "user_id", "used"),
    )


# ----- Failed Login Attempts (for rate limiting) -----

class FailedLogin(Base):
    __tablename__ = "failed_logins"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    ip_address = Column(String(50), nullable=True)
    attempted_at = Column(BigInteger, nullable=False, default=gen_ts)

    __table_args__ = (
        Index("ix_failed_logins_user_time", "user_id", "attempted_at"),
    )


class LockedAccount(Base):
    __tablename__ = "locked_accounts"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    locked_until = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)