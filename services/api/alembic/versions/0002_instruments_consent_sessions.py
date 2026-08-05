"""instruments + consent + sessions families (consent before sessions: FK)

Revision ID: 0002_instruments_consent
Revises: 0001_identity_institutions
Create Date: 2026-08-05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0002_instruments_consent"
down_revision = "0001_identity_institutions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "instruments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "instrument_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("instrument_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_immutable", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.CheckConstraint("(status <> 'published') OR is_immutable", name="ck_published_versions_immutable"),
        sa.ForeignKeyConstraint(["instrument_id"], ["instruments.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instrument_id", "version_no", name="uq_version_no_per_instrument"),
    )
    op.create_index("ix_instrument_versions_instrument_id", "instrument_versions", ["instrument_id"], unique=False)
    op.create_table(
        "instrument_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("scale", sa.String(length=64), nullable=False),
        sa.Column("scale_order", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.CheckConstraint("scale_order BETWEEN 1 AND 5", name="ck_scale_order_1_to_5"),
        sa.ForeignKeyConstraint(["version_id"], ["instrument_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_id", "scale", "scale_order", name="uq_item_per_scale"),
    )
    op.create_index("ix_instrument_items_version_id", "instrument_items", ["version_id"], unique=False)
    op.create_table(
        "consent_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_no"),
    )
    op.create_table(
        "consent_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("consent_version_id", sa.Uuid(), nullable=False),
        sa.Column("state", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.CheckConstraint(
            "state IN ('pending','granted','revoked','expired')", name="ck_consent_state"
        ),
        sa.ForeignKeyConstraint(["consent_version_id"], ["consent_versions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "consent_version_id", name="uq_grant_per_user_version"),
    )
    op.create_index("ix_consent_grants_consent_version_id", "consent_grants", ["consent_version_id"], unique=False)
    op.create_index("ix_consent_grants_user_id", "consent_grants", ["user_id"], unique=False)
    op.create_table(
        "sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("instrument_version_id", sa.Uuid(), nullable=False),
        sa.Column("consent_grant_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="in_progress", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.CheckConstraint(
            "status IN ('in_progress','completed','blocked','cancelled')", name="ck_session_status"
        ),
        sa.ForeignKeyConstraint(["consent_grant_id"], ["consent_grants.id"]),
        sa.ForeignKeyConstraint(["instrument_version_id"], ["instrument_versions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sessions_consent_grant_id", "sessions", ["consent_grant_id"], unique=False)
    op.create_index("ix_sessions_instrument_version_id", "sessions", ["instrument_version_id"], unique=False)
    op.create_index("ix_sessions_user_started", "sessions", ["user_id", "started_at"], unique=False)
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_table(
        "responses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.CheckConstraint("value BETWEEN 1 AND 5", name="ck_value_1_to_5"),
        sa.ForeignKeyConstraint(["item_id"], ["instrument_items.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "item_id", name="uq_response_per_session_item"),
    )
    op.create_index("ix_responses_item_id", "responses", ["item_id"], unique=False)
    op.create_index("ix_responses_session_id", "responses", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_responses_session_id", table_name="responses")
    op.drop_index("ix_responses_item_id", table_name="responses")
    op.drop_table("responses")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_index("ix_sessions_user_started", table_name="sessions")
    op.drop_index("ix_sessions_instrument_version_id", table_name="sessions")
    op.drop_index("ix_sessions_consent_grant_id", table_name="sessions")
    op.drop_table("sessions")
    op.drop_index("ix_consent_grants_user_id", table_name="consent_grants")
    op.drop_index("ix_consent_grants_consent_version_id", table_name="consent_grants")
    op.drop_table("consent_grants")
    op.drop_table("consent_versions")
    op.drop_index("ix_instrument_items_version_id", table_name="instrument_items")
    op.drop_table("instrument_items")
    op.drop_index("ix_instrument_versions_instrument_id", table_name="instrument_versions")
    op.drop_table("instrument_versions")
    op.drop_table("instruments")
