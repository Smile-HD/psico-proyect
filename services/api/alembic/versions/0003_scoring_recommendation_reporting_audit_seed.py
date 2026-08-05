"""scoring + recommendation (F5) + reporting (F6) + audit + seed families

F5/F6 tables are created empty-but-migrated.

Revision ID: 0003_scoring_recommendation_reporting_audit_seed
Revises: 0002_instruments_consent_sessions
Create Date: 2026-08-05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0003_scoring_recommendation_reporting_audit_seed"
down_revision = "0002_instruments_consent_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reference_sets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("instrument_version_id", sa.Uuid(), nullable=True),
        sa.Column("reference_status", sa.String(length=16), nullable=False),
        sa.Column("use", sa.String(length=32), server_default="research-only", nullable=False),
        sa.Column("norm_note", sa.Text(), nullable=True),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.CheckConstraint("reference_status IN ('synthetic','real')", name="ck_reference_status"),
        sa.ForeignKeyConstraint(["instrument_version_id"], ["instrument_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_reference_sets_instrument_version_id", "reference_sets", ["instrument_version_id"], unique=False)
    op.create_table(
        "reference_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reference_set_id", sa.Uuid(), nullable=False),
        sa.Column("scale", sa.String(length=64), nullable=False),
        sa.Column("value_type", sa.String(length=32), nullable=False),
        sa.Column("raw_value", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("transformed_value", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("percentile", sa.Integer(), nullable=True),
        sa.Column("t_score", sa.Integer(), nullable=True),
        sa.Column("eneatype", sa.Integer(), nullable=True),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.ForeignKeyConstraint(["reference_set_id"], ["reference_sets.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("reference_set_id", "scale", "value_type", name="uq_reference_value"),
    )
    op.create_index("ix_reference_values_reference_set_id", "reference_values", ["reference_set_id"], unique=False)
    op.create_table(
        "score_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("reference_set_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("raw", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.ForeignKeyConstraint(["reference_set_id"], ["reference_sets.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_score_runs_reference_set_id", "score_runs", ["reference_set_id"], unique=False)
    op.create_index("ix_score_runs_session_id", "score_runs", ["session_id"], unique=False)
    op.create_table(
        "recommendation_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("rule_type", sa.String(length=64), nullable=False),
        sa.Column("params", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendation_rules_program_id", "recommendation_rules", ["program_id"], unique=False)
    op.create_table(
        "recommendation_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("program_id", sa.Uuid(), nullable=False),
        sa.Column("fit_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["programs.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["recommendation_rules.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendation_results_program_id", "recommendation_results", ["program_id"], unique=False)
    op.create_index("ix_recommendation_results_rule_id", "recommendation_results", ["rule_id"], unique=False)
    op.create_index("ix_recommendation_results_session_id", "recommendation_results", ["session_id"], unique=False)
    op.create_table(
        "report_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("template_body", sa.Text(), nullable=True),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_table(
        "reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("format", sa.String(length=16), server_default="pdf", nullable=False),
        sa.Column("status", sa.String(length=16), server_default="pending", nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("source", sa.String(length=32), server_default="runtime", nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["report_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reports_session_id", "reports", ["session_id"], unique=False)
    op.create_index("ix_reports_template_id", "reports", ["template_id"], unique=False)
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_role", sa.String(length=64), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=True),
        sa.Column("outcome", sa.String(length=16), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.CheckConstraint("outcome IN ('allowed','denied')", name="ck_audit_outcome"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_actor_user_id", "audit_log", ["actor_user_id"], unique=False)
    op.create_index("ix_audit_log_event_occurred", "audit_log", ["event_type", "occurred_at"], unique=False)
    op.create_index("ix_audit_log_event_type", "audit_log", ["event_type"], unique=False)
    op.create_table(
        "seed_manifest",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("seed_version", sa.String(length=32), nullable=False),
        sa.Column("counts", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("seed_manifest")
    op.drop_index("ix_audit_log_event_type", table_name="audit_log")
    op.drop_index("ix_audit_log_event_occurred", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_user_id", table_name="audit_log")
    op.drop_table("audit_log")
    op.drop_index("ix_reports_template_id", table_name="reports")
    op.drop_index("ix_reports_session_id", table_name="reports")
    op.drop_table("reports")
    op.drop_table("report_templates")
    op.drop_index("ix_recommendation_results_session_id", table_name="recommendation_results")
    op.drop_index("ix_recommendation_results_rule_id", table_name="recommendation_results")
    op.drop_index("ix_recommendation_results_program_id", table_name="recommendation_results")
    op.drop_table("recommendation_results")
    op.drop_index("ix_recommendation_rules_program_id", table_name="recommendation_rules")
    op.drop_table("recommendation_rules")
    op.drop_index("ix_score_runs_session_id", table_name="score_runs")
    op.drop_index("ix_score_runs_reference_set_id", table_name="score_runs")
    op.drop_table("score_runs")
    op.drop_index("ix_reference_values_reference_set_id", table_name="reference_values")
    op.drop_table("reference_values")
    op.drop_index("ix_reference_sets_instrument_version_id", table_name="reference_sets")
    op.drop_table("reference_sets")
