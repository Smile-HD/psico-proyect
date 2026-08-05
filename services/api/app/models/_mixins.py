"""Shared model columns: the seed-marker contract.

Every seeded row MUST set synthetic = true and source = 'seed' where these
columns exist (synthetic-seed spec). Mix this in on domain tables.
"""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column


class SyntheticMixin:
    """Adds the synthetic/source marker columns to a model."""

    synthetic: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="runtime", server_default="runtime"
    )
