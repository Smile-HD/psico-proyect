"""Pydantic v2 request/response DTOs for the F3 session delivery API.

All DTOs use ``extra='forbid'`` to reject unexpected fields at the API
boundary and ``from_attributes=True`` to allow direct mapping from
SQLAlchemy model instances.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SessionModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------


class SessionCreate(SessionModel):
    """POST /api/v1/sessions — create a new in-progress session."""

    instrument_version_id: UUID | str


class ResponseCreate(SessionModel):
    """POST /api/v1/sessions/{id}/responses — idempotent item autosave.

    ``item_id`` references an InstrumentItem that must belong to the
    session's locked instrument version.  ``value`` must satisfy the
    Likert 1-5 constraint enforced both here (Pydantic) and in the DB.
    """

    item_id: UUID
    value: int = Field(..., ge=1, le=5)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class SessionCreateResponse(SessionModel):
    """Returned by POST /api/v1/sessions."""

    id: UUID
    status: str
    instrument_version_id: UUID
    started_at: datetime


class SavedResponseRead(SessionModel):
    """A single saved response returned inside the resume envelope."""

    item_id: UUID
    value: int


class SessionResumeResponse(SessionModel):
    """Returned by GET /api/v1/sessions/{id}/resume.

    ``remaining_seconds`` is calculated server-side from the instrument's
    duration_minutes and the elapsed time since ``started_at``.  A value
    of ``None`` means the instrument has no time limit.
    """

    id: UUID
    status: str
    instrument_version_id: UUID
    started_at: datetime
    remaining_seconds: float | None
    saved_responses: list[SavedResponseRead]


class ResponseSaveResponse(SessionModel):
    """Returned by POST /api/v1/sessions/{id}/responses."""

    response_id: UUID
    item_id: UUID
    value: int
    created: bool  # True on first save, False on idempotent replay


class SessionSubmitResponse(SessionModel):
    """Returned by POST /api/v1/sessions/{id}/submit."""

    id: UUID
    status: str
    completed_at: datetime
    response_count: int
