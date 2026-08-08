"""Add the four-level synthetic instrument catalog.

Revision ID: 0005_catalog_four_level
Revises: 0004_audit_append_only_trigger

The migration is deliberately linear and transactional. It keeps the physical
``instrument_items`` table so existing response and session references remain
valid, while replacing its denormalized scale fields with a normalized graph.
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_catalog_four_level"
down_revision = "0004_audit_append_only_trigger"
branch_labels = None
depends_on = None

SEED_SCALE_ORDER = {
    "Intereses": 1,
    "Aptitud verbal": 2,
    "Aptitud numérica": 3,
    "Razonamiento abstracto": 4,
    "Valores/preferencias": 5,
}
SEED_OPTION_LABELS = (
    "Nunca",
    "Casi nunca",
    "A veces",
    "Casi siempre",
    "Siempre",
)


def _seed_id(key: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"psico-seed:{key}")


def _create_catalog_tables() -> None:
    op.create_table(
        "scales",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("version_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("locale", sa.String(length=10), server_default="es", nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column(
            "synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "source", sa.String(length=32), server_default="runtime", nullable=False
        ),
        sa.ForeignKeyConstraint(["version_id"], ["instrument_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "version_id", "display_order", name="uq_scales_version_order"
        ),
        sa.UniqueConstraint("id", "version_id", name="uq_scales_id_version"),
        sa.CheckConstraint("display_order > 0", name="ck_scale_display_order_positive"),
    )
    op.create_index("ix_scales_version_id", "scales", ["version_id"], unique=False)

    op.create_table(
        "response_options",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("locale", sa.String(length=10), server_default="es", nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column(
            "synthetic", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "source", sa.String(length=32), server_default="runtime", nullable=False
        ),
        sa.ForeignKeyConstraint(["item_id"], ["instrument_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", "display_order", name="uq_option_item_order"),
        sa.UniqueConstraint("item_id", "value", name="uq_option_item_value"),
        sa.CheckConstraint(
            "display_order BETWEEN 1 AND 5", name="ck_option_display_order_1_to_5"
        ),
        sa.CheckConstraint("value BETWEEN 1 AND 5", name="ck_option_value_1_to_5"),
    )
    op.create_index(
        "ix_response_options_item_id", "response_options", ["item_id"], unique=False
    )

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("resource_scope", sa.String(length=160), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("response_status", sa.SmallInteger(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "actor_user_id",
            "operation",
            "resource_scope",
            "idempotency_key",
            name="uq_idempotency_scope",
        ),
    )
    op.create_index(
        "ix_idempotency_records_actor_user_id",
        "idempotency_records",
        ["actor_user_id"],
        unique=False,
    )


def _add_version_and_item_columns() -> None:
    op.add_column(
        "instrument_versions",
        sa.Column(
            "response_type",
            sa.String(length=32),
            server_default="likert_1_5",
            nullable=True,
        ),
    )
    op.add_column(
        "instrument_versions",
        sa.Column("adaptation_metadata", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "instrument_versions",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.add_column(
        "instrument_versions",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.add_column(
        "instrument_versions",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE instrument_versions "
            "SET response_type = 'likert_1_5', "
            "created_at = COALESCE(published_at, CURRENT_TIMESTAMP), "
            "updated_at = COALESCE(published_at, CURRENT_TIMESTAMP)"
        )
    )
    op.alter_column("instrument_versions", "response_type", nullable=False)
    op.alter_column("instrument_versions", "created_at", nullable=False)
    op.alter_column("instrument_versions", "updated_at", nullable=False)

    connection.execute(
        sa.text(
            "SELECT id, status FROM instrument_versions "
            "WHERE status NOT IN ('draft', 'published', 'archived')"
        )
    ).all()
    op.drop_constraint(
        "ck_published_versions_immutable", "instrument_versions", type_="check"
    )
    op.create_check_constraint(
        "ck_instrument_version_status",
        "instrument_versions",
        "status IN ('draft', 'published', 'archived')",
    )
    op.create_check_constraint(
        "ck_published_versions_immutable",
        "instrument_versions",
        "((status = 'draft' AND is_immutable = false) OR "
        "(status IN ('published', 'archived') AND is_immutable = true))",
    )

    op.add_column("instrument_items", sa.Column("scale_id", sa.Uuid(), nullable=True))
    op.add_column(
        "instrument_items", sa.Column("item_order", sa.Integer(), nullable=True)
    )
    op.add_column(
        "instrument_items", sa.Column("locale", sa.String(length=10), nullable=True)
    )
    op.add_column(
        "instrument_items", sa.Column("required", sa.Boolean(), nullable=True)
    )


def _backfill_catalog_graph() -> None:
    connection = op.get_bind()
    versions = (
        connection.execute(
            sa.text(
                "SELECT iv.id, iv.instrument_id, iv.source AS version_source, "
                "i.key AS instrument_key, i.source AS instrument_source "
                "FROM instrument_versions iv JOIN instruments i ON i.id = iv.instrument_id"
            )
        )
        .mappings()
        .all()
    )
    version_info = {row["id"]: row for row in versions}

    item_rows = (
        connection.execute(
            sa.text(
                "SELECT id, version_id, scale, scale_order, synthetic, source "
                "FROM instrument_items ORDER BY version_id, scale_order, id"
            )
        )
        .mappings()
        .all()
    )

    groups: dict[tuple[uuid.UUID, str], list[dict]] = {}
    for row in item_rows:
        groups.setdefault((row["version_id"], row["scale"]), []).append(row)

    scale_ids: dict[tuple[uuid.UUID, str], uuid.UUID] = {}
    nonseed_orders: dict[tuple[uuid.UUID, str], int] = {}
    for version_id in version_info:
        version_groups = [
            (key, rows) for key, rows in groups.items() if key[0] == version_id
        ]
        version_groups.sort(
            key=lambda pair: (
                min(row["scale_order"] for row in pair[1]),
                str(pair[0][1]),
            )
        )
        for display_order, (key, _rows) in enumerate(version_groups, start=1):
            nonseed_orders[key] = display_order

    for (version_id, scale_label), rows in groups.items():
        info = version_info[version_id]
        is_seed = info["instrument_key"] == "TP-S-01"
        if is_seed:
            if scale_label not in SEED_SCALE_ORDER:
                raise RuntimeError(f"unknown TP-S-01 seed scale: {scale_label}")
            display_order = SEED_SCALE_ORDER[scale_label]
            scale_id = _seed_id(f"TP-S-01:scale:{scale_label}")
            synthetic = True
            source = "seed"
        else:
            display_order = nonseed_orders[(version_id, scale_label)]
            scale_id = uuid.uuid4()
            synthetic = all(row["synthetic"] for row in rows)
            source = "runtime"

        connection.execute(
            sa.text(
                "INSERT INTO scales "
                "(id, version_id, label, locale, display_order, synthetic, source) "
                "VALUES (:id, :version_id, :label, 'es', :display_order, "
                ":synthetic, :source)"
            ),
            {
                "id": scale_id,
                "version_id": version_id,
                "label": scale_label,
                "display_order": display_order,
                "synthetic": synthetic,
                "source": source,
            },
        )
        scale_ids[(version_id, scale_label)] = scale_id

    seed_item_ids = {_seed_id(f"TP-S-01:i{index}"): index for index in range(1, 21)}
    for row in item_rows:
        version_id = row["version_id"]
        info = version_info[version_id]
        scale_id = scale_ids[(version_id, row["scale"])]
        connection.execute(
            sa.text(
                "UPDATE instrument_items SET scale_id = :scale_id, item_order = :item_order, "
                "locale = 'es', required = true WHERE id = :id"
            ),
            {"scale_id": scale_id, "item_order": row["scale_order"], "id": row["id"]},
        )

        is_seed = (
            info["instrument_key"] == "TP-S-01"
            or info["version_source"] == "seed"
            or info["instrument_source"] == "seed"
        )
        seed_index = seed_item_ids.get(row["id"])
        if is_seed and seed_index is None:
            raise RuntimeError(f"unknown TP-S-01 seed item id: {row['id']}")
        for value, label in enumerate(SEED_OPTION_LABELS, start=1):
            option_id = (
                _seed_id(f"TP-S-01:i{seed_index}:option:{value}")
                if is_seed
                else uuid.uuid4()
            )
            connection.execute(
                sa.text(
                    "INSERT INTO response_options "
                    "(id, item_id, label, locale, display_order, value, synthetic, source) "
                    "VALUES (:id, :item_id, :label, 'es', :display_order, :value, "
                    ":synthetic, :source)"
                ),
                {
                    "id": option_id,
                    "item_id": row["id"],
                    "label": label,
                    "display_order": value,
                    "value": value,
                    "synthetic": True if is_seed else bool(row["synthetic"]),
                    "source": "seed" if is_seed else row["source"],
                },
            )

    missing = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM instrument_items "
            "WHERE scale_id IS NULL OR item_order IS NULL OR locale IS NULL OR required IS NULL"
        )
    ).scalar_one()
    if missing:
        raise RuntimeError(f"catalog item backfill incomplete: {missing} rows")

    orphan_options = connection.execute(
        sa.text(
            "SELECT COUNT(*) FROM response_options ro "
            "LEFT JOIN instrument_items ii ON ii.id = ro.item_id "
            "WHERE ii.id IS NULL"
        )
    ).scalar_one()
    if orphan_options:
        raise RuntimeError(f"catalog option backfill has {orphan_options} orphan rows")


def _finalize_item_columns() -> None:
    op.alter_column("instrument_items", "scale_id", nullable=False)
    op.alter_column("instrument_items", "item_order", nullable=False)
    op.alter_column("instrument_items", "locale", nullable=False)
    op.alter_column("instrument_items", "required", nullable=False)
    op.drop_constraint("uq_item_per_scale", "instrument_items", type_="unique")
    op.drop_constraint("ck_scale_order_1_to_5", "instrument_items", type_="check")
    op.create_unique_constraint(
        "uq_item_per_scale_order", "instrument_items", ["scale_id", "item_order"]
    )
    op.create_check_constraint(
        "ck_item_order_positive", "instrument_items", "item_order > 0"
    )
    op.create_foreign_key(
        "fk_instrument_items_scale_version",
        "instrument_items",
        "scales",
        ["scale_id", "version_id"],
        ["id", "version_id"],
    )
    op.create_index(
        "ix_instrument_items_scale_id", "instrument_items", ["scale_id"], unique=False
    )
    op.drop_column("instrument_items", "scale_order")
    op.drop_column("instrument_items", "scale")


def _install_immutability_guards() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION catalog_version_immutability_guard() RETURNS trigger AS $$
        DECLARE transition text := current_setting('app.lifecycle_transition', true);
        BEGIN
            IF current_setting('app.seed_reset', true) = 'on' THEN
                IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
            END IF;
            IF TG_OP = 'DELETE' THEN
                IF OLD.status IN ('published', 'archived') THEN
                    RAISE EXCEPTION 'catalog version is immutable';
                END IF;
                RETURN OLD;
            END IF;
            IF OLD.status IN ('published', 'archived') THEN
                IF OLD.status = 'published' AND NEW.status = 'archived'
                   AND transition = 'archive'
                   AND NEW.is_immutable = true THEN
                    RETURN NEW;
                END IF;
                RAISE EXCEPTION 'catalog version is immutable';
            END IF;
            IF OLD.status = 'draft' AND NEW.status = 'published'
               AND transition = 'publish' AND NEW.is_immutable = true THEN
                RETURN NEW;
            END IF;
            IF OLD.status = 'draft' AND NEW.status = 'archived' THEN
                RAISE EXCEPTION 'draft catalog version cannot be archived';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION catalog_scale_immutability_guard() RETURNS trigger AS $$
        DECLARE version_status text;
        BEGIN
            IF current_setting('app.seed_reset', true) = 'on' THEN
                IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
            END IF;
            SELECT status INTO version_status FROM instrument_versions WHERE id = OLD.version_id;
            IF version_status IN ('published', 'archived') THEN
                RAISE EXCEPTION 'catalog scale is immutable';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION catalog_item_immutability_guard() RETURNS trigger AS $$
        DECLARE version_status text;
        BEGIN
            IF current_setting('app.seed_reset', true) = 'on' THEN
                IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
            END IF;
            SELECT status INTO version_status FROM instrument_versions WHERE id = OLD.version_id;
            IF version_status IN ('published', 'archived') THEN
                RAISE EXCEPTION 'catalog item is immutable';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION catalog_option_immutability_guard() RETURNS trigger AS $$
        DECLARE version_status text;
        BEGIN
            IF current_setting('app.seed_reset', true) = 'on' THEN
                IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
            END IF;
            SELECT iv.status INTO version_status
            FROM instrument_items ii JOIN instrument_versions iv ON iv.id = ii.version_id
            WHERE ii.id = OLD.item_id;
            IF version_status IN ('published', 'archived') THEN
                RAISE EXCEPTION 'catalog response option is immutable';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; ELSE RETURN NEW; END IF;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_catalog_version_immutability
        BEFORE UPDATE OR DELETE ON instrument_versions
        FOR EACH ROW EXECUTE FUNCTION catalog_version_immutability_guard();
        CREATE TRIGGER trg_catalog_scale_immutability
        BEFORE UPDATE OR DELETE ON scales
        FOR EACH ROW EXECUTE FUNCTION catalog_scale_immutability_guard();
        CREATE TRIGGER trg_catalog_item_immutability
        BEFORE UPDATE OR DELETE ON instrument_items
        FOR EACH ROW EXECUTE FUNCTION catalog_item_immutability_guard();
        CREATE TRIGGER trg_catalog_option_immutability
        BEFORE UPDATE OR DELETE ON response_options
        FOR EACH ROW EXECUTE FUNCTION catalog_option_immutability_guard();
        """
    )


def upgrade() -> None:
    connection = op.get_bind()
    invalid_statuses = connection.execute(
        sa.text(
            "SELECT id, status FROM instrument_versions "
            "WHERE status NOT IN ('draft', 'published', 'archived')"
        )
    ).all()
    if invalid_statuses:
        raise RuntimeError(
            f"unsupported instrument version statuses: {invalid_statuses}"
        )

    _create_catalog_tables()
    _add_version_and_item_columns()
    _backfill_catalog_graph()
    _finalize_item_columns()
    _install_immutability_guards()


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_catalog_option_immutability ON response_options"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS trg_catalog_item_immutability ON instrument_items"
    )
    op.execute("DROP TRIGGER IF EXISTS trg_catalog_scale_immutability ON scales")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_catalog_version_immutability ON instrument_versions"
    )
    op.execute("DROP FUNCTION IF EXISTS catalog_option_immutability_guard()")
    op.execute("DROP FUNCTION IF EXISTS catalog_item_immutability_guard()")
    op.execute("DROP FUNCTION IF EXISTS catalog_scale_immutability_guard()")
    op.execute("DROP FUNCTION IF EXISTS catalog_version_immutability_guard()")

    op.drop_constraint(
        "fk_instrument_items_scale_version", "instrument_items", type_="foreignkey"
    )
    op.drop_constraint("uq_item_per_scale_order", "instrument_items", type_="unique")
    op.drop_constraint("ck_item_order_positive", "instrument_items", type_="check")
    op.drop_index("ix_instrument_items_scale_id", table_name="instrument_items")
    op.add_column(
        "instrument_items", sa.Column("scale", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "instrument_items", sa.Column("scale_order", sa.Integer(), nullable=True)
    )
    op.execute(
        """
        UPDATE instrument_items ii
        SET scale = s.label, scale_order = ii.item_order
        FROM scales s WHERE s.id = ii.scale_id
        """
    )
    op.alter_column("instrument_items", "scale", nullable=False)
    op.alter_column("instrument_items", "scale_order", nullable=False)
    op.create_unique_constraint(
        "uq_item_per_scale", "instrument_items", ["version_id", "scale", "scale_order"]
    )
    op.create_check_constraint(
        "ck_scale_order_1_to_5", "instrument_items", "scale_order BETWEEN 1 AND 5"
    )
    op.drop_column("instrument_items", "required")
    op.drop_column("instrument_items", "locale")
    op.drop_column("instrument_items", "item_order")
    op.drop_column("instrument_items", "scale_id")

    op.drop_index(
        "ix_idempotency_records_actor_user_id", table_name="idempotency_records"
    )
    op.drop_table("idempotency_records")
    op.drop_index("ix_response_options_item_id", table_name="response_options")
    op.drop_table("response_options")
    op.drop_index("ix_scales_version_id", table_name="scales")
    op.drop_table("scales")

    op.drop_constraint(
        "ck_instrument_version_status", "instrument_versions", type_="check"
    )
    op.drop_constraint(
        "ck_published_versions_immutable", "instrument_versions", type_="check"
    )
    op.create_check_constraint(
        "ck_published_versions_immutable",
        "instrument_versions",
        "(status <> 'published') OR is_immutable",
    )
    for column in (
        "archived_at",
        "updated_at",
        "created_at",
        "adaptation_metadata",
        "response_type",
    ):
        op.drop_column("instrument_versions", column)
