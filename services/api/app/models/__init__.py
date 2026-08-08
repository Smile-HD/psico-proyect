"""SQLAlchemy 2 models for all nine table families plus seed_manifest.

Family modules:
  identity, institutions, instruments, sessions, scoring,
  recommendation, reporting, audit, consent, seed
"""

from app.db.base import Base

from .identity import Role, User, UserRole
from .institutions import Campus, Faculty, Institution, Program
from .instruments import (
    Instrument,
    InstrumentItem,
    InstrumentVersion,
    ResponseOption,
    Scale,
)
from .idempotency import IdempotencyRecord
from .sessions import Response, Session
from .scoring import ReferenceSet, ReferenceValue, ScoreRun
from .recommendation import RecommendationResult, RecommendationRule
from .reporting import Report, ReportTemplate
from .audit import AuditLog
from .consent import ConsentGrant, ConsentVersion
from .seed import SeedManifest

__all__ = [
    "Base",
    "User",
    "Role",
    "UserRole",
    "Institution",
    "Campus",
    "Faculty",
    "Program",
    "Instrument",
    "InstrumentVersion",
    "InstrumentItem",
    "Scale",
    "ResponseOption",
    "IdempotencyRecord",
    "Session",
    "Response",
    "ReferenceSet",
    "ReferenceValue",
    "ScoreRun",
    "RecommendationRule",
    "RecommendationResult",
    "Report",
    "ReportTemplate",
    "AuditLog",
    "ConsentVersion",
    "ConsentGrant",
    "SeedManifest",
]
