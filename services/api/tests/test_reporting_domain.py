"""Pure reporting-domain contracts for F6 slice 1."""

from __future__ import annotations

import copy
import inspect
from dataclasses import FrozenInstanceError

import pytest

from app.modules.reporting.domain import (
    MissingPlaceholderError,
    ReportInput,
    UnknownPlaceholderError,
    compose_report,
    parse_template,
    render_template,
)


NORM_NOTE = "Baremo de investigación para datos sintéticos; no es una norma real."
DISCLAIMER = (
    "Recomendaciones orientativas sobre datos sintéticos (research-only). "
    "No constituyen una norma UAGRM ni asesoramiento profesional."
)
TEMPLATE_BODY = (
    "Session {{session_id}}\n"
    "Scores {{scores}}\n"
    "Overall {{overall}}\n"
    "Recommendations {{recommendations}}\n"
    "Baremo {{norm_note}}\n"
    "Disclaimer {{disclaimer}}"
)


def _score_snapshot() -> dict[str, object]:
    return {
        "scales": [
            {
                "label": "Intereses",
                "raw": 14,
                "direct": {"z": 1.0},
                "transformed": {"percentile": 84, "t_score": 60, "eneatype": 6},
                "option_value": 5,
                "response_key": "answer-secret",
                "item_content": "Pregunta privada",
            },
            {
                "label": "Aptitud verbal",
                "raw": 11,
                "direct": {"z": 0.2},
                "transformed": {"percentile": 58, "t_score": 52, "eneatype": 5},
            },
        ],
        "overall": {
            "raw": 13,
            "transformed": {"percentile": 72, "t_score": 56, "eneatype": 6},
        },
        "norm_note": NORM_NOTE,
        "response_id": "response-secret",
        "secret": "do-not-render",
    }


def _f5_snapshot() -> dict[str, object]:
    return {
        "generated_at": "2026-08-11T12:00:00+00:00",
        "disclaimer": DISCLAIMER,
        "items": [
            {
                "program_id": "program-secret",
                "program_name": "Programa Uno",
                "program_code": "P1",
                "fit_score": "80.00",
                "justification": "Intereses ≥ 60 pct: cumple (84 pct)",
                "response_key": "response-secret",
                "option_id": "option-secret",
            }
        ],
        "rule_params": {"scale": "Intereses", "min_percentile": 60},
    }


def _report_input() -> ReportInput:
    return ReportInput(
        "session-1",
        "score-run-1",
        _score_snapshot(),
        _f5_snapshot(),
        "template-informe-basico",
        1,
        TEMPLATE_BODY,
    )


def test_report_composes_fixed_immutable_sections_from_pinned_snapshots() -> None:
    report_input = _report_input()
    before = copy.deepcopy(report_input)

    first = compose_report(report_input)
    second = compose_report(report_input)

    assert first == second
    assert report_input == before
    assert (first.session_id, first.score_run_id) == ("session-1", "score-run-1")
    assert (first.template_id, first.template_version_no) == (
        "template-informe-basico",
        1,
    )
    assert [section.key for section in first.sections] == [
        "scores",
        "overall",
        "recommendations",
        "norm_note",
        "disclaimer",
    ]
    assert first.sections[0].content[0].raw == 14
    assert first.sections[0].content[0].z == 1.0
    assert first.sections[0].content[0].percentile == 84
    assert first.sections[0].content[0].t_score == 60
    assert first.sections[0].content[0].eneatype == 6
    assert first.sections[1].content.raw == 13
    assert first.sections[2].content[0].program_name == "Programa Uno"
    assert first.sections[2].content[0].fit_score == "80.00"
    assert first.sections[3].content == NORM_NOTE
    assert first.sections[4].content == DISCLAIMER
    assert "option-secret" not in repr(first)
    assert "response-secret" not in repr(first)
    assert "Pregunta privada" not in repr(first)
    assert "do-not-render" not in repr(first)

    with pytest.raises(FrozenInstanceError):
        report_input.score_run_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        first.sections[0].content[0].raw = 99  # type: ignore[misc]


def test_report_preserves_outer_norm_note_when_score_run_snapshot_wraps_raw_payload() -> None:
    score_snapshot = _score_snapshot()
    wrapped_score_snapshot = {
        "raw": {
            "scales": score_snapshot["scales"],
            "overall": score_snapshot["overall"],
        },
        "norm_note": NORM_NOTE,
    }
    f5_snapshot = _f5_snapshot()
    f5_snapshot["recommendations"] = f5_snapshot.pop("items")
    report_input = ReportInput(
        session_id="session-wrapped",
        score_run_id="score-run-wrapped",
        score_snapshot=wrapped_score_snapshot,
        recommendation_snapshot=f5_snapshot,
        template_id="template-wrapped",
        template_version_no=1,
        template_body=TEMPLATE_BODY,
    )

    document = compose_report(report_input)

    assert document.norm_note == NORM_NOTE
    assert document.sections[2].content[0].program_name == "Programa Uno"


def test_template_parser_allows_only_literal_ratified_placeholders() -> None:
    values = {
        "session_id": "session-1",
        "scores": "scores-content",
        "overall": "overall-content",
        "recommendations": "recommendations-content",
        "norm_note": NORM_NOTE,
        "disclaimer": DISCLAIMER,
    }

    parsed = parse_template(TEMPLATE_BODY)
    rendered = parsed.render(values)

    assert parsed.placeholders == (
        "session_id",
        "scores",
        "overall",
        "recommendations",
        "norm_note",
        "disclaimer",
    )
    assert rendered == render_template(TEMPLATE_BODY, values)
    assert "scores-content" in rendered
    assert "overall-content" in rendered
    assert "recommendations-content" in rendered
    assert NORM_NOTE in rendered
    assert DISCLAIMER in rendered


def test_template_parser_rejects_unknown_and_missing_placeholders() -> None:
    with pytest.raises(UnknownPlaceholderError, match="unknown"):
        parse_template("{{scores}} {{option_values}}")

    with pytest.raises(UnknownPlaceholderError):
        parse_template("{{__import__('os').system('whoami')}}")

    with pytest.raises(MissingPlaceholderError, match="norm_note"):
        render_template("{{scores}} {{norm_note}}", {"scores": "safe"})


def test_reporting_domain_has_no_db_api_io_clock_or_dynamic_execution_dependencies() -> None:
    import app.modules.reporting.domain as domain

    imported = {
        getattr(value, "__name__", "").split(".", 1)[0]
        for value in vars(domain).values()
    }
    assert imported.isdisjoint(
        {"sqlalchemy", "psycopg", "fastapi", "pathlib", "datetime", "time", "random"}
    )
    source = inspect.getsource(domain)
    assert "eval(" not in source
    assert "exec(" not in source
    assert "__import__(" not in source
