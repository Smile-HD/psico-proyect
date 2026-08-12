"""Add traceable report persistence and immutable template versions.

Revision ID: 0006_reports_pdf
Revises: 0005_catalog_four_level
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_reports_pdf"
down_revision = "0005_catalog_four_level"
branch_labels = None
depends_on = None


def _install_template_immutability_trigger() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION report_template_published_immutability_guard()
        RETURNS trigger AS $$
        BEGIN
            IF current_setting('app.seed_reset', true) = 'on' THEN
                IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
            END IF;

            IF TG_OP = 'DELETE' THEN
                IF OLD.status IN ('published', 'retired') THEN
                    RAISE EXCEPTION 'report template version is immutable';
                END IF;
                RETURN OLD;
            END IF;

            IF OLD.status IN ('published', 'retired') THEN
                IF NEW.key IS NOT DISTINCT FROM OLD.key
                   AND NEW.name IS NOT DISTINCT FROM OLD.name
                   AND NEW.description IS NOT DISTINCT FROM OLD.description
                   AND NEW.template_body IS NOT DISTINCT FROM OLD.template_body
                   AND NEW.version_no = OLD.version_no
                   AND NEW.synthetic = OLD.synthetic
                   AND NEW.source IS NOT DISTINCT FROM OLD.source
                   AND (
                       NEW.status = OLD.status
                       OR (OLD.status = 'published' AND NEW.status = 'retired')
                   ) THEN
                    RETURN NEW;
                END IF;
                RAISE EXCEPTION 'report template version is immutable';
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_report_template_published_immutability
        BEFORE UPDATE OR DELETE ON report_templates
        FOR EACH ROW
        EXECUTE FUNCTION report_template_published_immutability_guard();
        """
    )


def upgrade() -> None:
    # 0003 created a single-key unique constraint. Versioned templates replace
    # that invariant with one unique version number per logical template key.
    op.execute(
        "ALTER TABLE report_templates "
        "DROP CONSTRAINT IF EXISTS report_templates_key_key"
    )
    op.add_column(
        "report_templates",
        sa.Column("version_no", sa.Integer(), server_default=sa.text("1"), nullable=False),
    )
    op.add_column(
        "report_templates",
        sa.Column(
            "status",
            sa.String(length=16),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
    )
    op.create_unique_constraint(
        "uq_report_template_key_version",
        "report_templates",
        ["key", "version_no"],
    )
    op.create_check_constraint(
        "ck_report_template_status",
        "report_templates",
        "status IN ('draft','published','retired')",
    )
    op.create_check_constraint(
        "ck_report_template_version_positive",
        "report_templates",
        "version_no > 0",
    )

    op.add_column(
        "reports",
        sa.Column("score_run_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("recommendation_snapshot", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column("template_version_no", sa.Integer(), nullable=True),
    )
    op.add_column("reports", sa.Column("storage_key", sa.String(length=255), nullable=True))
    op.add_column("reports", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.add_column("reports", sa.Column("byte_size", sa.Integer(), nullable=True))
    op.add_column("reports", sa.Column("media_type", sa.String(length=128), nullable=True))
    op.add_column(
        "reports",
        sa.Column("renderer_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "reports",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "reports",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column("reports", sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_reports_score_run_id",
        "reports",
        "score_runs",
        ["score_run_id"],
        ["id"],
    )
    op.create_index("ix_reports_score_run_id", "reports", ["score_run_id"], unique=False)
    op.create_check_constraint(
        "ck_report_status",
        "reports",
        "status IN ('pending','processing','ready','failed')",
    )
    op.create_check_constraint("ck_report_format", "reports", "format = 'pdf'")
    op.create_check_constraint(
        "ck_report_ready_artifact",
        "reports",
        "status <> 'ready' OR ("
        "storage_key IS NOT NULL AND sha256 IS NOT NULL AND byte_size IS NOT NULL "
        "AND media_type IS NOT NULL AND renderer_version IS NOT NULL "
        "AND generated_at IS NOT NULL AND failed_at IS NULL"
        ")",
    )
    op.create_check_constraint(
        "ck_report_failed_without_artifact",
        "reports",
        "status <> 'failed' OR ("
        "storage_key IS NULL AND sha256 IS NULL AND byte_size IS NULL "
        "AND media_type IS NULL AND renderer_version IS NULL "
        "AND generated_at IS NULL AND failed_at IS NOT NULL"
        ")",
    )

    _install_template_immutability_trigger()

    op.create_table(
        "report_artifacts",
        sa.Column("storage_key", sa.String(length=36), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("payload", sa.LargeBinary(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("storage_key"),
        sa.UniqueConstraint("report_id", name="uq_report_artifact_report"),
        sa.CheckConstraint(
            "byte_size >= 0",
            name="ck_report_artifact_byte_size_nonnegative",
        ),
    )


def downgrade() -> None:
    op.drop_table("report_artifacts")

    op.execute(
        "DROP TRIGGER IF EXISTS trg_report_template_published_immutability "
        "ON report_templates"
    )
    op.execute(
        "DROP FUNCTION IF EXISTS report_template_published_immutability_guard()"
    )

    op.drop_constraint("ck_report_failed_without_artifact", "reports", type_="check")
    op.drop_constraint("ck_report_ready_artifact", "reports", type_="check")
    op.drop_constraint("ck_report_format", "reports", type_="check")
    op.drop_constraint("ck_report_status", "reports", type_="check")
    op.drop_index("ix_reports_score_run_id", table_name="reports")
    op.drop_constraint("fk_reports_score_run_id", "reports", type_="foreignkey")
    for column in (
        "failed_at",
        "updated_at",
        "created_at",
        "renderer_version",
        "media_type",
        "byte_size",
        "sha256",
        "storage_key",
        "template_version_no",
        "recommendation_snapshot",
        "score_run_id",
    ):
        op.drop_column("reports", column)

    op.drop_constraint(
        "ck_report_template_version_positive", "report_templates", type_="check"
    )
    op.drop_constraint("ck_report_template_status", "report_templates", type_="check")
    op.drop_constraint(
        "uq_report_template_key_version", "report_templates", type_="unique"
    )
    op.drop_column("report_templates", "status")
    op.drop_column("report_templates", "version_no")
    op.create_unique_constraint(
        "report_templates_key_key", "report_templates", ["key"]
    )
