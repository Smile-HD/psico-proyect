"""ReportLab adapter for deterministic, Spanish professional reports."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone as utc_timezone, tzinfo
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol
from zoneinfo import ZoneInfo

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfdoc import TimeStamp
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.modules.reporting.domain import ReportDocument


PDF_MEDIA_TYPE = "application/pdf"
REPORT_RENDERER_VERSION = "reportlab-4.4.10"
FONT_NAME = "DejaVuSans"
DEFAULT_FONT_PATH = Path(__file__).with_name("fonts") / "DejaVuSans.ttf"


class ReportRenderError(RuntimeError):
    """A renderer failure that must be mapped by the reporting service."""


@dataclass(frozen=True)
class RenderedReport:
    """PDF bytes and the controlled metadata needed by the persistence seam."""

    payload: bytes
    media_type: str
    renderer_version: str
    metadata: Mapping[str, str]

    @property
    def content(self) -> bytes:
        return self.payload


class ReportRenderer(Protocol):
    """Replaceable renderer boundary consumed by the reporting service."""

    def render(self, document: ReportDocument) -> RenderedReport:
        ...


Clock = Callable[[], datetime]


def _timezone(value: tzinfo | str) -> tuple[tzinfo, str]:
    if isinstance(value, str):
        try:
            zone = ZoneInfo(value)
        except Exception as error:
            raise ValueError(f"unknown timezone: {value}") from error
        return zone, value
    if not isinstance(value, tzinfo):
        raise TypeError("timezone must be a tzinfo or IANA timezone name")
    name = getattr(value, "key", None)
    if name:
        return value, name
    if value == utc_timezone.utc:
        return value, "UTC"
    return value, str(value)


def _text(value: Any) -> str:
    return escape(str(value)).replace("\n", "<br/>")


class ReportLabRenderer:
    """Render a ``ReportDocument`` without system-font or wall-clock drift."""

    renderer_version = REPORT_RENDERER_VERSION

    def __init__(
        self,
        *,
        locale: str = "es",
        timezone: tzinfo | str = "UTC",
        clock: Clock | None = None,
        font_path: str | Path | None = None,
    ) -> None:
        if locale != "es":
            raise ValueError("only the Spanish locale ('es') is ratified")
        self.locale = locale
        self._timezone, self.timezone_name = _timezone(timezone)
        self._clock = clock or (lambda: datetime.now(utc_timezone.utc))
        self.font_path = Path(font_path) if font_path is not None else DEFAULT_FONT_PATH
        self._register_font()

    def _register_font(self) -> None:
        if not self.font_path.is_file():
            raise ReportRenderError("configured report font is unavailable")
        if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            try:
                pdfmetrics.registerFont(TTFont(FONT_NAME, str(self.font_path)))
            except Exception as error:
                raise ReportRenderError("configured report font cannot be registered") from error

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime):
            raise ReportRenderError("report clock must return datetime")
        if value.tzinfo is None:
            value = value.replace(tzinfo=utc_timezone.utc)
        return value.astimezone(self._timezone)

    def _styles(self) -> dict[str, ParagraphStyle]:
        body = ParagraphStyle(
            "ReportBody",
            fontName=FONT_NAME,
            fontSize=9.5,
            leading=13,
            alignment=TA_LEFT,
            spaceAfter=4,
        )
        return {
            "title": ParagraphStyle(
                "ReportTitle",
                parent=body,
                fontSize=18,
                leading=22,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#1F2937"),
                spaceAfter=5,
            ),
            "session": ParagraphStyle(
                "ReportSession",
                parent=body,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#4B5563"),
                spaceAfter=12,
            ),
            "heading": ParagraphStyle(
                "ReportHeading",
                parent=body,
                fontSize=12,
                leading=15,
                textColor=colors.HexColor("#111827"),
                spaceBefore=9,
                spaceAfter=6,
            ),
            "body": body,
            "label": ParagraphStyle(
                "ReportLabel",
                parent=body,
                fontSize=9,
                leading=12,
                textColor=colors.HexColor("#374151"),
            ),
        }

    @staticmethod
    def _table(data: list[list[Any]], widths: list[float]) -> Table:
        table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("LEADING", (0, 0), (-1, -1), 11),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9CA3AF")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        return table

    def _story(self, document: ReportDocument, styles: dict[str, ParagraphStyle]) -> list[Any]:
        story: list[Any] = [
            Paragraph("Informe de orientación", styles["title"]),
            Paragraph(f"Sesión: {_text(document.session_id)}", styles["session"]),
            Paragraph("Puntuaciones por escala", styles["heading"]),
        ]
        score_rows: list[list[Any]] = [
            [
                "Escala",
                "Puntaje bruto",
                "Z",
                "Percentil",
                "T",
                "Eneatipo",
            ]
        ]
        score_rows.extend(
            [
                _text(score.label),
                _text(score.raw),
                _text(score.z),
                _text(score.percentile),
                _text(score.t_score),
                _text(score.eneatype),
            ]
            for score in document.scores
        )
        story.append(self._table(score_rows, [39 * mm, 25 * mm, 16 * mm, 23 * mm, 13 * mm, 22 * mm]))
        story.extend(
            [
                Spacer(1, 4 * mm),
                Paragraph("Puntuación general", styles["heading"]),
            ]
        )
        overall = document.overall
        story.append(
            self._table(
                [
                    ["Puntaje bruto", "Percentil", "T", "Eneatipo"],
                    [
                        _text(overall.raw),
                        _text(overall.percentile),
                        _text(overall.t_score),
                        _text(overall.eneatype),
                    ],
                ],
                [32 * mm, 28 * mm, 20 * mm, 25 * mm],
            )
        )
        story.extend(
            [
                Spacer(1, 4 * mm),
                Paragraph("Recomendaciones por programa", styles["heading"]),
            ]
        )
        for recommendation in document.recommendations:
            story.extend(
                [
                    Paragraph(f"Programa: {_text(recommendation.program_name)}", styles["label"]),
                    Paragraph(f"Ajuste: {_text(recommendation.fit_score)}", styles["body"]),
                    Paragraph(
                        f"Justificación: {_text(recommendation.justification)}",
                        styles["body"],
                    ),
                ]
            )
        story.extend(
            [
                Spacer(1, 4 * mm),
                Paragraph("Baremo", styles["heading"]),
                Paragraph(_text(document.norm_note), styles["body"]),
                Spacer(1, 2 * mm),
                Paragraph("Descargo de responsabilidad", styles["heading"]),
                Paragraph(_text(document.disclaimer), styles["body"]),
            ]
        )
        return story

    def _decorate_page(self, canvas: Any, document: Any, generated_at: datetime) -> None:
        canvas.saveState()
        canvas.setTitle("TestPsico - Informe sintetico")
        canvas.setAuthor("TestPsico")
        canvas.setSubject("Synthetic research-only report")
        canvas.setCreator("TestPsico")
        # ReportLab's default producer identifies the renderer and can include
        # vendor internals in metadata. Replace it with the application owner.
        if hasattr(canvas, "_doc") and hasattr(canvas._doc, "info"):
            canvas._doc.info.producer = "TestPsico"
            timestamp = TimeStamp(invariant=True)
            timestamp.t = generated_at.timestamp()
            timestamp.lt = (
                generated_at.year,
                generated_at.month,
                generated_at.day,
                generated_at.hour,
                generated_at.minute,
                generated_at.second,
            )
            timestamp.YMDhms = timestamp.lt
            offset_minutes = int(
                (generated_at.utcoffset() or utc_timezone.utc.utcoffset(None)).total_seconds()
                / 60
            )
            timestamp.dhh, timestamp.dmm = divmod(offset_minutes, 60)
            timestamp.tzname = self.timezone_name
            canvas._doc._timeStamp = timestamp
        canvas.setFont(FONT_NAME, 8)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Página {document.page}")
        canvas.restoreState()

    def render(self, document: ReportDocument) -> RenderedReport:
        if not isinstance(document, ReportDocument):
            raise ReportRenderError("a ReportDocument is required")
        generated_at = self._now()
        buffer = BytesIO()
        styles = self._styles()
        try:
            pdf = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                leftMargin=18 * mm,
                rightMargin=18 * mm,
                topMargin=16 * mm,
                bottomMargin=18 * mm,
                title="TestPsico - Informe sintetico",
                author="TestPsico",
            )
            pdf.build(
                self._story(document, styles),
                onFirstPage=lambda canvas, doc: self._decorate_page(
                    canvas, doc, generated_at
                ),
                onLaterPages=lambda canvas, doc: self._decorate_page(
                    canvas, doc, generated_at
                ),
            )
        except Exception as error:
            raise ReportRenderError("report PDF rendering failed") from error

        return RenderedReport(
            payload=buffer.getvalue(),
            media_type=PDF_MEDIA_TYPE,
            renderer_version=self.renderer_version,
            metadata={
                "locale": self.locale,
                "timezone": self.timezone_name,
                "generated_at": generated_at.isoformat(),
                "title": "TestPsico - Informe sintetico",
                "author": "TestPsico",
            },
        )


PdfRenderer = ReportLabRenderer
DeterministicPdfRenderer = ReportLabRenderer
