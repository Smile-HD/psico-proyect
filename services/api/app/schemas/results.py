"""Pydantic v2 response DTOs for the persisted results API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ResultsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class ScoreTransformed(ResultsModel):
    percentile: int
    t_score: int
    eneatype: int


class ScoreDirect(ResultsModel):
    z: float


class ScaleResult(ResultsModel):
    label: str
    raw: int
    direct: ScoreDirect
    transformed: ScoreTransformed


class OverallResult(ResultsModel):
    raw: int
    transformed: ScoreTransformed


class ScoreRunResult(ResultsModel):
    id: UUID
    status: Literal["completed"]
    computed_at: datetime


class ResultsResponse(ResultsModel):
    session_id: UUID
    run: ScoreRunResult
    reference_set_id: UUID
    norm_note: str
    scales: list[ScaleResult]
    overall: OverallResult


# Compatibility aliases make the DTO vocabulary explicit for route consumers.
ResultResponse = ResultsResponse
ResultScale = ScaleResult
ResultOverall = OverallResult
ResultRun = ScoreRunResult
