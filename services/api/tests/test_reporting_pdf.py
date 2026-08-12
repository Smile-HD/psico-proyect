"""Normalized PDF renderer contracts for the F6 reporting boundary."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from app.modules.reporting.domain import ReportInput, compose_report
from app.modules.reporting.pdf_renderer import ReportLabRenderer

import pytest
from pypdf import PdfReader


NORM_NOTE = "Baremo exclusivo para investigación sintética."
DISCLAIMER = "Aviso F5 exclusivo: orientación sintética y no profesional."
LEAK_MARKERS = (
    "option-value-secret",
    "response-key-secret",
    "mapping-1-5-secret",
    "item-content-secret",
    "secret-token",
    "D:\\internal\\report.pdf",
)


def _document():
    return compose_report(
        ReportInput(
            session_id="session-pdf-1",
            score_run_id="score-run-pdf-1",
            score_snapshot={
                "scales": [
                    {
                        "label": "Intereses",
                        "raw": 14,
                        "direct": {"z": 1.0},
                        "transformed": {
                            "percentile": 84,
                            "t_score": 60,
                            "eneatype": 6,
                        },
                        "option_value": LEAK_MARKERS[0],
                        "response_key": LEAK_MARKERS[1],
                        "item_content": LEAK_MARKERS[3],
                    },
                    {
                        "label": "Aptitud verbal",
                        "raw": 11,
                        "direct": {"z": 0.2},
                        "transformed": {
                            "percentile": 58,
                            "t_score": 52,
                            "eneatype": 5,
                        },
                    },
                ],
                "overall": {
                    "raw": 13,
                    "transformed": {
                        "percentile": 72,
                        "t_score": 56,
                        "eneatype": 6,
                    },
                },
                "norm_note": NORM_NOTE,
                "secret": LEAK_MARKERS[4],
            },
            f5_snapshot={
                "items": [
                    {
                        "program_name": "Programa Uno",
                        "fit_score": "80.00",
                        "justification": "Perfil sintético compatible.",
                        "option_id": LEAK_MARKERS[0],
                        "response_key": LEAK_MARKERS[1],
                    }
                ],
                "disclaimer": DISCLAIMER,
                "rule_params": LEAK_MARKERS[2],
            },
            template_id="template-pdf-1",
            template_version_no=1,
            template_body=(
                "{{session_id}} {{scores}} {{overall}} {{recommendations}} "
                "{{norm_note}} {{disclaimer}}"
            ),
        )
    )


def _font_names(reader: PdfReader) -> tuple[tuple[str, bool], ...]:
    fonts: list[tuple[str, bool]] = []
    for page in reader.pages:
        resources = page.get("/Resources")
        if not resources:
            continue
        font_dictionary = resources.get("/Font")
        if not font_dictionary:
            continue
        for font_reference in font_dictionary.values():
            font = font_reference.get_object()
            names = [str(font.get("/BaseFont", ""))]
            descriptors = []
            descriptor = font.get("/FontDescriptor")
            if descriptor:
                descriptors.append(descriptor.get_object())
            for descendant_reference in font.get("/DescendantFonts", []):
                descendant = descendant_reference.get_object()
                names.append(str(descendant.get("/BaseFont", "")))
                descendant_descriptor = descendant.get("/FontDescriptor")
                if descendant_descriptor:
                    descriptors.append(descendant_descriptor.get_object())
            embedded = any("/FontFile2" in descriptor for descriptor in descriptors)
            fonts.extend((name, embedded) for name in names)
    return tuple(fonts)


def _normalized_pdf(payload: bytes) -> dict[str, object]:
    reader = PdfReader(BytesIO(payload))
    pages = []
    for page in reader.pages:
        box = page.mediabox
        pages.append(
            {
                "size": tuple(round(float(value), 2) for value in box),
                "text": page.extract_text() or "",
            }
        )
    metadata = {
        str(key): str(value)
        for key, value in (reader.metadata or {}).items()
        if str(key) not in {"/CreationDate", "/ModDate"}
    }
    return {
        "pages": pages,
        "metadata": metadata,
        "fonts": _font_names(reader),
    }


def test_renderer_is_normalized_deterministic_and_embeds_spanish_dejavu_font() -> None:
    fixed_clock = lambda: datetime(2026, 8, 11, 12, 30, tzinfo=timezone.utc)
    renderer = ReportLabRenderer(
        locale="es",
        timezone=ZoneInfo("America/La_Paz"),
        clock=fixed_clock,
    )

    first = renderer.render(_document())
    second = renderer.render(_document())

    assert first.payload.startswith(b"%PDF-")
    assert first.media_type == "application/pdf"
    assert first.renderer_version
    assert first.metadata["locale"] == "es"
    assert first.metadata["timezone"] == "America/La_Paz"
    assert first.metadata["generated_at"] == "2026-08-11T08:30:00-04:00"
    reader = PdfReader(BytesIO(first.payload))
    assert str(reader.metadata["/CreationDate"]) == "D:20260811083000-04'00'"
    assert _normalized_pdf(first.payload) == _normalized_pdf(second.payload)

    normalized = _normalized_pdf(first.payload)
    text = "\n".join(page["text"] for page in normalized["pages"])
    assert len(normalized["pages"]) >= 1
    assert "Puntuaciones por escala" in text
    assert "Intereses" in text
    assert "Puntuación general" in text
    assert "Recomendaciones por programa" in text
    assert "Baremo" in text
    assert "Descargo de responsabilidad" in text
    assert NORM_NOTE in text
    assert DISCLAIMER in text

    baremo_start = text.index("Baremo")
    disclaimer_start = text.index("Descargo de responsabilidad")
    assert NORM_NOTE in text[baremo_start:disclaimer_start]
    assert DISCLAIMER not in text[baremo_start:disclaimer_start]
    assert DISCLAIMER in text[disclaimer_start:]
    assert NORM_NOTE not in text[disclaimer_start:]

    font_names = normalized["fonts"]
    assert any("DejaVuSans" in name and embedded for name, embedded in font_names)
    metadata_text = " ".join(normalized["metadata"].values())
    for marker in LEAK_MARKERS:
        assert marker not in text
        assert marker not in metadata_text
    assert "reportlab" not in metadata_text.lower()
    assert "pdf_renderer" not in metadata_text.lower()
    assert "/app" not in metadata_text
    assert "D:\\" not in metadata_text


def test_renderer_uses_injected_clock_and_rejects_unsupported_locale() -> None:
    renderer = ReportLabRenderer(
        locale="es",
        timezone=timezone.utc,
        clock=lambda: datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
    )

    result = renderer.render(_document())

    assert result.metadata["generated_at"] == "2030-01-02T03:04:05+00:00"
    assert result.metadata["timezone"] == "UTC"
    with pytest.raises(ValueError, match="locale"):
        ReportLabRenderer(locale="en")


def test_renderer_default_font_asset_is_inside_reporting_module() -> None:
    asset = Path(__file__).parents[1] / "app" / "modules" / "reporting" / "fonts" / "DejaVuSans.ttf"

    assert asset.is_file()
    assert asset.stat().st_size > 100_000
