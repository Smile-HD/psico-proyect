"""F2.1 RED tests for the catalog database slice.

Database tests use PostgreSQL when PSICO_DATABASE_URL is configured. The model
and loader contract tests remain runnable without a database.
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import CheckConstraint, UniqueConstraint, select, text

from app.models import (
    IdempotencyRecord,
    Instrument,
    InstrumentItem,
    InstrumentVersion,
    ResponseOption,
    Scale,
)
from app.seed.loader import (
    FIXTURES_DIR,
    SEED_OPTION_LABELS,
    SeedResetConflictError,
    reset_seed,
    run_seed,
    seed_id,
)
from tests.db_utils import SKIP_MESSAGE, db_reachable, db_url


def _constraints(model):
    return {constraint.name: constraint for constraint in model.__table__.constraints}


def test_catalog_models_declare_four_level_constraints() -> None:
    scales = _constraints(Scale)
    items = _constraints(InstrumentItem)
    options = _constraints(ResponseOption)
    versions = _constraints(InstrumentVersion)
    idempotency = _constraints(IdempotencyRecord)

    assert "uq_scales_version_order" in scales
    assert "ck_scale_display_order_positive" in scales
    assert "uq_item_per_scale_order" in items
    assert "ck_item_order_positive" in items
    assert "uq_option_item_order" in options
    assert "uq_option_item_value" in options
    assert "ck_option_display_order_1_to_5" in options
    assert "ck_option_value_1_to_5" in options
    assert "ck_instrument_version_status" in versions
    assert "ck_published_versions_immutable" in versions
    assert "uq_idempotency_scope" in idempotency

    assert any(
        isinstance(constraint, UniqueConstraint)
        and tuple(column.name for column in constraint.columns)
        == ("id", "version_id")
        for constraint in Scale.__table__.constraints
    )
    assert any(isinstance(constraint, CheckConstraint) for constraint in options.values())


def test_catalog_model_relationships_form_scale_item_option_chain() -> None:
    instrument = Instrument(key="TEST-CATALOG", title="Synthetic catalog")
    version = InstrumentVersion(instrument=instrument, version_no=1)
    scale = Scale(version=version, label="Intereses", display_order=1, locale="es")
    item = InstrumentItem(
        version=version,
        scale=scale,
        item_order=1,
        locale="es",
        required=True,
        text="Ítem sintético",
    )
    option = ResponseOption(
        item=item,
        label="Nunca",
        locale="es",
        display_order=1,
        value=1,
    )

    assert scale.version is version
    assert scale.items == [item]
    assert item.scale is scale
    assert item.response_options == [option]
    assert option.item is item
    assert version.scales == [scale]


def test_model_defaults_cover_runtime_and_archived_rows() -> None:
    version = InstrumentVersion(version_no=2, status="archived", is_immutable=True)
    assert InstrumentVersion.__table__.c.response_type.default.arg == "likert_1_5"
    assert version.status == "archived"
    assert version.is_immutable is True

    record = IdempotencyRecord(
        actor_user_id=uuid.uuid4(),
        operation="catalog.publish",
        resource_scope="version:1",
        idempotency_key="request-1",
        request_hash="a" * 64,
        response_status=200,
        response_body={"status": "published"},
    )
    assert record.request_hash == "a" * 64
    assert record.response_body["status"] == "published"


def test_seed_option_labels_are_stable_and_research_only() -> None:
    fixture = json.loads((FIXTURES_DIR / "items.json").read_text(encoding="utf-8"))
    assert fixture["key"] == "TP-S-01"
    assert SEED_OPTION_LABELS == (
        "Nunca",
        "Casi nunca",
        "A veces",
        "Casi siempre",
        "Siempre",
    )
    assert seed_id("TP-S-01:i1:option:1").version == 5
    assert all(isinstance(label, str) and label for label in SEED_OPTION_LABELS)


@pytest.fixture(scope="module")
def catalog_db_session():
    url = db_url()
    if not db_reachable(url):
        pytest.skip(SKIP_MESSAGE)
    from alembic import command
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool
    from tests.conftest import alembic_config
    from tests.test_schema import _new_test_database
    from tests.db_utils import maintenance_url

    dbname, test_url = _new_test_database(url)
    command.upgrade(alembic_config(test_url), "head")
    engine = create_engine(test_url, poolclass=NullPool)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        maint = create_engine(maintenance_url(url), isolation_level="AUTOCOMMIT")
        with maint.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)'))
        maint.dispose()


def test_catalog_schema_has_four_level_tables(catalog_db_session) -> None:
    tables = {
        row[0]
        for row in catalog_db_session.execute(
            text(
                "SELECT tablename FROM pg_tables "
                "WHERE schemaname = current_schema()"
            )
        )
    }
    assert {"scales", "response_options", "idempotency_records"} <= tables


def test_seed_graph_matches_loader_contract(catalog_db_session) -> None:
    run_seed(catalog_db_session)
    version_id = seed_id("TP-S-01:v1")
    scale_count = catalog_db_session.execute(
        text("SELECT COUNT(*) FROM scales WHERE version_id = :version_id"),
        {"version_id": version_id},
    ).scalar_one()
    item_count = catalog_db_session.execute(
        text("SELECT COUNT(*) FROM instrument_items WHERE version_id = :version_id"),
        {"version_id": version_id},
    ).scalar_one()
    option_count = catalog_db_session.execute(
        text(
            "SELECT COUNT(*) FROM response_options ro "
            "JOIN instrument_items ii ON ii.id = ro.item_id "
            "WHERE ii.version_id = :version_id"
        ),
        {"version_id": version_id},
    ).scalar_one()
    assert (scale_count, item_count, option_count) == (5, 20, 100)
    assert catalog_db_session.execute(
        text(
            "SELECT id FROM scales WHERE version_id = :version_id "
            "AND label = 'Intereses' AND display_order = 1"
        ),
        {"version_id": version_id},
    ).scalar_one() == seed_id("TP-S-01:scale:Intereses")
    assert catalog_db_session.execute(
        text(
            "SELECT id, label, display_order, value FROM response_options "
            "WHERE item_id = :item_id ORDER BY display_order"
        ),
        {"item_id": seed_id("TP-S-01:i1")},
    ).all() == [
        (seed_id(f"TP-S-01:i1:option:{value}"), label, value, value)
        for value, label in enumerate(SEED_OPTION_LABELS, start=1)
    ]


def test_seed_reset_coexists_with_runtime_rows(catalog_db_session) -> None:
    run_seed(catalog_db_session)
    runtime_id = uuid.uuid4()
    catalog_db_session.execute(
        text(
            "INSERT INTO instruments (id, key, title, synthetic, source) "
            "VALUES (:id, :key, 'Runtime synthetic', false, 'runtime')"
        ),
        {"id": runtime_id, "key": f"RUNTIME-{uuid.uuid4().hex[:8]}"},
    )
    catalog_db_session.commit()
    reset_seed(catalog_db_session)
    assert catalog_db_session.execute(
        text("SELECT source FROM instruments WHERE id = :id"), {"id": runtime_id}
    ).scalar_one() == "runtime"
    assert catalog_db_session.execute(
        text("SELECT COUNT(*) FROM scales WHERE source = 'seed'")
    ).scalar_one() == 5
    catalog_db_session.execute(text("DELETE FROM instruments WHERE id = :id"), {"id": runtime_id})
    catalog_db_session.commit()


def test_seed_reset_rejects_cross_ownership_before_delete(catalog_db_session) -> None:
    run_seed(catalog_db_session)
    runtime_user_id = uuid.uuid4()
    runtime_session_id = uuid.uuid4()
    catalog_db_session.execute(
        text(
            "INSERT INTO users (id, username, password_hash, full_name, synthetic, source) "
            "VALUES (:id, :username, 'hash', 'Runtime', false, 'runtime')"
        ),
        {"id": runtime_user_id, "username": f"runtime-{uuid.uuid4().hex[:8]}"},
    )
    catalog_db_session.execute(
        text(
            "INSERT INTO sessions "
            "(id, user_id, instrument_version_id, status, synthetic, source) "
            "VALUES (:id, :user_id, :version_id, 'completed', false, 'runtime')"
        ),
        {
            "id": runtime_session_id,
            "user_id": runtime_user_id,
            "version_id": seed_id("TP-S-01:v1"),
        },
    )
    catalog_db_session.commit()
    before = catalog_db_session.execute(
        text("SELECT COUNT(*) FROM scales WHERE source = 'seed'")
    ).scalar_one()
    with pytest.raises(SeedResetConflictError) as error:
        reset_seed(catalog_db_session)
    assert str(error.value) == "seed_reset_dependency_conflict"
    assert catalog_db_session.execute(
        text("SELECT COUNT(*) FROM scales WHERE source = 'seed'")
    ).scalar_one() == before
    catalog_db_session.execute(
        text("DELETE FROM sessions WHERE id = :id"), {"id": runtime_session_id}
    )
    catalog_db_session.execute(
        text("DELETE FROM users WHERE id = :id"), {"id": runtime_user_id}
    )
    catalog_db_session.commit()


def test_status_check_and_option_range_are_enforced(catalog_db_session) -> None:
    instrument_id = uuid.uuid4()
    version_id = uuid.uuid4()
    catalog_db_session.execute(
        text(
            "INSERT INTO instruments (id, key, title, synthetic, source) "
            "VALUES (:id, :key, :title, true, 'runtime')"
        ),
        {"id": instrument_id, "key": f"TEST-{uuid.uuid4().hex[:8]}", "title": "Synthetic"},
    )
    catalog_db_session.execute(
        text(
            "INSERT INTO instrument_versions "
            "(id, instrument_id, version_no, status, response_type, "
            "is_immutable, synthetic, source) VALUES "
            "(:id, :instrument_id, 1, 'draft', 'likert_1_5', false, true, 'runtime')"
        ),
        {"id": version_id, "instrument_id": instrument_id},
    )
    catalog_db_session.commit()

    with pytest.raises(Exception):
        catalog_db_session.execute(
            text("UPDATE instrument_versions SET status = 'unknown' WHERE id = :id"),
            {"id": version_id},
        )
        catalog_db_session.commit()
    catalog_db_session.rollback()
    catalog_db_session.execute(
        text("DELETE FROM instrument_versions WHERE id = :id"), {"id": version_id}
    )
    catalog_db_session.execute(
        text("DELETE FROM instruments WHERE id = :id"), {"id": instrument_id}
    )
    catalog_db_session.commit()
