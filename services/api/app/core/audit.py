"""Audit catalog + append-only audit writing (audit-consent spec).

Events write to audit_log. The DB trigger rejects UPDATE/DELETE; the app role
has INSERT+SELECT only. The deny-list forbids logging raw responses, PII
beyond the actor id, tokens/passwords, and instrument item content.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.audit import AuditLog

logger = logging.getLogger("psico.api.audit")

EVENT_CATALOG = {
    "auth.login",
    "auth.denied",
    "user.role_changed",
    "instrument.published",
    "consent.granted",
    "consent.revoked",
    "session.started",
    "session.completed",
    "session.blocked_without_consent",
    "seed.executed",
}

# Substrings that MUST NEVER appear in audit metadata (deny-list).
DENY_LIST = ("password", "token", "response", "item_text", "pii", "secret")


def assert_deny_list(metadata: dict | None) -> None:
    """Raise ValueError if any metadata key/value touches the deny-list."""
    if not metadata:
        return
    for key, value in metadata.items():
        key_low = key.lower()
        for banned in DENY_LIST:
            if banned in key_low:
                raise ValueError(f"deny-list violation on metadata key: {key!r}")
        if isinstance(value, str) and any(banned in value.lower() for banned in DENY_LIST):
            raise ValueError(f"deny-list violation in metadata value of {key!r}")


def record(
    db: Session,
    event_type: str,
    *,
    actor_user_id: uuid.UUID | None = None,
    actor_role: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    action: str | None = None,
    outcome: str = "allowed",
    metadata: dict | None = None,
    commit: bool = False,
    occurred_at: datetime | None = None,
) -> AuditLog:
    if event_type not in EVENT_CATALOG:
        raise ValueError(f"unknown audit event type: {event_type!r}")
    assert_deny_list(metadata)
    row = AuditLog(
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_role=actor_role,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        outcome=outcome,
        metadata_=metadata or {},
        occurred_at=occurred_at or datetime.now(),
    )
    db.add(row)
    if commit:
        db.commit()
    return row
