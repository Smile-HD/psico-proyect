"""Idempotent synthetic seed engine.

Deterministic UUID5 ids under the ``psico-seed:`` namespace + ``INSERT ...
ON CONFLICT (id) DO NOTHING`` upserts (FK order) + a per-run seed_manifest
(counts, sha256 over fixture files, executed_at).

``--reset`` deletes only seed-owned rows (synthetic=true / source='seed'),
in reverse FK order, then re-seeds. Non-seed data is never touched.

Entry points:
    python -m app.seed            # idempotent seed
    python -m app.seed --reset    # reset seed-owned rows, then re-seed
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core import audit
from app.core.auth import hash_password
from app.core.config import settings
from app.models.audit import AuditLog  # noqa: F401  (imported for trigger awareness)
from app.models.consent import ConsentGrant, ConsentVersion
from app.models.identity import Role, User, UserRole
from app.models.institutions import Campus, Faculty, Institution, Program
from app.models.instruments import Instrument, InstrumentItem, InstrumentVersion
from app.models.scoring import ReferenceSet, ReferenceValue
from app.models.seed import SeedManifest
from app.models.sessions import Response, Session

logger = logging.getLogger("psico.seed")

SEED_VERSION = "1.0.0"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

# Tables that carry synthetic/source columns and may hold seed-owned rows,
# listed in FK order (parents before children).
SEED_TABLES = [
    "roles",
    "users",
    "user_roles",
    "institutions",
    "campuses",
    "faculties",
    "programs",
    "instruments",
    "instrument_versions",
    "instrument_items",
    "consent_versions",
    "consent_grants",
    "sessions",
    "responses",
    "reference_sets",
    "reference_values",
]

# Reverse FK order for --reset (children before parents).
SEED_TABLES_REVERSE = list(reversed(SEED_TABLES))


def seed_id(key: str) -> uuid.UUID:
    """Deterministic UUID5 under the pinned psico-seed namespace (contracts)."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"psico-seed:{key}")


def fixtures_checksum() -> str:
    """sha256 over all fixture files (sorted relative paths, concatenated bytes)."""
    hasher = hashlib.sha256()
    for path in sorted(FIXTURES_DIR.rglob("*")):
        if path.is_file():
            hasher.update(path.read_bytes())
    return hasher.hexdigest()


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _upsert(db: Session, model, row: dict, conflict_cols: list[str] | None = None) -> None:
    stmt = (
        pg_insert(model)
        .values(**row)
        .on_conflict_do_nothing(index_elements=conflict_cols or [model.id])
    )
    db.execute(stmt)


def _seed_rows(db: Session) -> None:
    """Insert all seed-owned rows (FK order). Idempotent by deterministic id."""
    # --- roles -------------------------------------------------------------
    role_rows = [
        {"id": seed_id("role:admin"), "name": "admin", "description": "Administrador del sistema (desarrollo)", "synthetic": True, "source": "seed"},
        {"id": seed_id("role:psicologo"), "name": "psicólogo", "description": "Psicólogo/a — aplica sesiones y revisa resultados (desarrollo)", "synthetic": True, "source": "seed"},
        {"id": seed_id("role:evaluado"), "name": "evaluado", "description": "Evaluado/a — participante sintético (desarrollo)", "synthetic": True, "source": "seed"},
    ]
    for row in role_rows:
        _upsert(db, Role, row)

    # --- users (3 dev accounts + 30 profiles) -------------------------------
    dev_users = [
        ("admin", settings.dev_password_admin, "Cuenta de desarrollo — Administrador", "role:admin"),
        ("psicologo", settings.dev_password_psicologo, "Cuenta de desarrollo — Psicólogo", "role:psicologo"),
        ("evaluado", settings.dev_password_evaluado, "Cuenta de desarrollo — Evaluado", "role:evaluado"),
    ]
    profiles = []
    for profile_file in sorted((FIXTURES_DIR / "profiles").glob("*.json")):
        profiles.append(json.loads(profile_file.read_text(encoding="utf-8")))

    user_rows: list[dict] = []
    for username, password, full_name, role_key in dev_users:
        user_rows.append({
            "id": seed_id(f"user:{username}"),
            "username": username,
            "password_hash": hash_password(password),
            "full_name": full_name,
            "email": f"{username}@psico.test",
            "is_active": True,
            "synthetic": True,
            "source": "seed",
        })
    for profile in profiles:
        user_rows.append({
            "id": seed_id(profile["key"]),
            "username": profile["key"],
            "password_hash": hash_password(f"psico-seed-{profile['key']}"),
            "full_name": profile["name"],
            "email": f"{profile['key']}@psico.test",
            "is_active": True,
            "synthetic": True,
            "source": "seed",
        })
    for row in user_rows:
        _upsert(db, User, row)

    # --- user_roles ----------------------------------------------------------
    for username, _pw, _fn, role_key in dev_users:
        _upsert(db, UserRole, {
            "user_id": seed_id(f"user:{username}"),
            "role_id": seed_id(role_key),
            "synthetic": True,
            "source": "seed",
        }, conflict_cols=["user_id", "role_id"])
    for profile in profiles:
        _upsert(db, UserRole, {
            "user_id": seed_id(profile["key"]),
            "role_id": seed_id("role:evaluado"),
            "synthetic": True,
            "source": "seed",
        }, conflict_cols=["user_id", "role_id"])

    # --- institutions (1 synthetic institution, no real UAGRM data) ----------
    inst_id = seed_id("institution:dev")
    _upsert(db, Institution, {
        "id": inst_id, "name": "Institución Sintética de Desarrollo",
        "code": "ISD-001", "synthetic": True, "source": "seed",
    })
    campus_id = seed_id("campus:dev")
    _upsert(db, Campus, {
        "id": campus_id, "institution_id": inst_id, "name": "Campus Sintético",
        "code": "CS-001", "synthetic": True, "source": "seed",
    })
    faculty_id = seed_id("faculty:dev")
    _upsert(db, Faculty, {
        "id": faculty_id, "institution_id": inst_id, "campus_id": campus_id,
        "name": "Facultad Sintética de Ciencias", "code": "FS-001",
        "synthetic": True, "source": "seed",
    })
    program_id = seed_id("program:dev")
    _upsert(db, Program, {
        "id": program_id, "institution_id": inst_id, "faculty_id": faculty_id,
        "name": "Programa Sintético de Orientación", "code": "PS-001",
        "synthetic": True, "source": "seed",
    })

    # --- instrument TP-S-01 (20 items, version 1, published + immutable) ------
    items = _load_json("items.json")
    instrument_id = seed_id(items["key"])  # contract key TP-S-01
    _upsert(db, Instrument, {
        "id": instrument_id, "key": items["key"], "title": items["title"],
        "description": items["description"], "synthetic": True, "source": "seed",
    })
    version_id = seed_id("TP-S-01:v1")
    _upsert(db, InstrumentVersion, {
        "id": version_id, "instrument_id": instrument_id,
        "version_no": items["version_no"], "status": items["status"],
        "published_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "is_immutable": True, "synthetic": True, "source": "seed",
    })
    flat_items: list[tuple[str, int, str]] = []
    for scale in items["scales"]:
        for item in scale["items"]:
            flat_items.append((scale["scale"], item["order"], item["text"]))
    for index, (scale, order, text) in enumerate(flat_items, start=1):
        _upsert(db, InstrumentItem, {
            "id": seed_id(f"TP-S-01:i{index}"),
            "version_id": version_id, "scale": scale, "scale_order": order,
            "text": text, "synthetic": True, "source": "seed",
        })

    # --- reference set RS-TP-S-01 (synthetic / research-only) ------------------
    reference = _load_json("reference.json")
    ref_id = seed_id(reference["key"])  # contract key RS-TP-S-01
    _upsert(db, ReferenceSet, {
        "id": ref_id, "key": reference["key"], "instrument_version_id": version_id,
        "reference_status": reference["reference_status"], "use": reference["use"],
        "norm_note": reference["norm_note"], "synthetic": True, "source": "seed",
    })
    for value in reference["values"]:
        _upsert(db, ReferenceValue, {
            "id": seed_id(f"RS-TP-S-01:{value['scale']}:{value['value_type']}:{value.get('raw_value', '')}"),
            "reference_set_id": ref_id, "scale": value["scale"],
            "value_type": value["value_type"],
            "raw_value": value.get("raw_value"),
            "percentile": value.get("percentile"),
            "t_score": value.get("t_score"),
            "eneatype": value.get("eneatype"),
            "synthetic": True, "source": "seed",
        })

    # --- consent template + grants for the 30 profiles --------------------------
    consent_id = seed_id("consent:v1")
    consent_body = (
        "**Consentimiento informado (investigación — datos sintéticos)**\n\n"
        "Este entorno es de desarrollo. Todos los datos son sintéticos y "
        "marcados como research-only; no corresponden a personas reales ni a "
        "normas UAGRM. Al firmar, aceptás que tus respuestas sintéticas se "
        "usen para probar el sistema. Podés revocar el consentimiento en "
        "cualquier momento."
    )
    _upsert(db, ConsentVersion, {
        "id": consent_id, "version_no": 1,
        "title": "Consentimiento informado de investigación (sintético)",
        "body": consent_body, "effective_from": datetime(2026, 1, 1).date(),
        "is_active": True, "synthetic": True, "source": "seed",
    })
    for profile in profiles:
        user_id = seed_id(profile["key"])
        grant_id = seed_id(f"grant:{profile['key']}")
        _upsert(db, ConsentGrant, {
            "id": grant_id, "user_id": user_id, "consent_version_id": consent_id,
            "state": "granted",
            "signed_at": datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
            "ip": "127.0.0.1", "synthetic": True, "source": "seed",
        })
        session_id = seed_id(f"session:{profile['key']}")
        _upsert(db, Session, {
            "id": session_id, "user_id": user_id, "instrument_version_id": version_id,
            "consent_grant_id": grant_id, "status": "completed",
            "started_at": datetime(2026, 1, 15, 10, 5, tzinfo=timezone.utc),
            "completed_at": datetime(2026, 1, 15, 10, 25, tzinfo=timezone.utc),
            "synthetic": True, "source": "seed",
        })
        for index, value in enumerate(profile["responses"], start=1):
            _upsert(db, Response, {
                "id": seed_id(f"response:{profile['key']}:i{index}"),
                "session_id": session_id,
                "item_id": seed_id(f"TP-S-01:i{index}"),
                "value": value, "synthetic": True, "source": "seed",
            })


def collect_counts(db: Session) -> dict:
    """Seeded row counts per table (source='seed') plus manifest runs."""
    counts: dict = {}
    for table in SEED_TABLES:
        raw = db.execute(
            text(f"SELECT COUNT(*) FROM {table} WHERE source = 'seed'")
        ).scalar()
        counts[table] = int(raw or 0)
    counts["seed_manifest_runs"] = db.scalar(
        select(func.count()).select_from(SeedManifest)
    ) or 0
    return counts


def _write_manifest(db: Session, counts: dict) -> dict:
    manifest = SeedManifest(
        seed_version=SEED_VERSION,
        counts=counts,
        checksum=fixtures_checksum(),
        executed_at=datetime.now(timezone.utc),
    )
    db.add(manifest)
    db.flush()
    return {
        "seed_version": manifest.seed_version,
        "counts": manifest.counts,
        "checksum": manifest.checksum,
        "executed_at": manifest.executed_at.isoformat() if manifest.executed_at else None,
    }


def _reset_seed_rows(db: Session) -> None:
    """Delete seed-owned rows only (source='seed'), children before parents."""
    for table in SEED_TABLES_REVERSE:
        db.execute(text(f"DELETE FROM {table} WHERE source = 'seed'"))
    db.execute(delete(SeedManifest))


def run_seed(db: Session) -> dict:
    """Idempotent seed + manifest + seed.executed audit event. Returns summary."""
    try:
        _seed_rows(db)
        counts = collect_counts(db)
        manifest = _write_manifest(db, counts)
        audit.record(
            db,
            "seed.executed",
            actor_user_id=None,
            actor_role=None,
            resource_type="seed",
            action="run",
            outcome="allowed",
            metadata={"seed_version": SEED_VERSION, "checksum": manifest["checksum"]},
            commit=False,
        )
        db.commit()
        return manifest
    except Exception:
        db.rollback()
        raise


def reset_seed(db: Session) -> dict:
    """--reset: delete seed-owned rows (reverse FK order), then re-seed."""
    try:
        _reset_seed_rows(db)
        _seed_rows(db)
        counts = collect_counts(db)
        manifest = _write_manifest(db, counts)
        audit.record(
            db,
            "seed.executed",
            actor_user_id=None,
            actor_role=None,
            resource_type="seed",
            action="reset",
            outcome="allowed",
            metadata={"seed_version": SEED_VERSION, "checksum": manifest["checksum"]},
            commit=False,
        )
        db.commit()
        return manifest
    except Exception:
        db.rollback()
        raise
