"""Pydantic v2 request and response DTOs for the catalog API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Locale = Literal["es"]
ResponseType = Literal["likert_1_5"]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
CatalogKey = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=2,
        max_length=64,
        pattern=r"^[A-Z0-9_.-]+$",
    ),
]


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class AdaptationMetadata(CatalogModel):
    base_locale: Locale
    target_locale: Locale
    label: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    description: Annotated[str | None, StringConstraints(max_length=1000)] = None


class CreateInstrumentRequest(CatalogModel):
    key: CatalogKey
    title: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    description: Annotated[str | None, StringConstraints(max_length=5000)] = None
    adaptation: AdaptationMetadata | None = None


class CreateDraftVersionRequest(CatalogModel):
    source_version_id: UUID | None = None
    adaptation: AdaptationMetadata | None = None


class OptionInput(CatalogModel):
    id: UUID | None = None
    display_order: Literal[1, 2, 3, 4, 5]
    label: NonEmptyText
    locale: Locale


class ItemInput(CatalogModel):
    id: UUID | None = None
    item_order: Annotated[int, Field(gt=0)]
    text: NonEmptyText
    locale: Locale
    required: bool = True
    options: Annotated[list[OptionInput], Field(min_length=5, max_length=5)]


class ScaleInput(CatalogModel):
    id: UUID | None = None
    display_order: Annotated[int, Field(gt=0)]
    label: NonEmptyText
    locale: Locale
    items: Annotated[list[ItemInput], Field(min_length=1)]


class SaveDraftContentRequest(CatalogModel):
    response_type: ResponseType
    adaptation: AdaptationMetadata | None = None
    scales: Annotated[list[ScaleInput], Field(min_length=1)]


class InstrumentSummary(CatalogModel):
    id: UUID
    key: str
    title: str
    description: str | None
    synthetic: bool
    source: str
    created_at: datetime


class VersionSummary(CatalogModel):
    instrument_version_id: UUID
    instrument_id: UUID
    version_no: int
    status: Literal["draft", "published", "archived"]
    response_type: ResponseType
    is_immutable: bool
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    archived_at: datetime | None = None
    synthetic: bool
    source: str


class CreateInstrumentResponse(CatalogModel):
    instrument: InstrumentSummary
    draft: VersionSummary


class AggregateCounts(CatalogModel):
    scale_count: int
    item_count: int
    option_count: int


class MutationResult(CatalogModel):
    instrument_version_id: UUID
    instrument_id: UUID
    version_no: int
    status: Literal["draft", "published", "archived"]
    is_immutable: bool
    counts: AggregateCounts
    published_at: datetime | None = None
    archived_at: datetime | None = None
    lifecycle_at: datetime | None = None


class AdminOptionRead(CatalogModel):
    id: UUID
    display_order: Literal[1, 2, 3, 4, 5]
    label: str
    locale: Locale


class AdminItemRead(CatalogModel):
    id: UUID
    item_order: int
    text: str
    locale: Locale
    required: bool
    response_options: list[AdminOptionRead]


class AdminScaleRead(CatalogModel):
    id: UUID
    display_order: int
    label: str
    locale: Locale
    items: list[AdminItemRead]


class AdminVersionDetail(CatalogModel):
    """Flat authoring detail for one version.

    Fields mirror VersionSummary plus instrument identity (title, key) so the
    web editor renders header and status without extra lookups.
    """

    instrument_version_id: UUID
    instrument_id: UUID
    version_no: int
    status: Literal["draft", "published", "archived"]
    response_type: ResponseType
    is_immutable: bool
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    archived_at: datetime | None = None
    synthetic: bool
    source: str
    title: str
    instrument_key: str
    adaptation: AdaptationMetadata | None = None
    scales: list[AdminScaleRead]


class PublishedOptionRead(CatalogModel):
    id: UUID
    display_order: Literal[1, 2, 3, 4, 5]
    label: str
    locale: Locale


class PublishedItemRead(CatalogModel):
    id: UUID
    item_order: int
    text: str
    locale: Locale
    required: bool
    response_options: list[PublishedOptionRead]


class PublishedScaleRead(CatalogModel):
    id: UUID
    display_order: int
    label: str
    locale: Locale
    items: list[PublishedItemRead]


class PublishedVersionRead(CatalogModel):
    instrument_version_id: UUID
    instrument_key: str
    title: str
    description: str | None
    version_no: int
    status: Literal["published"]
    published_at: datetime
    response_type: ResponseType
    locale: Locale
    adaptation: AdaptationMetadata | None = None
    scales: list[PublishedScaleRead]


class PublishedVersionSummary(CatalogModel):
    """Public discovery row for one published instrument version.

    The listing intentionally contains only stable identifiers and human-facing
    labels. The full evaluator projection remains behind the version-specific
    published-read endpoint, and never exposes option values here.
    """

    instrument_version_id: UUID
    instrument_key: str
    title: str
    version_no: int


class PublishedVersionsResponse(CatalogModel):
    versions: list[PublishedVersionSummary]


class AdminListRow(VersionSummary):
    """Version row enriched with instrument identity for the authoring list.

    The web catalog table renders key/title per row; keeping the version
    summary fields preserves the archived contract (one row per version).
    """

    key: str
    title: str
    description: str | None = None


class CatalogListResponse(CatalogModel):
    items: list[AdminListRow]
    page: int
    page_size: int
    total: int


class AdminInstrumentDetail(CatalogModel):
    instrument: InstrumentSummary
    read_only: bool
    versions: list[VersionSummary]
