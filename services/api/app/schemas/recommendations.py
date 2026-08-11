"""Pydantic v2 response DTOs for the recommendation API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RecommendationModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class RecommendationItem(RecommendationModel):
    program_id: UUID
    program_name: str
    program_code: str
    fit_score: float
    justification: str


class RecommendationsResponse(RecommendationModel):
    session_id: UUID
    generated_at: datetime
    disclaimer: str
    items: list[RecommendationItem]


# Compatibility aliases keep route-facing and singular DTO vocabulary explicit.
RecommendationResponse = RecommendationsResponse
RecommendationResultItem = RecommendationItem
