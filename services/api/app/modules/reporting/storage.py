"""PostgreSQL BYTEA storage seam for opaque report artifacts."""

from __future__ import annotations

import hashlib
import io
import uuid
from dataclasses import dataclass
from typing import BinaryIO

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session as DbSession

from app.models.reporting import Report, ReportArtifact


PDF_MEDIA_TYPE = "application/pdf"


class ArtifactNotFoundError(LookupError):
    """The requested opaque artifact key does not exist."""


class ArtifactConflictError(ValueError):
    """The same report already owns a different artifact."""


@dataclass(frozen=True)
class ArtifactMetadata:
    storage_key: str
    sha256: str
    byte_size: int
    media_type: str

    @property
    def checksum(self) -> str:
        return self.sha256


@dataclass
class ArtifactStream:
    """A file-like in-memory stream with metadata but no path or URL."""

    metadata: ArtifactMetadata
    stream: BinaryIO

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)

    def close(self) -> None:
        self.stream.close()

    def __enter__(self) -> "ArtifactStream":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def _opaque_key(value: str) -> str:
    try:
        parsed = uuid.UUID(str(value))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("storage key must be an opaque UUID4") from error
    if parsed.version != 4 or str(parsed) != str(value).lower():
        raise ValueError("storage key must be an opaque UUID4")
    return str(parsed)


def _report_id(value: uuid.UUID | str) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError("report id must be a UUID") from error


def _metadata(row: ReportArtifact) -> ArtifactMetadata:
    return ArtifactMetadata(
        storage_key=row.storage_key,
        sha256=row.sha256,
        byte_size=row.byte_size,
        media_type=row.media_type,
    )


class PostgresReportStorage:
    """Caller-owned PostgreSQL artifact storage with idempotent operations."""

    def put(
        self,
        db: DbSession,
        *,
        report_id: uuid.UUID | str,
        payload: bytes | bytearray | memoryview,
        media_type: str = PDF_MEDIA_TYPE,
    ) -> ArtifactMetadata:
        report_uuid = _report_id(report_id)
        if not isinstance(payload, (bytes, bytearray, memoryview)):
            raise TypeError("artifact payload must be bytes-like")
        body = bytes(payload)
        if not media_type.strip():
            raise ValueError("artifact media type is required")
        digest = hashlib.sha256(body).hexdigest()
        current = db.scalar(
            select(ReportArtifact).where(ReportArtifact.report_id == report_uuid)
        )
        if current is not None:
            if (
                current.sha256 != digest
                or current.byte_size != len(body)
                or current.media_type != media_type
                or bytes(current.payload) != body
            ):
                raise ArtifactConflictError("report already owns a different artifact")
            return _metadata(current)

        artifact = ReportArtifact(
            storage_key=str(uuid.uuid4()),
            report_id=report_uuid,
            payload=body,
            sha256=digest,
            byte_size=len(body),
            media_type=media_type,
        )
        db.add(artifact)
        db.flush()
        return _metadata(artifact)

    def open(self, db: DbSession, storage_key: str) -> ArtifactStream:
        key = _opaque_key(storage_key)
        artifact = db.scalar(
            select(ReportArtifact).where(ReportArtifact.storage_key == key)
        )
        if artifact is None:
            raise ArtifactNotFoundError("artifact not found")
        return ArtifactStream(_metadata(artifact), io.BytesIO(bytes(artifact.payload)))

    def delete(self, db: DbSession, storage_key: str) -> bool:
        key = _opaque_key(storage_key)
        artifact = db.scalar(
            select(ReportArtifact).where(ReportArtifact.storage_key == key)
        )
        if artifact is None:
            return False
        db.delete(artifact)
        db.flush()
        return True

    def cleanup_orphans(self, db: DbSession) -> int:
        statement = delete(ReportArtifact).where(
            ~exists(select(Report.id).where(Report.id == ReportArtifact.report_id))
        )
        result = db.execute(statement)
        db.flush()
        return int(result.rowcount or 0)


PostgresArtifactStorage = PostgresReportStorage
ReportStorage = PostgresReportStorage
