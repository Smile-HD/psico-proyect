"""Strict request and response DTOs for the F6 reports API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ReportGenerateRequest(ReportModel):
    """The report trigger has no client-selectable options."""


class ReportMetadata(ReportModel):
    id: UUID
    session_id: UUID
    template_id: UUID
    template_version_no: int = Field(gt=0)
    status: Literal["pending", "processing", "ready", "failed"]
    format: Literal["pdf"]
    generated_at: datetime | None = None
    checksum: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    byte_size: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_artifact_projection(self) -> "ReportMetadata":
        if self.status == "ready" and (
            self.checksum is None or self.byte_size is None
        ):
            raise ValueError("ready reports require checksum and byte_size")
        if self.status != "ready" and (
            self.checksum is not None or self.byte_size is not None
        ):
            raise ValueError("non-ready reports cannot expose artifact metadata")
        return self


# Compatibility aliases keep route-facing vocabulary explicit.
ReportResponse = ReportMetadata
ReportGenerateResponse = ReportMetadata
