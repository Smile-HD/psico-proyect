"""append-only audit: trigger + app role grants

- DB trigger rejects UPDATE/DELETE on audit_log (survives app bugs).
- The app role (psico_app) is granted INSERT + SELECT on audit_log only;
  there are no audit mutation endpoints. In dev compose the API connects as
  psico_app, so this grant documents the contract; the trigger is the
  enforcement.

Revision ID: 0004_audit_append_only_trigger
Revises: 0003_scoring_recommendation
Create Date: 2026-08-05
"""
from __future__ import annotations

from alembic import op

revision = "0004_audit_append_only_trigger"
down_revision = "0003_scoring_recommendation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'audit_log is append-only: UPDATE/DELETE is not allowed';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_audit_append_only
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_append_only();
        """
    )
    # App role exists only if the db was created with a different owner; guard
    # so the migration is idempotent across dev compose setups.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'psico_app') THEN
                CREATE ROLE psico_app;
            END IF;
        END
        $$;
        """
    )
    op.execute("GRANT INSERT, SELECT ON audit_log TO psico_app;")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_append_only ON audit_log;")
    op.execute("DROP FUNCTION IF EXISTS audit_append_only();")
    op.execute("REVOKE INSERT, SELECT ON audit_log FROM psico_app;")
