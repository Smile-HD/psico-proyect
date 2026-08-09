"""Pydantic v2 request and response DTOs for evaluation sessions."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


SessionStatus = Literal["in_progress", "completed"]
ResponseType = Literal["likert_1_5"]
LikertDisplayOrder = Literal[1, 2, 3, 4, 5]


class SessionModel(BaseModel):
    """Shared DTO configuration for stable, numeric-free session contracts."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class StartRequest(SessionModel):
    """Session start input.

    The version is intentionally optional at the DTO boundary. Missing and
    malformed identifiers must reach the service gate and produce the same
    ``NOT_FOUND`` envelope as an unknown or non-published version.
    """

    instrument_version_id: str | None = None

    @field_validator("instrument_version_id", mode="before")
    @classmethod
    def normalize_identifier(cls, value: object) -> object:
        if value is None or isinstance(value, str):
            return value
        return str(value)


class ResponseInput(SessionModel):
    item_id: UUID
    response_option_id: UUID


class BatchResponseRequest(SessionModel):
    responses: list[ResponseInput] = Field(default_factory=list)


class SessionProgress(SessionModel):
    answered: int = Field(ge=0)
    total: int = Field(ge=0)


class SessionSummary(SessionModel):
    id: UUID
    status: SessionStatus
    instrument_version_id: UUID
    started_at: datetime | None = None
    completed_at: datetime | None = None


class SessionListResponse(SessionModel):
    sessions: list[SessionSummary]


class SessionCreatedResponse(SessionModel):
    id: UUID
    status: SessionStatus


class SessionSaveResponse(SessionModel):
    id: UUID
    status: SessionStatus
    saved_count: int = Field(ge=0)


class SessionOption(SessionModel):
    id: UUID
    display_order: LikertDisplayOrder
    label: str
    locale: Literal["es"]


class SessionItem(SessionModel):
    id: UUID
    item_order: int = Field(gt=0)
    text: str
    locale: Literal["es"]
    required: bool
    response_options: list[SessionOption]
    response_option_id: UUID | None = None


class SessionScale(SessionModel):
    id: UUID
    display_order: int = Field(gt=0)
    label: str
    locale: Literal["es"]
    items: list[SessionItem]


class SessionProjection(SessionModel):
    instrument_version_id: UUID
    version_no: int = Field(gt=0)
    response_type: ResponseType
    scales: list[SessionScale]


class SessionDetail(SessionModel):
    id: UUID
    status: SessionStatus
    instrument_version_id: UUID
    progress: SessionProgress
    projection: SessionProjection | None = None


# Compatibility aliases keep the route/request names used by earlier F1/F3
# callers while the canonical DTOs live in this module.
SessionStartRequest = StartRequest
ResponseBatchRequest = BatchResponseRequest
SessionResponseBatchRequest = BatchResponseRequest
SessionCompleteResponse = SessionCreatedResponse
