"""Application service for the synthetic instrument catalog lifecycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit
from app.core.errors import CONFLICT, NOT_FOUND, ApiError
from app.models.instruments import (
    Instrument,
    InstrumentItem,
    InstrumentVersion,
    ResponseOption,
    Scale,
)
from app.modules.assessment_authoring import domain
from app.modules.assessment_authoring.domain import CatalogValidationError
from app.modules.assessment_authoring.errors import (
    archive_requires_published,
    catalog_validation,
    duplicate_instrument_key,
    resource_not_found,
    seed_catalog_read_only,
    version_immutable,
    version_not_draft,
)
from app.modules.assessment_authoring.idempotency import (
    IdempotencyReplay,
    lookup_idempotency,
    store_idempotency,
)
from app.modules.assessment_authoring.repository import CatalogRepository
from app.schemas.catalog import (
    AdminInstrumentDetail,
    AdminItemRead,
    AdminListRow,
    AdminOptionRead,
    AdminScaleRead,
    AdminVersionDetail,
    AggregateCounts,
    CatalogListResponse,
    CreateDraftVersionRequest,
    CreateInstrumentRequest,
    CreateInstrumentResponse,
    InstrumentSummary,
    MutationResult,
    PublishedItemRead,
    PublishedOptionRead,
    PublishedScaleRead,
    PublishedVersionRead,
    PublishedVersionSummary,
    PublishedVersionsResponse,
    SaveDraftContentRequest,
    VersionSummary,
)


class CatalogService:
    def __init__(self, repository: CatalogRepository | None = None) -> None:
        self.repository = repository or CatalogRepository()

    @staticmethod
    def _request_body(body: Any) -> dict[str, Any]:
        return (
            body.model_dump(mode="json")
            if hasattr(body, "model_dump")
            else dict(body or {})
        )

    @staticmethod
    def _adaptation(body: Any) -> dict[str, Any] | None:
        adaptation = getattr(body, "adaptation", None)
        return adaptation.model_dump(mode="json") if adaptation is not None else None

    @staticmethod
    def _summary(version: InstrumentVersion) -> VersionSummary:
        return VersionSummary(
            instrument_version_id=version.id,
            instrument_id=version.instrument_id,
            version_no=version.version_no,
            status=version.status,
            response_type=version.response_type,
            is_immutable=version.is_immutable,
            created_at=version.created_at,
            updated_at=version.updated_at,
            published_at=version.published_at,
            archived_at=version.archived_at,
            synthetic=version.synthetic,
            source=version.source,
        )

    @staticmethod
    def _instrument_summary(instrument: Instrument) -> InstrumentSummary:
        return InstrumentSummary(
            id=instrument.id,
            key=instrument.key,
            title=instrument.title,
            description=instrument.description,
            synthetic=instrument.synthetic,
            source=instrument.source,
            created_at=instrument.created_at,
        )

    @staticmethod
    def _list_row(version: InstrumentVersion) -> AdminListRow:
        instrument = version.instrument
        return AdminListRow(
            instrument_version_id=version.id,
            instrument_id=version.instrument_id,
            version_no=version.version_no,
            status=version.status,
            response_type=version.response_type,
            is_immutable=version.is_immutable,
            created_at=version.created_at,
            updated_at=version.updated_at,
            published_at=version.published_at,
            archived_at=version.archived_at,
            synthetic=version.synthetic,
            source=version.source,
            key=instrument.key,
            title=instrument.title,
            description=instrument.description,
        )

    @staticmethod
    def _counts_result(
        version: InstrumentVersion, counts: dict[str, int]
    ) -> MutationResult:
        lifecycle_at = version.archived_at or version.published_at
        return MutationResult(
            instrument_version_id=version.id,
            instrument_id=version.instrument_id,
            version_no=version.version_no,
            status=version.status,
            is_immutable=version.is_immutable,
            counts=AggregateCounts(**counts),
            published_at=version.published_at,
            archived_at=version.archived_at,
            lifecycle_at=lifecycle_at,
        )

    @staticmethod
    def _metadata(
        version: InstrumentVersion, counts: dict[str, int], transition: str
    ) -> dict[str, Any]:
        return {
            "instrument_id": str(version.instrument_id),
            "instrument_version_id": str(version.id),
            "version_no": version.version_no,
            "transition": transition,
            **counts,
        }

    @staticmethod
    def _actor_role(user: Any) -> str:
        return ",".join(user.roles)

    def _replay_or_none(
        self,
        db: Session,
        *,
        user: Any,
        operation: str,
        resource_scope: str,
        idempotency_key: str,
        request_body: Any,
    ) -> IdempotencyReplay | None:
        return lookup_idempotency(
            db,
            actor_user_id=user.id,
            operation=operation,
            resource_scope=resource_scope,
            idempotency_key=idempotency_key,
            request_body=request_body,
        )

    def create_instrument(
        self,
        db: Session,
        user: Any,
        body: CreateInstrumentRequest,
        idempotency_key: str,
    ) -> tuple[int, dict[str, Any]]:
        request_body = self._request_body(body)
        scope = f"instrument-key:{body.key}"
        replay = self._replay_or_none(
            db,
            user=user,
            operation="catalog.create_instrument",
            resource_scope=scope,
            idempotency_key=idempotency_key,
            request_body=request_body,
        )
        if replay:
            return replay.status_code, replay.body
        if body.key == "TP-S-01":
            raise seed_catalog_read_only({"key": body.key})
        if db.scalar(select(Instrument).where(Instrument.key == body.key)) is not None:
            raise duplicate_instrument_key({"key": body.key})

        try:
            instrument, version = self.repository.create_instrument(
                db,
                instrument_id=uuid.uuid4(),
                key=body.key,
                title=body.title,
                description=body.description,
                adaptation=self._adaptation(body),
            )
            counts = self.repository.counts(db, version.id)
            audit.record(
                db,
                "instrument.draft_created",
                actor_user_id=user.id,
                actor_role=self._actor_role(user),
                resource_type="instrument_version",
                resource_id=str(version.id),
                action="create",
                metadata=self._metadata(version, counts, "none"),
            )
            response = CreateInstrumentResponse(
                instrument=self._instrument_summary(instrument),
                draft=self._summary(version),
            ).model_dump(mode="json")
            store_idempotency(
                db,
                actor_user_id=user.id,
                operation="catalog.create_instrument",
                resource_scope=scope,
                idempotency_key=idempotency_key,
                request_body=request_body,
                response_status=201,
                response_body=response,
            )
            db.commit()
            return 201, response
        except IntegrityError as error:
            db.rollback()
            diag = getattr(error.orig, "diag", None)
            constraint_name = (
                getattr(diag, "constraint_name", None) if diag is not None else None
            )
            if constraint_name == "instruments_key_key":
                raise duplicate_instrument_key({"key": body.key})
            # Any other integrity failure (e.g. a broken FK in the audit
            # trail) must surface as itself, never as a misleading duplicate.
            raise

    def create_version(
        self,
        db: Session,
        user: Any,
        instrument_id: uuid.UUID,
        body: CreateDraftVersionRequest,
        idempotency_key: str,
    ) -> tuple[int, dict[str, Any]]:
        request_body = self._request_body(body)
        scope = f"instrument:{instrument_id}"
        replay = self._replay_or_none(
            db,
            user=user,
            operation="catalog.create_version",
            resource_scope=scope,
            idempotency_key=idempotency_key,
            request_body=request_body,
        )
        if replay:
            return replay.status_code, replay.body
        instrument = self.repository.get_instrument(db, instrument_id, lock=True)
        if instrument is None:
            raise resource_not_found({"instrument_id": str(instrument_id)})
        if self.repository.is_seed_instrument(instrument):
            raise seed_catalog_read_only({"instrument_id": str(instrument_id)})

        source = None
        if body.source_version_id is not None:
            source = self.repository.get_version(db, body.source_version_id, lock=True)
            if source is None or source.instrument_id != instrument.id:
                raise catalog_validation(
                    "invalid_catalog_version",
                    {"source_version_id": str(body.source_version_id)},
                )
            if source.status != domain.PUBLISHED or self.repository.is_seed_version(
                source
            ):
                raise ApiError(
                    CONFLICT,
                    "invalid_clone_source",
                    details={"source_version_id": str(source.id)},
                )

        version = self.repository.create_version(
            db,
            instrument=instrument,
            version_no=self.repository.next_version_no(db, instrument.id),
            adaptation=self._adaptation(body)
            if body.adaptation is not None
            else (source.adaptation_metadata if source else None),
        )
        if source is not None:
            self._write_cloned_graph(
                db, version, self.repository.aggregate_mapping(source)
            )
        db.flush()
        counts = self.repository.counts(db, version.id)
        audit.record(
            db,
            "instrument.draft_created",
            actor_user_id=user.id,
            actor_role=self._actor_role(user),
            resource_type="instrument_version",
            resource_id=str(version.id),
            action="clone" if source else "create",
            metadata=self._metadata(version, counts, "none"),
        )
        result = self._counts_result(version, counts).model_dump(mode="json")
        store_idempotency(
            db,
            actor_user_id=user.id,
            operation="catalog.create_version",
            resource_scope=scope,
            idempotency_key=idempotency_key,
            request_body=request_body,
            response_status=201,
            response_body=result,
        )
        db.commit()
        return 201, result

    @staticmethod
    def _write_cloned_graph(
        db: Session, version: InstrumentVersion, aggregate: dict[str, Any]
    ) -> None:
        for raw_scale in aggregate.get("scales", []):
            scale = Scale(
                id=uuid.uuid4(),
                version_id=version.id,
                label=raw_scale["label"],
                locale=raw_scale["locale"],
                display_order=raw_scale["display_order"],
                synthetic=True,
                source="runtime",
            )
            db.add(scale)
            db.flush()
            for raw_item in raw_scale.get("items", []):
                item = InstrumentItem(
                    id=uuid.uuid4(),
                    version_id=version.id,
                    scale_id=scale.id,
                    item_order=raw_item["item_order"],
                    locale=raw_item["locale"],
                    required=raw_item["required"],
                    text=raw_item["text"],
                    synthetic=True,
                    source="runtime",
                )
                db.add(item)
                db.flush()
                for raw_option in raw_item.get("options", []):
                    db.add(
                        ResponseOption(
                            id=uuid.uuid4(),
                            item_id=item.id,
                            label=raw_option["label"],
                            locale=raw_option["locale"],
                            display_order=raw_option["display_order"],
                            value=raw_option["value"],
                            synthetic=True,
                            source="runtime",
                        )
                    )

    def save_content(
        self,
        db: Session,
        user: Any,
        version_id: uuid.UUID,
        body: SaveDraftContentRequest,
        idempotency_key: str,
    ) -> tuple[int, dict[str, Any]]:
        request_body = self._request_body(body)
        scope = f"version:{version_id}"
        replay = self._replay_or_none(
            db,
            user=user,
            operation="catalog.save_content",
            resource_scope=scope,
            idempotency_key=idempotency_key,
            request_body=request_body,
        )
        if replay:
            return replay.status_code, replay.body
        version = self.repository.get_version(db, version_id, lock=True)
        self._require_draft(version)
        if self.repository.is_seed_version(version):
            raise seed_catalog_read_only({"instrument_version_id": str(version_id)})
        aggregate = body.model_dump(mode="python")
        aggregate["version_id"] = version.id
        try:
            domain.validate_hierarchy(aggregate, version_id=version.id)
        except CatalogValidationError as error:
            raise catalog_validation(
                "invalid_catalog_version",
                {"path": error.path, "message": error.message},
            )
        self._replace_draft_graph(db, version, aggregate)
        version.adaptation_metadata = self._adaptation(body)
        version.updated_at = datetime.now(timezone.utc)
        db.flush()
        counts = self.repository.counts(db, version.id)
        audit.record(
            db,
            "instrument.draft_updated",
            actor_user_id=user.id,
            actor_role=self._actor_role(user),
            resource_type="instrument_version",
            resource_id=str(version.id),
            action="save",
            metadata=self._metadata(version, counts, "draft->draft"),
        )
        result = self._counts_result(version, counts).model_dump(mode="json")
        store_idempotency(
            db,
            actor_user_id=user.id,
            operation="catalog.save_content",
            resource_scope=scope,
            idempotency_key=idempotency_key,
            request_body=request_body,
            response_status=200,
            response_body=result,
        )
        db.commit()
        return 200, result

    @staticmethod
    def _require_draft(version: InstrumentVersion | None) -> InstrumentVersion:
        if version is None:
            raise resource_not_found()
        if version.status != domain.DRAFT:
            if version.is_immutable:
                raise version_immutable({"instrument_version_id": str(version.id)})
            raise version_not_draft({"instrument_version_id": str(version.id)})
        return version

    @staticmethod
    def _replace_draft_graph(
        db: Session, version: InstrumentVersion, aggregate: dict[str, Any]
    ) -> None:
        existing_scales = {scale.id: scale for scale in version.scales}
        existing_items = {
            item.id: item for scale in version.scales for item in scale.items
        }
        existing_options = {
            option.id: option
            for item in existing_items.values()
            for option in item.response_options
        }
        scale_ids: set[uuid.UUID] = set()
        item_ids: set[uuid.UUID] = set()
        option_ids: set[uuid.UUID] = set()
        for scale_input in aggregate["scales"]:
            scale_ids.add(scale_input.get("id") or uuid.uuid4())
            for item_input in scale_input["items"]:
                item_ids.add(item_input.get("id") or uuid.uuid4())
                for _option_input in item_input["options"]:
                    option_ids.add(_option_input.get("id") or uuid.uuid4())
        # 1) Remove rows absent from the incoming aggregate FIRST and flush, so
        # re-creating them (replace-all payloads carry no ids) cannot collide
        # with the old rows on unique constraints.
        for option_id, option in existing_options.items():
            if option_id not in option_ids:
                db.delete(option)
        for item_id, item in existing_items.items():
            if item_id not in item_ids:
                for option in list(item.response_options):
                    db.delete(option)
                db.delete(item)
        for scale_id, scale in existing_scales.items():
            if scale_id not in scale_ids:
                for item in list(scale.items):
                    for option in list(item.response_options):
                        db.delete(option)
                    db.delete(item)
                db.delete(scale)
        db.flush()
        # 2) Upsert or create every row from the aggregate.
        for scale_input in aggregate["scales"]:
            scale_id = scale_input.get("id") or uuid.uuid4()
            scale_ids.add(scale_id)
            scale = existing_scales.get(scale_id)
            if scale is None and scale_input.get("id") is not None:
                raise catalog_validation(
                    "invalid_catalog_version", {"path": "scales.id"}
                )
            if scale is None:
                scale = Scale(
                    id=scale_id, version_id=version.id, synthetic=True, source="runtime"
                )
                db.add(scale)
            scale.label = scale_input["label"]
            scale.locale = scale_input["locale"]
            scale.display_order = scale_input["display_order"]
            for item_input in scale_input["items"]:
                item_id = item_input.get("id") or uuid.uuid4()
                item_ids.add(item_id)
                item = existing_items.get(item_id)
                if item is None and item_input.get("id") is not None:
                    raise catalog_validation(
                        "invalid_catalog_version", {"path": "scales.items.id"}
                    )
                if item is not None and item.scale_id != scale_id:
                    raise catalog_validation(
                        "invalid_catalog_version", {"path": "scales.items.scale_id"}
                    )
                if item is None:
                    item = InstrumentItem(
                        id=item_id,
                        version_id=version.id,
                        scale_id=scale_id,
                        synthetic=True,
                        source="runtime",
                    )
                    db.add(item)
                item.scale_id = scale_id
                item.version_id = version.id
                item.item_order = item_input["item_order"]
                item.text = item_input["text"]
                item.locale = item_input["locale"]
                item.required = item_input["required"]
                for option_input in item_input["options"]:
                    option_id = option_input.get("id") or uuid.uuid4()
                    option_ids.add(option_id)
                    option = existing_options.get(option_id)
                    if option is None and option_input.get("id") is not None:
                        raise catalog_validation(
                            "invalid_catalog_version", {"path": "options.id"}
                        )
                    if option is not None and option.item_id != item_id:
                        raise catalog_validation(
                            "invalid_catalog_version", {"path": "options.item_id"}
                        )
                    if option is None:
                        option = ResponseOption(
                            id=option_id,
                            item_id=item_id,
                            synthetic=True,
                            source="runtime",
                        )
                        db.add(option)
                    option.item_id = item_id
                    option.display_order = option_input["display_order"]
                    option.value = option_input["display_order"]
                    option.label = option_input["label"]
                    option.locale = option_input["locale"]

    def publish(
        self, db: Session, user: Any, version_id: uuid.UUID, idempotency_key: str
    ) -> tuple[int, dict[str, Any]]:
        scope = f"version:{version_id}"
        request_body: dict[str, Any] = {}
        replay = self._replay_or_none(
            db,
            user=user,
            operation="catalog.publish",
            resource_scope=scope,
            idempotency_key=idempotency_key,
            request_body=request_body,
        )
        if replay:
            return replay.status_code, replay.body
        version = self.repository.get_version(db, version_id, lock=True)
        if version is None:
            raise resource_not_found()
        if version.status != domain.DRAFT:
            raise version_not_draft(
                {"instrument_version_id": str(version_id), "status": version.status}
            )
        if self.repository.is_seed_version(version):
            raise seed_catalog_read_only({"instrument_version_id": str(version_id)})
        try:
            domain.validate_hierarchy(
                self.repository.aggregate_mapping(version), version_id=version.id
            )
            self._assert_runtime_graph(version)
        except CatalogValidationError as error:
            raise catalog_validation(
                "invalid_catalog_version",
                {"path": error.path, "message": error.message},
            )
        db.execute(text("SET LOCAL app.lifecycle_transition = 'publish'"))
        version.status = domain.PUBLISHED
        version.is_immutable = True
        version.published_at = datetime.now(timezone.utc)
        version.updated_at = version.published_at
        db.flush()
        counts = self.repository.counts(db, version.id)
        audit.record(
            db,
            "instrument.published",
            actor_user_id=user.id,
            actor_role=self._actor_role(user),
            resource_type="instrument_version",
            resource_id=str(version.id),
            action="publish",
            metadata=self._metadata(version, counts, "draft->published"),
        )
        result = self._counts_result(version, counts).model_dump(mode="json")
        store_idempotency(
            db,
            actor_user_id=user.id,
            operation="catalog.publish",
            resource_scope=scope,
            idempotency_key=idempotency_key,
            request_body=request_body,
            response_status=200,
            response_body=result,
        )
        db.commit()
        return 200, result

    @staticmethod
    def _assert_runtime_graph(version: InstrumentVersion) -> None:
        rows = [version, *version.scales]
        rows.extend(item for scale in version.scales for item in scale.items)
        rows.extend(
            option
            for scale in version.scales
            for item in scale.items
            for option in item.response_options
        )
        if any(not row.synthetic or row.source != "runtime" for row in rows):
            raise CatalogValidationError(
                "runtime catalog rows must be synthetic and runtime sourced"
            )

    def archive(
        self, db: Session, user: Any, version_id: uuid.UUID, idempotency_key: str
    ) -> tuple[int, dict[str, Any]]:
        scope = f"version:{version_id}"
        request_body: dict[str, Any] = {}
        replay = self._replay_or_none(
            db,
            user=user,
            operation="catalog.archive",
            resource_scope=scope,
            idempotency_key=idempotency_key,
            request_body=request_body,
        )
        if replay:
            return replay.status_code, replay.body
        version = self.repository.get_version(db, version_id, lock=True)
        if version is None:
            raise resource_not_found()
        if version.status != domain.PUBLISHED:
            raise archive_requires_published(
                {"instrument_version_id": str(version_id), "status": version.status}
            )
        db.execute(text("SET LOCAL app.lifecycle_transition = 'archive'"))
        now = datetime.now(timezone.utc)
        version.status = domain.ARCHIVED
        version.archived_at = now
        version.updated_at = now
        version.is_immutable = True
        db.flush()
        counts = self.repository.counts(db, version.id)
        audit.record(
            db,
            "instrument.archived",
            actor_user_id=user.id,
            actor_role=self._actor_role(user),
            resource_type="instrument_version",
            resource_id=str(version.id),
            action="archive",
            metadata=self._metadata(version, counts, "published->archived"),
        )
        result = self._counts_result(version, counts).model_dump(mode="json")
        store_idempotency(
            db,
            actor_user_id=user.id,
            operation="catalog.archive",
            resource_scope=scope,
            idempotency_key=idempotency_key,
            request_body=request_body,
            response_status=200,
            response_body=result,
        )
        db.commit()
        return 200, result

    def published_read(
        self, db: Session, version_id: uuid.UUID
    ) -> PublishedVersionRead:
        version = self.repository.get_version(db, version_id)
        if version is None or version.status != domain.PUBLISHED:
            raise ApiError(NOT_FOUND, "resource_not_found")
        scales: list[PublishedScaleRead] = []
        for scale in sorted(version.scales, key=lambda row: row.display_order):
            items: list[PublishedItemRead] = []
            for item in sorted(scale.items, key=lambda row: row.item_order):
                items.append(
                    PublishedItemRead(
                        id=item.id,
                        item_order=item.item_order,
                        text=item.text,
                        locale=item.locale,
                        required=item.required,
                        response_options=[
                            PublishedOptionRead(
                                id=option.id,
                                display_order=option.display_order,
                                label=option.label,
                                locale=option.locale,
                            )
                            for option in sorted(
                                item.response_options, key=lambda row: row.display_order
                            )
                        ],
                    )
                )
            scales.append(
                PublishedScaleRead(
                    id=scale.id,
                    display_order=scale.display_order,
                    label=scale.label,
                    locale=scale.locale,
                    items=items,
                )
            )
        return PublishedVersionRead(
            instrument_version_id=version.id,
            instrument_key=version.instrument.key,
            title=version.instrument.title,
            description=version.instrument.description,
            version_no=version.version_no,
            status="published",
            published_at=version.published_at,
            response_type=version.response_type,
            locale="es",
            adaptation=version.adaptation_metadata,
            scales=scales,
        )

    def published_list(self, db: Session) -> PublishedVersionsResponse:
        """Return discovery-safe summaries for published versions only."""

        return PublishedVersionsResponse(
            versions=[
                PublishedVersionSummary(
                    instrument_version_id=version.id,
                    instrument_key=version.instrument.key,
                    title=version.instrument.title,
                    version_no=version.version_no,
                )
                for version in self.repository.list_published_versions(db)
            ]
        )

    def admin_list(
        self,
        db: Session,
        page: int,
        page_size: int,
        key: str | None,
        status: str | None,
    ) -> CatalogListResponse:
        rows, total = self.repository.list_instruments(
            db, page=page, page_size=page_size, key=key, status=status
        )
        return CatalogListResponse(
            items=[self._list_row(row) for row in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    def admin_instrument(
        self, db: Session, instrument_id: uuid.UUID
    ) -> AdminInstrumentDetail:
        instrument = self.repository.get_instrument(db, instrument_id)
        if instrument is None:
            raise resource_not_found({"instrument_id": str(instrument_id)})
        versions = list(
            db.scalars(
                select(InstrumentVersion)
                .where(InstrumentVersion.instrument_id == instrument_id)
                .order_by(InstrumentVersion.version_no)
            ).all()
        )
        return AdminInstrumentDetail(
            instrument=self._instrument_summary(instrument),
            read_only=self.repository.is_seed_instrument(instrument),
            versions=[self._summary(version) for version in versions],
        )

    def admin_version(self, db: Session, version_id: uuid.UUID) -> AdminVersionDetail:
        version = self.repository.get_version(db, version_id)
        if version is None:
            raise resource_not_found({"instrument_version_id": str(version_id)})
        scales: list[AdminScaleRead] = []
        for scale in sorted(version.scales, key=lambda row: row.display_order):
            scales.append(
                AdminScaleRead(
                    id=scale.id,
                    display_order=scale.display_order,
                    label=scale.label,
                    locale=scale.locale,
                    items=[
                        AdminItemRead(
                            id=item.id,
                            item_order=item.item_order,
                            text=item.text,
                            locale=item.locale,
                            required=item.required,
                            response_options=[
                                AdminOptionRead(
                                    id=option.id,
                                    display_order=option.display_order,
                                    label=option.label,
                                    locale=option.locale,
                                )
                                for option in sorted(
                                    item.response_options,
                                    key=lambda row: row.display_order,
                                )
                            ],
                        )
                        for item in sorted(scale.items, key=lambda row: row.item_order)
                    ],
                )
            )
        return AdminVersionDetail(
            instrument_version_id=version.id,
            instrument_id=version.instrument_id,
            version_no=version.version_no,
            status=version.status,
            response_type=version.response_type,
            is_immutable=version.is_immutable,
            created_at=version.created_at,
            updated_at=version.updated_at,
            published_at=version.published_at,
            archived_at=version.archived_at,
            synthetic=version.synthetic,
            source=version.source,
            title=version.instrument.title,
            instrument_key=version.instrument.key,
            adaptation=version.adaptation_metadata,
            scales=scales,
        )


service = CatalogService()
