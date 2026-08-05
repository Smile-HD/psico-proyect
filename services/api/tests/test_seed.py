"""RED test — seed (F1): idempotency, deterministic ids, scoped reset.

Pure tests: UUID5 determinism + version nibble, pinned keys, fixture math
(20 items = 5 scales x 4, 30 profiles x 20 responses, norm_note present).
DB tests (skip without PostgreSQL):
  - Running seed twice leaves identical row counts (manifest appended).
  - Manifest counts match the live database.
  - --reset removes only seed-owned rows; a manual non-seed row survives.
  - F5/F6 stay empty after seed.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.models.consent import ConsentGrant
from app.models.instruments import InstrumentItem
from app.models.scoring import ReferenceSet
from app.models.seed import SeedManifest
from app.models.sessions import Response, Session
from app.seed.loader import (
    FIXTURES_DIR,
    SEED_VERSION,
    collect_counts,
    reset_seed,
    run_seed,
    seed_id,
)
from tests.conftest import alembic_config
from tests.db_utils import SKIP_MESSAGE, db_reachable, db_url, maintenance_url

# --------------------------------------------------------------------------- #
# DB isolation: seed tests mutate the database heavily (reset + reseed), so
# they run against their own throwaway database instead of the session-scoped
# shared DB that consent/auth tests use.
# --------------------------------------------------------------------------- #


def _new_test_database(url: str) -> tuple[str, str]:
    """Create a throwaway database on the same server; return (name, url)."""
    dbname = f"psico_seed_test_{uuid.uuid4().hex[:12]}"
    maint = create_engine(maintenance_url(url), isolation_level="AUTOCOMMIT")
    with maint.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{dbname}"'))
    maint.dispose()
    base, _, _ = url.rpartition("/")
    return dbname, f"{base}/{dbname}"


@pytest.fixture(scope="module")
def engine():
    url = db_url()
    if not db_reachable(url):
        pytest.skip(SKIP_MESSAGE)
    dbname, test_url = _new_test_database(url)
    command.upgrade(alembic_config(test_url), "head")
    # NullPool: release every connection immediately so teardown can drop the
    # throwaway database without ObjectInUse errors.
    eng = create_engine(test_url, poolclass=NullPool)
    yield eng
    eng.dispose()
    maint = create_engine(maintenance_url(url), isolation_level="AUTOCOMMIT")
    with maint.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{dbname}"'))
    maint.dispose()


@pytest.fixture(scope="module")
def db_session(engine):
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()

# --------------------------------------------------------------------------- #
# Pure: deterministic ids and fixture structure
# --------------------------------------------------------------------------- #


def test_seed_id_deterministic_and_uuid5() -> None:
    a = seed_id("TP-S-01")
    b = seed_id("TP-S-01")
    assert a == b
    assert a.version == 5  # UUID5 version nibble
    # runtime-style uuid4 differs and has version nibble 4
    assert uuid.uuid4().version == 4


def test_pinned_seed_keys_resolve() -> None:
    for key in ("evaluado_01", "TP-S-01", "RS-TP-S-01"):
        assert seed_id(key) == uuid.uuid5(uuid.NAMESPACE_URL, f"psico-seed:{key}")


def test_items_fixture_math() -> None:
    items = json.loads((FIXTURES_DIR / "items.json").read_text(encoding="utf-8"))
    total = 0
    for scale in items["scales"]:
        assert 1 <= len(scale["items"]) <= 5  # CHECK 1-5 items per scale
        total += len(scale["items"])
    assert total == 20
    assert len(items["scales"]) == 5


def test_reference_fixture_research_only() -> None:
    reference = json.loads((FIXTURES_DIR / "reference.json").read_text(encoding="utf-8"))
    assert reference["key"] == "RS-TP-S-01"
    assert reference["reference_status"] == "synthetic"
    assert reference["use"] == "research-only"
    assert reference["norm_note"] == "NO es una norma UAGRM. Datos inventados para desarrollo."


def test_profiles_fixtures_exist() -> None:
    profiles = sorted((FIXTURES_DIR / "profiles").glob("evaluado_*.json"))
    assert len(profiles) == 30
    for profile_file in profiles:
        profile = json.loads(profile_file.read_text(encoding="utf-8"))
        assert len(profile["responses"]) == 20
        assert all(1 <= v <= 5 for v in profile["responses"])


def test_checksum_deterministic() -> None:
    from app.seed.loader import fixtures_checksum

    assert fixtures_checksum() == fixtures_checksum()
    assert len(fixtures_checksum()) == 64  # sha256 hex


# --------------------------------------------------------------------------- #
# DB: idempotency, manifest, scoped reset
# --------------------------------------------------------------------------- #


def _snapshot(db_session) -> dict:
    snap = {}
    for table in ("instruments", "instrument_items", "sessions", "responses",
                  "reference_sets", "reference_values", "consent_grants",
                  "users", "roles"):
        snap[table] = db_session.scalar(
            text(f"SELECT COUNT(*) FROM {table} WHERE source = 'seed'")
        )
    return snap


def test_seed_twice_identical_counts(engine, db_session) -> None:
    reset_seed(db_session)  # clean known baseline
    run_seed(db_session)
    before = _snapshot(db_session)
    manifests_before = db_session.scalar(select(func.count()).select_from(SeedManifest))

    run_seed(db_session)  # second run — must be a no-op for rows

    after = _snapshot(db_session)
    assert after == before
    assert db_session.scalar(select(func.count()).select_from(SeedManifest)) == manifests_before + 1


def test_manifest_counts_match_db(engine, db_session) -> None:
    run_seed(db_session)
    manifest = db_session.scalar(
        select(SeedManifest).order_by(SeedManifest.executed_at.desc())
    )
    assert manifest is not None
    assert manifest.seed_version == SEED_VERSION
    assert len(manifest.checksum) == 64
    assert manifest.executed_at is not None
    live = collect_counts(db_session)
    for table in ("instruments", "instrument_items", "sessions", "responses",
                  "reference_sets", "reference_values", "consent_grants", "users"):
        assert manifest.counts[table] == live[table] == _snapshot(db_session)[table]


def test_item_and_response_math(engine, db_session) -> None:
    run_seed(db_session)
    items = db_session.scalar(select(func.count()).select_from(InstrumentItem))
    sessions = db_session.scalar(select(func.count()).select_from(Session))
    responses = db_session.scalar(select(func.count()).select_from(Response))
    grants = db_session.scalar(select(func.count()).select_from(ConsentGrant))
    assert items == 20
    assert sessions == 30
    assert responses == 600
    assert grants == 30
    # norm_note present in DB
    ref = db_session.scalar(select(ReferenceSet).where(ReferenceSet.key == "RS-TP-S-01"))
    assert ref is not None
    assert ref.reference_status == "synthetic"
    assert ref.use == "research-only"
    assert ref.norm_note == "NO es una norma UAGRM. Datos inventados para desarrollo."


def test_reset_keeps_non_seed(engine, db_session) -> None:
    from app.core.auth import hash_password

    reset_seed(db_session)
    # manual non-seed row (unique per run)
    manual_username = f"manual_{uuid.uuid4().hex[:8]}"
    db_session.execute(
        text(
            "INSERT INTO users (id, username, password_hash, full_name, email,"
            " is_active, synthetic, source) VALUES (:id, :u, :p, :f, :e, true, false, 'manual')"
        ),
        {
            "id": uuid.uuid4(),
            "u": manual_username,
            "p": hash_password("x"),
            "f": "Manual row",
            "e": f"{manual_username}@psico.test",
        },
    )
    db_session.commit()

    reset_seed(db_session)  # --reset path: wipe seed-owned, re-seed

    row = db_session.execute(
        text("SELECT source FROM users WHERE username = :u"), {"u": manual_username}
    ).first()
    assert row is not None and row[0] == "manual"  # non-seed survived
    # seed rows restored with deterministic ids
    assert _snapshot(db_session)["sessions"] == 30


def test_f5_f6_empty_after_seed(engine, db_session) -> None:
    run_seed(db_session)
    for table in ("recommendation_rules", "recommendation_results",
                  "reports", "report_templates"):
        count = db_session.scalar(text(f"SELECT COUNT(*) FROM {table}"))
        assert count == 0, f"{table} must stay empty in F1"


def test_seed_executed_audited(engine, db_session) -> None:
    run_seed(db_session)
    events = db_session.scalar(
        text("SELECT COUNT(*) FROM audit_log WHERE event_type = 'seed.executed'")
    )
    assert events >= 1
