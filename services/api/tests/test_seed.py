"""RED test — seed: idempotency, deterministic ids, scoped reset.

Pure tests: UUID5 determinism + version nibble, pinned keys, fixture math
(20 items = 5 scales x 4, 30 profiles x 20 responses, norm_note present).
DB tests (skip without PostgreSQL):
  - Running seed twice leaves identical row counts (manifest appended).
  - Manifest counts match the live database.
  - --reset removes only seed-owned rows; a manual non-seed row survives.
  - F5 recommendation rules are seeded while runtime results stay empty.
"""

from __future__ import annotations

import json
import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.models.consent import ConsentGrant
from app.models.institutions import Program
from app.models.instruments import InstrumentItem
from app.models.recommendation import RecommendationResult, RecommendationRule
from app.models.reporting import Report, ReportArtifact, ReportTemplate
from app.models.scoring import ReferenceSet
from app.models.scoring import ScoreRun
from app.models.seed import SeedManifest
from app.models.identity import User
from app.models.idempotency import IdempotencyRecord
from app.models.instruments import Instrument, InstrumentVersion
from app.models.sessions import Response, Session
from app.seed.loader import (
    FIXTURES_DIR,
    SEED_TABLES,
    SEED_VERSION,
    SeedResetConflictError,
    collect_counts,
    fixtures_checksum,
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


def test_recommendation_fixtures_define_synthetic_programs_and_rules() -> None:
    programs_fixture = json.loads(
        (FIXTURES_DIR / "programs.json").read_text(encoding="utf-8")
    )
    rules_fixture = json.loads(
        (FIXTURES_DIR / "recommendation_rules.json").read_text(encoding="utf-8")
    )

    programs = programs_fixture["programs"]
    rules = rules_fixture["rules"]
    assert 4 <= len(programs) <= 6
    program_keys = {program["key"] for program in programs}
    assert len(program_keys) == len(programs)
    assert all(key.startswith("program:") for key in program_keys)
    assert len({program["code"] for program in programs}) == len(programs)

    assert rules
    assert all(rule["is_active"] is True for rule in rules)
    assert all(rule["rule_type"] == "percentile_min" for rule in rules)
    assert all(rule["program_key"] in program_keys for rule in rules)
    assert all(
        rule["key"].startswith(f"rule:{rule['program_key']}:") for rule in rules
    )
    scales = {rule["params"]["scale"] for rule in rules}
    assert {
        "Intereses",
        "Aptitud verbal",
        "Aptitud numérica",
        "Razonamiento abstracto",
        "Valores/preferencias",
        "overall",
    }.issubset(scales)
    assert any("weight" not in rule["params"] for rule in rules)


def test_recommendation_tables_are_part_of_seed_scope() -> None:
    assert SEED_VERSION != "1.0.0"
    assert "recommendation_rules" in SEED_TABLES
    assert "recommendation_results" in SEED_TABLES


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
                  "users", "roles", "programs", "recommendation_rules",
                  "recommendation_results"):
        snap[table] = db_session.scalar(
            text(f"SELECT COUNT(*) FROM {table} WHERE source = 'seed'")
        )
    return snap


def _recommendation_snapshot(db_session) -> dict:
    return {
        "program_ids": tuple(
            sorted(
                str(value)
                for value in db_session.execute(
                    text("SELECT id FROM programs WHERE source = 'seed'")
                ).scalars()
            )
        ),
        "rule_ids": tuple(
            sorted(
                str(value)
                for value in db_session.execute(
                    text("SELECT id FROM recommendation_rules WHERE source = 'seed'")
                ).scalars()
            )
        ),
        "program_count": db_session.scalar(
            text("SELECT COUNT(*) FROM programs WHERE source = 'seed'")
        ),
        "rule_count": db_session.scalar(
            text("SELECT COUNT(*) FROM recommendation_rules WHERE source = 'seed'")
        ),
        "result_count": db_session.scalar(
            text("SELECT COUNT(*) FROM recommendation_results WHERE source = 'seed'")
        ),
    }


def test_seed_twice_identical_counts(engine, db_session) -> None:
    reset_seed(db_session)  # clean known baseline
    run_seed(db_session)
    before = _snapshot(db_session)
    manifests_before = db_session.scalar(select(func.count()).select_from(SeedManifest))

    run_seed(db_session)  # second run — must be a no-op for rows

    after = _snapshot(db_session)
    assert after == before
    assert (
        db_session.scalar(select(func.count()).select_from(SeedManifest))
        == manifests_before + 1
    )


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
                  "reference_sets", "reference_values", "consent_grants", "users",
                  "programs", "recommendation_rules", "recommendation_results"):
        assert manifest.counts[table] == live[table] == _snapshot(db_session)[table]


def test_recommendation_seed_content_and_results_empty(engine, db_session) -> None:
    programs_fixture = json.loads(
        (FIXTURES_DIR / "programs.json").read_text(encoding="utf-8")
    )
    rules_fixture = json.loads(
        (FIXTURES_DIR / "recommendation_rules.json").read_text(encoding="utf-8")
    )
    reset_seed(db_session)
    run_seed(db_session)

    programs = db_session.scalars(
        select(Program).where(
            Program.faculty_id == seed_id("faculty:dev"), Program.source == "seed"
        )
    ).all()
    expected_program_ids = {
        seed_id(program["key"]) for program in programs_fixture["programs"]
    }
    assert len(programs) == len(expected_program_ids) + 1  # includes program:dev
    assert expected_program_ids.issubset({program.id for program in programs})
    assert seed_id("program:dev") in {program.id for program in programs}
    assert all(program.synthetic and program.source == "seed" for program in programs)
    assert len({program.code for program in programs}) == len(programs)

    expected_rule_ids = {seed_id(rule["key"]) for rule in rules_fixture["rules"]}
    rules = db_session.scalars(
        select(RecommendationRule).where(RecommendationRule.source == "seed")
    ).all()
    assert {rule.id for rule in rules} == expected_rule_ids
    assert all(rule.synthetic and rule.source == "seed" for rule in rules)
    assert all(rule.is_active for rule in rules)
    assert all(rule.rule_type == "percentile_min" for rule in rules)
    assert all(
        rule.program_id in expected_program_ids
        and rule.params["scale"]
        in {
            "Intereses",
            "Aptitud verbal",
            "Aptitud numérica",
            "Razonamiento abstracto",
            "Valores/preferencias",
            "overall",
        }
        for rule in rules
    )
    assert db_session.scalar(select(func.count()).select_from(RecommendationResult)) == 0
    counts = collect_counts(db_session)
    assert counts["recommendation_rules"] == len(rules)
    assert counts["recommendation_results"] == 0


def test_recommendation_seed_is_idempotent(engine, db_session) -> None:
    reset_seed(db_session)
    run_seed(db_session)
    first = _recommendation_snapshot(db_session)
    manifests_before = db_session.scalar(select(func.count()).select_from(SeedManifest))
    assert first["program_count"] >= 5
    assert first["rule_count"] > 0

    run_seed(db_session)

    assert _recommendation_snapshot(db_session) == first
    assert (
        db_session.scalar(select(func.count()).select_from(SeedManifest))
        == manifests_before + 1
    )


def test_seed_reset_rejects_runtime_recommendation_dependency(engine, db_session) -> None:
    rules_fixture = json.loads(
        (FIXTURES_DIR / "recommendation_rules.json").read_text(encoding="utf-8")
    )
    run_seed(db_session)
    rule = rules_fixture["rules"][0]
    runtime_result_id = uuid.uuid4()
    db_session.execute(
        text(
            "INSERT INTO recommendation_results "
            "(id, session_id, rule_id, program_id, fit_score, justification, synthetic, source) "
            "VALUES (:id, :session_id, :rule_id, :program_id, 50.00, 'runtime row', false, 'runtime')"
        ),
        {
            "id": runtime_result_id,
            "session_id": seed_id("session:evaluado_01"),
            "rule_id": seed_id(rule["key"]),
            "program_id": seed_id(rule["program_key"]),
        },
    )
    db_session.commit()
    before = _recommendation_snapshot(db_session)

    with pytest.raises(SeedResetConflictError) as error:
        reset_seed(db_session)

    assert str(error.value) == "seed_reset_dependency_conflict"
    assert _recommendation_snapshot(db_session) == before
    assert (
        db_session.scalar(
            text("SELECT COUNT(*) FROM recommendation_results WHERE id = :id"),
            {"id": runtime_result_id},
        )
        == 1
    )
    db_session.execute(
        text("DELETE FROM recommendation_results WHERE id = :id"),
        {"id": runtime_result_id},
    )
    db_session.commit()


def test_reset_removes_seed_owned_recommendation_rows(engine, db_session) -> None:
    rules_fixture = json.loads(
        (FIXTURES_DIR / "recommendation_rules.json").read_text(encoding="utf-8")
    )
    run_seed(db_session)
    rule = rules_fixture["rules"][0]
    seed_result_id = seed_id("recommendation-result:test-seed")
    db_session.execute(
        text(
            "INSERT INTO recommendation_results "
            "(id, session_id, rule_id, program_id, fit_score, justification, synthetic, source) "
            "VALUES (:id, :session_id, :rule_id, :program_id, 75.00, 'seed row', true, 'seed')"
        ),
        {
            "id": seed_result_id,
            "session_id": seed_id("session:evaluado_01"),
            "rule_id": seed_id(rule["key"]),
            "program_id": seed_id(rule["program_key"]),
        },
    )
    db_session.commit()
    assert (
        db_session.scalar(
            text("SELECT COUNT(*) FROM recommendation_results WHERE source = 'seed'")
        )
        == 1
    )

    reset_seed(db_session)

    assert (
        db_session.scalar(
            text("SELECT COUNT(*) FROM recommendation_results WHERE source = 'seed'")
        )
        == 0
    )
    assert db_session.scalar(
        text("SELECT COUNT(*) FROM recommendation_rules WHERE source = 'seed'")
    ) > 0


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


def test_f5_f6_seed_state_after_seed(engine, db_session) -> None:
    run_seed(db_session)
    assert db_session.scalar(text("SELECT COUNT(*) FROM recommendation_rules")) > 0
    assert db_session.scalar(text("SELECT COUNT(*) FROM recommendation_results")) == 0
    assert db_session.scalar(text("SELECT COUNT(*) FROM reports")) == 0
    assert db_session.scalar(
        text("SELECT COUNT(*) FROM report_templates WHERE source = 'seed'")
    ) == 1


def test_seed_executed_audited(engine, db_session) -> None:
    run_seed(db_session)
    events = db_session.scalar(
        text("SELECT COUNT(*) FROM audit_log WHERE event_type = 'seed.executed'")
    )
    assert events >= 1


def test_report_template_fixture_is_literal_spanish_seed_data() -> None:
    fixture = json.loads(
        (FIXTURES_DIR / "report_template.json").read_text(encoding="utf-8")
    )
    assert fixture["key"] == "informe-basico"
    assert fixture["version_no"] == 1
    assert fixture["status"] == "published"
    assert set(
        token for token in ("{{session_id}}", "{{scores}}", "{{overall}}", "{{recommendations}}", "{{norm_note}}", "{{disclaimer}}")
        if token in fixture["template_body"]
    ) == {
        "{{session_id}}",
        "{{scores}}",
        "{{overall}}",
        "{{recommendations}}",
        "{{norm_note}}",
        "{{disclaimer}}",
    }
    assert "{%" not in fixture["template_body"]


def test_report_template_is_seeded_once_and_manifested(engine, db_session) -> None:
    reset_seed(db_session)
    run_seed(db_session)
    first = db_session.scalar(
        select(ReportTemplate).where(ReportTemplate.key == "informe-basico")
    )
    assert first is not None
    assert first.id == seed_id("report-template:informe-basico")
    assert first.id.version == 5
    assert first.version_no == 1
    assert first.status == "published"
    assert first.synthetic is True and first.source == "seed"
    assert db_session.scalar(
        text("SELECT COUNT(*) FROM report_templates WHERE key = 'informe-basico'")
    ) == 1

    template_snapshot = (first.id, first.template_body)
    run_seed(db_session)
    second = db_session.scalar(
        select(ReportTemplate).where(ReportTemplate.key == "informe-basico")
    )
    assert second is not None
    assert (second.id, second.template_body) == template_snapshot
    assert db_session.scalar(
        text("SELECT COUNT(*) FROM report_templates WHERE key = 'informe-basico'")
    ) == 1


def test_reset_appends_manifest_without_changing_seed_template_identity(
    engine, db_session
) -> None:
    reset_seed(db_session)
    run_seed(db_session)
    template_id = db_session.scalar(
        select(ReportTemplate.id).where(ReportTemplate.key == "informe-basico")
    )
    before_manifests = db_session.scalar(select(func.count()).select_from(SeedManifest))

    reset_seed(db_session)

    after_manifests = db_session.scalar(select(func.count()).select_from(SeedManifest))
    assert after_manifests == before_manifests + 1
    assert db_session.scalar(
        select(ReportTemplate.id).where(ReportTemplate.key == "informe-basico")
    ) == template_id
    assert db_session.scalar(text("SELECT COUNT(*) FROM score_runs")) == 0
    assert db_session.scalar(text("SELECT COUNT(*) FROM reports")) == 0

    manifest = db_session.scalar(
        select(SeedManifest).order_by(SeedManifest.executed_at.desc())
    )
    assert manifest is not None
    assert manifest.counts["report_templates"] == 1
    assert manifest.checksum == fixtures_checksum()
    assert SEED_VERSION != "1.1.0"


def test_seed_reset_preflight_rejects_runtime_reporting_dependencies_atomically(
    engine, db_session
) -> None:
    reset_seed(db_session)
    run_seed(db_session)
    seed_session_id = seed_id("session:evaluado_01")
    reference_id = seed_id("RS-TP-S-01")
    runtime_score_run_id = uuid.uuid4()
    db_session.execute(
        text(
            "INSERT INTO score_runs "
            "(id, session_id, reference_set_id, status, raw, synthetic, source) "
            "VALUES (:id, :session_id, :reference_set_id, 'completed', '{}'::jsonb, false, 'runtime')"
        ),
        {
            "id": runtime_score_run_id,
            "session_id": seed_session_id,
            "reference_set_id": reference_id,
        },
    )
    db_session.commit()
    before = {
        "templates": db_session.scalar(text("SELECT COUNT(*) FROM report_templates WHERE source = 'seed'")),
        "score_runs": db_session.scalar(text("SELECT COUNT(*) FROM score_runs")),
        "manifests": db_session.scalar(text("SELECT COUNT(*) FROM seed_manifest")),
    }

    with pytest.raises(SeedResetConflictError) as error:
        reset_seed(db_session)

    assert str(error.value) == "seed_reset_dependency_conflict"
    assert {
        "templates": db_session.scalar(text("SELECT COUNT(*) FROM report_templates WHERE source = 'seed'")),
        "score_runs": db_session.scalar(text("SELECT COUNT(*) FROM score_runs")),
        "manifests": db_session.scalar(text("SELECT COUNT(*) FROM seed_manifest")),
    } == before
    assert db_session.get(ScoreRun, runtime_score_run_id) is not None

    db_session.execute(text("DELETE FROM score_runs WHERE id = :id"), {"id": runtime_score_run_id})
    db_session.commit()


def test_runtime_report_score_run_artifact_and_template_survive_seed_reset(
    engine, db_session
) -> None:
    reset_seed(db_session)
    run_seed(db_session)

    runtime_user = User(
        id=uuid.uuid4(),
        username=f"runtime-report-{uuid.uuid4().hex[:8]}",
        password_hash="hash",
        full_name="Synthetic runtime report user",
        synthetic=False,
        source="runtime",
    )
    runtime_instrument = Instrument(
        id=uuid.uuid4(),
        key=f"RUNTIME-REPORT-{uuid.uuid4().hex[:8]}",
        title="Synthetic runtime report instrument",
        synthetic=False,
        source="runtime",
    )
    runtime_version = InstrumentVersion(
        id=uuid.uuid4(),
        instrument_id=runtime_instrument.id,
        version_no=1,
        status="draft",
        is_immutable=False,
        synthetic=False,
        source="runtime",
    )
    runtime_reference = ReferenceSet(
        id=uuid.uuid4(),
        key=f"RUNTIME-REPORT-REF-{uuid.uuid4().hex[:8]}",
        instrument_version_id=runtime_version.id,
        reference_status="synthetic",
        use="research-only",
        norm_note="Synthetic runtime reference note.",
        synthetic=False,
        source="runtime",
    )
    runtime_session = Session(
        id=uuid.uuid4(),
        user_id=runtime_user.id,
        instrument_version_id=runtime_version.id,
        status="completed",
        completed_at=datetime.now(timezone.utc),
        synthetic=False,
        source="runtime",
    )
    runtime_score_run = ScoreRun(
        id=uuid.uuid4(),
        session_id=runtime_session.id,
        reference_set_id=runtime_reference.id,
        status="completed",
        raw={"synthetic": True},
        synthetic=False,
        source="runtime",
    )
    runtime_template = ReportTemplate(
        id=uuid.uuid4(),
        key=f"runtime-report-template-{uuid.uuid4().hex[:8]}",
        name="Synthetic runtime template",
        template_body="{{session_id}} {{scores}} {{overall}} {{recommendations}} {{norm_note}} {{disclaimer}}",
        version_no=1,
        status="published",
        synthetic=False,
        source="runtime",
    )
    runtime_report = Report(
        id=uuid.uuid4(),
        session_id=runtime_session.id,
        score_run_id=runtime_score_run.id,
        template_id=runtime_template.id,
        template_version_no=1,
        recommendation_snapshot={"items": []},
        format="pdf",
        status="ready",
        storage_key=str(uuid.uuid4()),
        sha256=hashlib.sha256(b"runtime-pdf").hexdigest(),
        byte_size=len(b"runtime-pdf"),
        media_type="application/pdf",
        renderer_version="runtime-test",
        generated_at=datetime.now(timezone.utc),
        synthetic=False,
        source="runtime",
    )
    runtime_artifact = ReportArtifact(
        storage_key=runtime_report.storage_key,
        report_id=runtime_report.id,
        payload=b"runtime-pdf",
        sha256=runtime_report.sha256,
        byte_size=runtime_report.byte_size,
        media_type="application/pdf",
    )
    db_session.add_all(
        [runtime_user, runtime_instrument, runtime_template]
    )
    db_session.flush()
    db_session.add_all([runtime_version, runtime_reference, runtime_session])
    db_session.flush()
    db_session.add(runtime_score_run)
    db_session.flush()
    db_session.add_all([runtime_report, runtime_artifact])
    db_session.commit()

    reset_seed(db_session)

    assert db_session.get(ScoreRun, runtime_score_run.id) is not None
    assert db_session.get(Report, runtime_report.id) is not None
    assert db_session.get(ReportArtifact, runtime_artifact.storage_key) is not None
    assert db_session.get(ReportTemplate, runtime_template.id) is not None
    assert db_session.get(ReportTemplate, seed_id("report-template:informe-basico")) is not None


def test_seed_reset_preflight_rejects_runtime_report_over_seed_template(
    engine, db_session
) -> None:
    reset_seed(db_session)
    run_seed(db_session)
    template = db_session.get(
        ReportTemplate, seed_id("report-template:informe-basico")
    )
    assert template is not None
    runtime_report = Report(
        id=uuid.uuid4(),
        session_id=seed_id("session:evaluado_01"),
        template_id=template.id,
        template_version_no=template.version_no,
        format="pdf",
        status="pending",
        synthetic=False,
        source="runtime",
    )
    db_session.add(runtime_report)
    db_session.commit()
    before = (
        db_session.scalar(text("SELECT COUNT(*) FROM report_templates WHERE source = 'seed'")),
        db_session.scalar(text("SELECT COUNT(*) FROM reports")),
    )

    with pytest.raises(SeedResetConflictError) as error:
        reset_seed(db_session)

    assert str(error.value) == "seed_reset_dependency_conflict"
    assert (
        db_session.scalar(text("SELECT COUNT(*) FROM report_templates WHERE source = 'seed'")),
        db_session.scalar(text("SELECT COUNT(*) FROM reports")),
    ) == before
    assert db_session.get(Report, runtime_report.id) is not None
    db_session.delete(runtime_report)
    db_session.commit()


def test_seed_reset_preflight_rejects_runtime_idempotency_for_seed_user(
    engine, db_session
) -> None:
    reset_seed(db_session)
    run_seed(db_session)
    record_id = uuid.uuid4()
    db_session.execute(
        text(
            "INSERT INTO idempotency_records "
            "(id, actor_user_id, operation, resource_scope, idempotency_key, "
            "request_hash, response_status, response_body) "
            "VALUES (:id, :actor_user_id, 'report.generated', 'session:test', "
            "'seed-reset-idempotency', :request_hash, 200, '{}'::jsonb)"
        ),
        {
            "id": record_id,
            "actor_user_id": seed_id("user:admin"),
            "request_hash": "a" * 64,
        },
    )
    db_session.commit()

    with pytest.raises(SeedResetConflictError) as error:
        reset_seed(db_session)

    assert str(error.value) == "seed_reset_dependency_conflict"
    assert db_session.get(IdempotencyRecord, record_id) is not None
    db_session.execute(
        text("DELETE FROM idempotency_records WHERE id = :id"), {"id": record_id}
    )
    db_session.commit()
