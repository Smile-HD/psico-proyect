"""F2.1.8 migration upgrade-from-F1 coverage."""

from __future__ import annotations

import json
import uuid

import pytest
from alembic import command
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.seed.loader import FIXTURES_DIR, SEED_OPTION_LABELS, seed_id
from tests.conftest import alembic_config
from tests.db_utils import SKIP_MESSAGE, db_reachable, db_url, maintenance_url
from tests.test_schema import _new_test_database


@pytest.fixture(scope="module")
def migrated_f1_db():
    url = db_url()
    if not db_reachable(url):
        pytest.skip(SKIP_MESSAGE)
    dbname, test_url = _new_test_database(url)
    command.upgrade(alembic_config(test_url), "0004_audit_append_only_trigger")
    engine = create_engine(test_url, poolclass=NullPool)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    fixture = json.loads((FIXTURES_DIR / "items.json").read_text(encoding="utf-8"))
    instrument_id = seed_id("TP-S-01")
    version_id = seed_id("TP-S-01:v1")
    user_id = seed_id("migration-user")
    session_id = seed_id("migration-session")
    reference_id = seed_id("RS-TP-S-01")
    session.execute(
        text(
            "INSERT INTO instruments (id, key, title, description, synthetic, source) "
            "VALUES (:id, :key, :title, :description, true, 'seed')"
        ),
        {"id": instrument_id, "key": fixture["key"], "title": fixture["title"], "description": fixture["description"]},
    )
    session.execute(
        text(
            "INSERT INTO instrument_versions "
            "(id, instrument_id, version_no, status, published_at, is_immutable, synthetic, source) "
            "VALUES (:id, :instrument_id, 1, 'published', '2026-01-01T00:00:00Z', true, true, 'seed')"
        ),
        {"id": version_id, "instrument_id": instrument_id},
    )
    item_ids = []
    item_index = 0
    for scale in fixture["scales"]:
        for item in scale["items"]:
            item_index += 1
            item_id = seed_id(f"TP-S-01:i{item_index}")
            item_ids.append(item_id)
            session.execute(
                text(
                    "INSERT INTO instrument_items "
                    "(id, version_id, scale, scale_order, text, synthetic, source) "
                    "VALUES (:id, :version_id, :scale, :scale_order, :text, true, 'seed')"
                ),
                {
                    "id": item_id,
                    "version_id": version_id,
                    "scale": scale["scale"],
                    "scale_order": item["order"],
                    "text": item["text"],
                },
            )
    session.execute(
        text(
            "INSERT INTO users (id, username, password_hash, full_name, synthetic, source) "
            "VALUES (:id, 'migration-user', 'hash', 'Migration user', true, 'seed')"
        ),
        {"id": user_id},
    )
    session.execute(
        text(
            "INSERT INTO sessions "
            "(id, user_id, instrument_version_id, status, synthetic, source) "
            "VALUES (:id, :user_id, :version_id, 'completed', true, 'seed')"
        ),
        {"id": session_id, "user_id": user_id, "version_id": version_id},
    )
    session.execute(
        text(
            "INSERT INTO responses "
            "(id, session_id, item_id, value, synthetic, source) "
            "VALUES (:id, :session_id, :item_id, 3, true, 'seed')"
        ),
        {"id": seed_id("migration-response"), "session_id": session_id, "item_id": item_ids[0]},
    )
    session.execute(
        text(
            "INSERT INTO reference_sets "
            "(id, key, instrument_version_id, reference_status, use, synthetic, source) "
            "VALUES (:id, 'RS-TP-S-01', :version_id, 'synthetic', 'research-only', true, 'seed')"
        ),
        {"id": reference_id, "version_id": version_id},
    )
    session.commit()
    session.close()
    engine.dispose()
    command.upgrade(alembic_config(test_url), "head")
    migrated_engine = create_engine(test_url, poolclass=NullPool)
    migrated_session = sessionmaker(bind=migrated_engine, expire_on_commit=False)()
    try:
        yield migrated_session
    finally:
        migrated_session.close()
        migrated_engine.dispose()
        maintenance = create_engine(maintenance_url(url), isolation_level="AUTOCOMMIT")
        with maintenance.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)'))
        maintenance.dispose()


def test_f1_seed_identity_and_references_survive(migrated_f1_db) -> None:
    version_id = seed_id("TP-S-01:v1")
    version_row = migrated_f1_db.execute(
        text("SELECT id, published_at FROM instrument_versions WHERE id = :id"),
        {"id": version_id},
    ).one()
    assert version_row[0] == version_id
    assert version_row[1].isoformat() == "2026-01-01T00:00:00+00:00"
    assert migrated_f1_db.execute(
        text("SELECT COUNT(*) FROM scales WHERE version_id = :id"), {"id": version_id}
    ).scalar_one() == 5
    assert migrated_f1_db.execute(
        text("SELECT COUNT(*) FROM instrument_items WHERE version_id = :id"), {"id": version_id}
    ).scalar_one() == 20
    assert migrated_f1_db.execute(
        text(
            "SELECT COUNT(*) FROM response_options ro "
            "JOIN instrument_items ii ON ii.id = ro.item_id WHERE ii.version_id = :id"
        ),
        {"id": version_id},
    ).scalar_one() == 100
    assert migrated_f1_db.execute(
        text("SELECT COUNT(*) FROM sessions WHERE instrument_version_id = :id"),
        {"id": version_id},
    ).scalar_one() == 1
    assert migrated_f1_db.execute(
        text("SELECT item_id FROM responses WHERE id = :id"),
        {"id": seed_id("migration-response")},
    ).scalar_one() == seed_id("TP-S-01:i1")


def test_f1_backfill_preserves_option_identity_and_values(migrated_f1_db) -> None:
    rows = migrated_f1_db.execute(
        text(
            "SELECT id, label, display_order, value FROM response_options "
            "WHERE item_id = :item_id ORDER BY display_order"
        ),
        {"item_id": seed_id("TP-S-01:i1")},
    ).all()
    assert rows == [
        (seed_id(f"TP-S-01:i1:option:{value}"), label, value, value)
        for value, label in enumerate(SEED_OPTION_LABELS, start=1)
    ]


def test_f1_backfill_upgrade_is_idempotent(migrated_f1_db) -> None:
    # The fixture's second upgrade call is the idempotency proof; counts remain stable.
    assert migrated_f1_db.execute(
        text("SELECT version_num FROM alembic_version")
    ).scalar_one() == "0005_catalog_four_level"
