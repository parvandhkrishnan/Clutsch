"""initial_schema

Revision ID: 001
Revises:
Create Date: 2026-07-10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Tenants ---
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain"),
    )

    # --- Users ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("mfa_secret", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_users_username"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"])
    op.create_index(op.f("ix_users_email"), "users", ["email"])
    op.create_index(op.f("ix_users_tenant_id"), "users", ["tenant_id"])

    # --- Items ---
    op.create_table(
        "items",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("sender_handle", sa.String(255), nullable=True),
        sa.Column("recipient", sa.String(255), nullable=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("thread_id", sa.String(255), nullable=True),
        sa.Column("priority_score", sa.Float(), nullable=True),
        sa.Column("priority_tier", sa.String(20), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("urgency", sa.Float(), nullable=True),
        sa.Column("importance", sa.Float(), nullable=True),
        sa.Column("action_suggested", sa.String(500), nullable=True),
        sa.Column("deadline", sa.String(100), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("item_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_snoozed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("snoozed_until", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_items_tenant_id"), "items", ["tenant_id"])
    op.create_index(op.f("ix_items_source"), "items", ["source"])
    op.create_index("ix_items_tenant_source", "items", ["tenant_id", "source"])
    op.create_index("ix_items_tenant_priority", "items", ["tenant_id", "priority_score"])

    # --- Integrations ---
    op.create_table(
        "integrations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("sync_frequency", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("priority_threshold", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token", sa.Text(), nullable=True),
        sa.Column("refresh_token", sa.Text(), nullable=True),
        sa.Column("api_key", sa.Text(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "provider", name="uq_tenant_provider"),
    )
    op.create_index(op.f("ix_integrations_tenant_id"), "integrations", ["tenant_id"])

    # --- Delegations ---
    op.create_table(
        "delegations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("assigned_to", sa.String(255), nullable=False),
        sa.Column("assigned_by", sa.String(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"],),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", name="uq_delegation_item"),
    )
    op.create_index(op.f("ix_delegations_item_id"), "delegations", ["item_id"])

    # --- Presence ---
    op.create_table(
        "presence",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(50), nullable=False, server_default="viewing"),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"],),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_presence_item_id"), "presence", ["item_id"])
    op.create_index("ix_presence_item_user", "presence", ["item_id", "user_id"])

    # --- Contact Priorities ---
    op.create_table(
        "contact_priorities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("platform", sa.String(50), nullable=False),
        sa.Column("handle", sa.String(255), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "platform", "handle", name="uq_contact_priority"),
    )
    op.create_index(op.f("ix_contact_priorities_tenant_id"), "contact_priorities", ["tenant_id"])

    # --- Project Priorities ---
    op.create_table(
        "project_priorities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("project_id", sa.String(255), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "project_id", name="uq_project_priority"),
    )
    op.create_index(op.f("ix_project_priorities_tenant_id"), "project_priorities", ["tenant_id"])

    # --- Client Priorities ---
    op.create_table(
        "client_priorities",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("client_id", sa.String(255), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "client_id", name="uq_client_priority"),
    )
    op.create_index(op.f("ix_client_priorities_tenant_id"), "client_priorities", ["tenant_id"])

    # --- Custom Weights ---
    op.create_table(
        "custom_weights",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("weights", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id"),
    )
    op.create_index(op.f("ix_custom_weights_tenant_id"), "custom_weights", ["tenant_id"])

    # --- Semantic Weights ---
    op.create_table(
        "semantic_weights",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("weights", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id"),
    )
    op.create_index(op.f("ix_semantic_weights_tenant_id"), "semantic_weights", ["tenant_id"])

    # --- Consent Records ---
    op.create_table(
        "consent_records",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("purpose", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_consent_records_user_id"), "consent_records", ["user_id"])

    # --- Grievances ---
    op.create_table(
        "grievances",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_grievances_user_id"), "grievances", ["user_id"])

    # --- Nominees ---
    op.create_table(
        "nominees",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("relationship", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_nominees_user_id"), "nominees", ["user_id"])

    # --- Audit Logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("timestamp", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_user_action", "audit_logs", ["user_id", "action"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])

    # --- Billing ---
    op.create_table(
        "billing",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="Free"),
        sa.Column("subscription_id", sa.String(255), nullable=True),
        sa.Column("customer_id", sa.String(255), nullable=True),
        sa.Column("usage_active_integrations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage_team_members", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("usage_ai_items_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("usage_smart_responses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("limits_active_integrations", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("limits_team_members", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("limits_ai_items_processed", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("limits_smart_responses", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id"),
    )
    op.create_index(op.f("ix_billing_tenant_id"), "billing", ["tenant_id"])

    # --- Custom Integrations ---
    op.create_table(
        "custom_integrations",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_custom_integrations_tenant_id"), "custom_integrations", ["tenant_id"])

    # --- Workflows ---
    op.create_table(
        "workflows",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_workflows_tenant_id"), "workflows", ["tenant_id"])

    # --- MFA Recovery Codes ---
    op.create_table(
        "mfa_recovery_codes",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("hashed_code", sa.String(255), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mfa_recovery_codes_user_id"), "mfa_recovery_codes", ["user_id"])
    op.create_index("ix_mfa_codes_user", "mfa_recovery_codes", ["user_id", "used"])

    # --- Failed Logins ---
    op.create_table(
        "failed_logins",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("attempted_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_failed_logins_user_id"), "failed_logins", ["user_id"])
    op.create_index("ix_failed_logins_user_time", "failed_logins", ["user_id", "attempted_at"])

    # --- Locked Accounts ---
    op.create_table(
        "locked_accounts",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("locked_until", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"],),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_locked_accounts_user_id"), "locked_accounts", ["user_id"])


def downgrade() -> None:
    op.drop_table("locked_accounts")
    op.drop_table("failed_logins")
    op.drop_table("mfa_recovery_codes")
    op.drop_table("workflows")
    op.drop_table("custom_integrations")
    op.drop_table("billing")
    op.drop_table("audit_logs")
    op.drop_table("nominees")
    op.drop_table("grievances")
    op.drop_table("consent_records")
    op.drop_table("semantic_weights")
    op.drop_table("custom_weights")
    op.drop_table("client_priorities")
    op.drop_table("project_priorities")
    op.drop_table("contact_priorities")
    op.drop_table("presence")
    op.drop_table("delegations")
    op.drop_table("integrations")
    op.drop_table("items")
    op.drop_table("users")
    op.drop_table("tenants")