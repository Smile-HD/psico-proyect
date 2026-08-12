"""Pure, deterministic composition of professional report documents.

The repository and service layers adapt persisted F4/F5 rows into the frozen
``ReportInput`` boundary. This module consumes only those snapshots and plain
template data: it performs no database access, I/O, clock reads, network work,
engine invocation, or dynamic template evaluation.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


_MISSING = object()
_PLACEHOLDER_NAME = re.compile(r"[a-z][a-z0-9_]*\Z")
_PLACEHOLDER = re.compile(r"\{\{\s*([a-z][a-z0-9_]*)\s*\}\}")
ALLOWED_TEMPLATE_PLACEHOLDERS = frozenset(
    {
        "session_id",
        "scores",
        "overall",
        "recommendations",
        "norm_note",
        "disclaimer",
    }
)
SECTION_ORDER = ("scores", "overall", "recommendations", "norm_note", "disclaimer")


class ReportDomainError(ValueError):
    """A typed failure caused by invalid report composition input."""

    def __init__(self, message: str, *, path: str | None = None) -> None:
        self.message = message
        self.path = path
        self.errors = (
            [{"path": path, "message": message}] if path else [{"message": message}]
        )
        super().__init__(f"{path}: {message}" if path else message)


class ReportIntegrityError(ReportDomainError):
    """A required persisted snapshot field is missing or malformed."""


class TemplateError(ReportDomainError):
    """A report template is malformed or requests an unsupported value."""


class TemplateSyntaxError(TemplateError):
    """A template contains malformed placeholder syntax."""


class UnknownPlaceholderError(TemplateError):
    """A template requests a placeholder outside the ratified allow-list."""


class MissingPlaceholderError(TemplateError):
    """A referenced allow-listed placeholder has no supplied value."""


def _field(source: Any, *names: str, default: Any = _MISSING) -> Any:
    """Read a field from either a mapping snapshot or a plain object."""

    for name in names:
        if isinstance(source, Mapping) and name in source:
            return source[name]
        if not isinstance(source, Mapping) and hasattr(source, name):
            return getattr(source, name)
    return default


def _required(source: Any, *names: str, path: str) -> Any:
    value = _field(source, *names)
    if value is _MISSING or value is None:
        raise ReportIntegrityError("field is required", path=path)
    return value


def _text(value: Any, path: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise ReportIntegrityError("value must be a non-empty string", path=path)
    return value


def _integer(value: Any, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ReportIntegrityError("value must be an integer", path=path)
    return value


def _number(value: Any, path: str) -> int | float | Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ReportIntegrityError("value must be numeric", path=path)
    if isinstance(value, float) and not math.isfinite(value):
        raise ReportIntegrityError("value must be finite", path=path)
    if isinstance(value, Decimal) and not value.is_finite():
        raise ReportIntegrityError("value must be finite", path=path)
    return value


def _fit_score(value: Any, path: str) -> Any:
    """Validate a persisted fit score while retaining its snapshot type."""

    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal, str)):
        raise ReportIntegrityError("fit_score must be numeric", path=path)
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise ReportIntegrityError("fit_score must be numeric", path=path) from error
    if not decimal.is_finite():
        raise ReportIntegrityError("fit_score must be finite", path=path)
    return value


@dataclass(frozen=True)
class ReportInput:
    """Pinned, immutable inputs for one deterministic report composition.

    ``f4_snapshot``/``recommendation_snapshot`` and ``template`` are accepted
    as keyword aliases because repository adapters naturally use those names;
    the stored fields remain canonical and frozen.
    """

    session_id: Any
    score_run_id: Any
    score_snapshot: Any
    f5_snapshot: Any
    template_id: Any
    template_version_no: int | None
    template_body: str | None
    norm_note: str | None = None
    disclaimer: str | None = None

    def __init__(
        self,
        session_id: Any,
        score_run_id: Any,
        score_snapshot: Any = None,
        f5_snapshot: Any = None,
        template_id: Any = None,
        template_version_no: int | None = None,
        template_body: str | None = None,
        *,
        f4_snapshot: Any = None,
        recommendation_snapshot: Any = None,
        norm_note: str | None = None,
        disclaimer: str | None = None,
        template_version: int | None = None,
        template: Any = None,
    ) -> None:
        if score_snapshot is not None and f4_snapshot is not None and score_snapshot != f4_snapshot:
            raise ReportIntegrityError("conflicting score snapshots", path="score_snapshot")
        if f5_snapshot is not None and recommendation_snapshot is not None and f5_snapshot != recommendation_snapshot:
            raise ReportIntegrityError(
                "conflicting recommendation snapshots", path="f5_snapshot"
            )
        if score_snapshot is None:
            score_snapshot = f4_snapshot
        if f5_snapshot is None:
            f5_snapshot = recommendation_snapshot
        if template_version_no is not None and template_version is not None and template_version_no != template_version:
            raise ReportIntegrityError(
                "conflicting template versions", path="template_version_no"
            )
        if template_version_no is None:
            template_version_no = template_version

        if template is not None:
            if isinstance(template, Mapping) or hasattr(template, "__dict__"):
                candidate_id = _field(template, "template_id", "id")
                candidate_version = _field(template, "template_version_no", "version_no", "version")
                candidate_body = _field(template, "template_body", "body")
                if template_id is None:
                    template_id = None if candidate_id is _MISSING else candidate_id
                if template_version_no is None:
                    template_version_no = None if candidate_version is _MISSING else candidate_version
                if template_body is None:
                    template_body = None if candidate_body is _MISSING else candidate_body
            elif template_body is None and isinstance(template, str):
                template_body = template

        object.__setattr__(self, "session_id", session_id)
        object.__setattr__(self, "score_run_id", score_run_id)
        object.__setattr__(self, "score_snapshot", score_snapshot)
        object.__setattr__(self, "f5_snapshot", f5_snapshot)
        object.__setattr__(self, "template_id", template_id)
        object.__setattr__(self, "template_version_no", template_version_no)
        object.__setattr__(self, "template_body", template_body)
        object.__setattr__(self, "norm_note", norm_note)
        object.__setattr__(self, "disclaimer", disclaimer)

    @property
    def f4_snapshot(self) -> Any:
        return self.score_snapshot

    @property
    def recommendation_snapshot(self) -> Any:
        return self.f5_snapshot

    @property
    def template_version(self) -> int | None:
        return self.template_version_no


@dataclass(frozen=True)
class ScaleScore:
    """Allowed per-scale score fields copied from the pinned F4 snapshot."""

    label: str
    raw: int
    z: int | float | Decimal
    percentile: int
    t_score: int
    eneatype: int

@dataclass(frozen=True)
class OverallScore:
    """Allowed overall score fields copied from the pinned F4 snapshot."""

    raw: int
    percentile: int
    t_score: int
    eneatype: int

@dataclass(frozen=True)
class ProgramRecommendation:
    """Allowed per-program fields copied from the pinned F5 snapshot."""

    program_name: str
    fit_score: Any
    justification: str

@dataclass(frozen=True)
class ReportSection:
    """One fixed report section; its content is already safely projected."""

    key: str
    content: Any

    @property
    def kind(self) -> str:
        return self.key

@dataclass(frozen=True)
class ReportDocument:
    """Immutable logical document with fixed section order and source pins."""

    session_id: Any
    score_run_id: Any
    template_id: Any
    template_version_no: int
    sections: tuple[ReportSection, ...]
    rendered_template: str

    @property
    def scores(self) -> tuple[ScaleScore, ...]:
        return self.sections[0].content

    @property
    def overall(self) -> OverallScore:
        return self.sections[1].content

    @property
    def recommendations(self) -> tuple[ProgramRecommendation, ...]:
        return self.sections[2].content

    @property
    def norm_note(self) -> str:
        return self.sections[3].content

    @property
    def disclaimer(self) -> str:
        return self.sections[4].content

    @property
    def template_text(self) -> str:
        return self.rendered_template


@dataclass(frozen=True)
class ParsedTemplate:
    """Validated data template with literal, allow-listed substitutions only."""

    body: str
    placeholders: tuple[str, ...]

    def render(self, values: Mapping[str, Any] | Any) -> str:
        def replacement(match: re.Match[str]) -> str:
            name = match.group(1)
            value = _field(values, name)
            if value is _MISSING or value is None:
                raise MissingPlaceholderError(
                    "placeholder value is required", path=f"template.{name}"
                )
            return str(value)

        return _PLACEHOLDER.sub(replacement, self.body)


def parse_template(template_body: str) -> ParsedTemplate:
    """Validate a template and return its literal placeholder sequence.

    Only ``{{name}}`` placeholders from ``ALLOWED_TEMPLATE_PLACEHOLDERS`` are
    recognized. Everything else is data or a typed template error; no Python
    expression is parsed or evaluated.
    """

    if not isinstance(template_body, str) or not template_body.strip():
        raise TemplateSyntaxError("template body must be a non-empty string", path="template.body")
    if "{%" in template_body or "{#" in template_body:
        raise TemplateSyntaxError("template directives are not supported", path="template.body")

    placeholders: list[str] = []
    cursor = 0
    while True:
        opening = template_body.find("{{", cursor)
        if opening < 0:
            if "}}" in template_body[cursor:]:
                raise TemplateSyntaxError("unmatched closing placeholder", path="template.body")
            break
        closing = template_body.find("}}", opening + 2)
        if closing < 0:
            raise TemplateSyntaxError("unclosed placeholder", path="template.body")
        raw_name = template_body[opening + 2 : closing].strip()
        if _PLACEHOLDER_NAME.fullmatch(raw_name) is None:
            raise UnknownPlaceholderError(
                f"unknown placeholder: {raw_name or '<empty>'}",
                path="template.body",
            )
        if raw_name not in ALLOWED_TEMPLATE_PLACEHOLDERS:
            raise UnknownPlaceholderError(
                f"unknown placeholder: {raw_name}", path="template.body"
            )
        placeholders.append(raw_name)
        cursor = closing + 2

    return ParsedTemplate(template_body, tuple(placeholders))


def render_template(template_body: str, values: Mapping[str, Any] | Any) -> str:
    """Render an allow-listed data template without evaluating its contents."""

    return parse_template(template_body).render(values)


parse_template_body = parse_template
render_report_template = render_template


def _snapshot_value(source: Any, name: str, default: Any = _MISSING) -> Any:
    value = _field(source, name)
    if value is not _MISSING:
        return value
    raw = _field(source, "raw")
    if raw is not _MISSING:
        value = _field(raw, name)
        if value is not _MISSING:
            return value
    return default


def _transformed(source: Any) -> Any:
    return _field(source, "transformed", default={})


def _normalize_scale(scale: Any, index: int) -> ScaleScore:
    path = f"score_snapshot.scales[{index}]"
    label = _text(_required(scale, "label", path=f"{path}.label"), f"{path}.label")
    raw = _integer(_required(scale, "raw", path=f"{path}.raw"), f"{path}.raw")
    direct = _field(scale, "direct")
    if direct is _MISSING:
        direct = _transformed(scale)
    transformed = _transformed(scale)
    z = _number(_required(direct, "z", path=f"{path}.direct.z"), f"{path}.direct.z")
    percentile = _integer(
        _required(transformed, "percentile", path=f"{path}.transformed.percentile"),
        f"{path}.transformed.percentile",
    )
    t_score = _integer(
        _required(transformed, "t_score", "t", path=f"{path}.transformed.t_score"),
        f"{path}.transformed.t_score",
    )
    eneatype = _integer(
        _required(transformed, "eneatype", path=f"{path}.transformed.eneatype"),
        f"{path}.transformed.eneatype",
    )
    return ScaleScore(label, raw, z, percentile, t_score, eneatype)


def _normalize_overall(overall: Any) -> OverallScore:
    raw = _integer(_required(overall, "raw", path="score_snapshot.overall.raw"), "score_snapshot.overall.raw")
    transformed = _transformed(overall)
    percentile = _integer(
        _required(transformed, "percentile", path="score_snapshot.overall.transformed.percentile"),
        "score_snapshot.overall.transformed.percentile",
    )
    t_score = _integer(
        _required(transformed, "t_score", "t", path="score_snapshot.overall.transformed.t_score"),
        "score_snapshot.overall.transformed.t_score",
    )
    eneatype = _integer(
        _required(transformed, "eneatype", path="score_snapshot.overall.transformed.eneatype"),
        "score_snapshot.overall.transformed.eneatype",
    )
    return OverallScore(raw, percentile, t_score, eneatype)


def _normalize_recommendation(item: Any, index: int) -> ProgramRecommendation:
    path = f"f5_snapshot.items[{index}]"
    program_name = _text(
        _required(item, "program_name", "name", path=f"{path}.program_name"),
        f"{path}.program_name",
    )
    fit_score = _fit_score(
        _required(item, "fit_score", "fit", path=f"{path}.fit_score"),
        f"{path}.fit_score",
    )
    justification = _text(
        _required(item, "justification", path=f"{path}.justification"),
        f"{path}.justification",
        allow_empty=True,
    )
    return ProgramRecommendation(program_name, fit_score, justification)


def _format_scores(scores: tuple[ScaleScore, ...]) -> str:
    return "\n".join(
        f"{score.label}: raw={score.raw}; z={score.z}; percentile={score.percentile}; "
        f"T={score.t_score}; eneatype={score.eneatype}"
        for score in scores
    )


def _format_overall(overall: OverallScore) -> str:
    return (
        f"raw={overall.raw}; percentile={overall.percentile}; T={overall.t_score}; "
        f"eneatype={overall.eneatype}"
    )


def _format_recommendations(recommendations: tuple[ProgramRecommendation, ...]) -> str:
    return "\n".join(
        f"{recommendation.program_name}: fit={recommendation.fit_score}; "
        f"{recommendation.justification}"
        for recommendation in recommendations
    )


def compose_report(report_input: ReportInput) -> ReportDocument:
    """Compose one deterministic document from pinned, persisted snapshots."""

    if not isinstance(report_input, ReportInput):
        raise ReportIntegrityError("ReportInput is required", path="report_input")
    session_id = _required(report_input, "session_id", path="session_id")
    score_run_id = _required(report_input, "score_run_id", path="score_run_id")
    template_id = _required(report_input, "template_id", path="template_id")
    template_version = _integer(
        _required(report_input, "template_version_no", path="template_version_no"),
        "template_version_no",
    )
    if template_version < 1:
        raise ReportIntegrityError("template version must be positive", path="template_version_no")
    template_body = _text(
        _required(report_input, "template_body", path="template_body"),
        "template_body",
    )

    score_snapshot = _required(report_input, "score_snapshot", path="score_snapshot")
    raw_scales = _snapshot_value(score_snapshot, "scales")
    if raw_scales is _MISSING or isinstance(raw_scales, (str, bytes)):
        raise ReportIntegrityError("scales must be iterable", path="score_snapshot.scales")
    try:
        scales = tuple(_normalize_scale(scale, index) for index, scale in enumerate(raw_scales))
    except TypeError as error:
        raise ReportIntegrityError("scales must be iterable", path="score_snapshot.scales") from error
    if not scales:
        raise ReportIntegrityError("at least one scale is required", path="score_snapshot.scales")

    overall = _snapshot_value(score_snapshot, "overall")
    if overall is _MISSING or overall is None:
        raise ReportIntegrityError("field is required", path="score_snapshot.overall")
    normalized_overall = _normalize_overall(overall)

    norm_note = report_input.norm_note
    if norm_note is None:
        norm_note = _snapshot_value(score_snapshot, "norm_note")
    norm_note = _text(norm_note, "norm_note")

    f5_snapshot = _required(report_input, "f5_snapshot", path="f5_snapshot")
    raw_items = _field(f5_snapshot, "items", "recommendations")
    if raw_items is _MISSING or isinstance(raw_items, (str, bytes)):
        raise ReportIntegrityError("items must be iterable", path="f5_snapshot.items")
    try:
        recommendations = tuple(
            _normalize_recommendation(item, index)
            for index, item in enumerate(raw_items)
        )
    except TypeError as error:
        raise ReportIntegrityError("items must be iterable", path="f5_snapshot.items") from error

    disclaimer = report_input.disclaimer
    if disclaimer is None:
        disclaimer = _field(f5_snapshot, "disclaimer")
    disclaimer = _text(disclaimer, "disclaimer")

    parsed_template = parse_template(template_body)
    template_values = {
        "session_id": str(session_id),
        "scores": _format_scores(scales),
        "overall": _format_overall(normalized_overall),
        "recommendations": _format_recommendations(recommendations),
        "norm_note": norm_note,
        "disclaimer": disclaimer,
    }
    rendered_template = parsed_template.render(template_values)
    sections = (
        ReportSection("scores", scales),
        ReportSection("overall", normalized_overall),
        ReportSection("recommendations", recommendations),
        ReportSection("norm_note", norm_note),
        ReportSection("disclaimer", disclaimer),
    )
    return ReportDocument(
        session_id=session_id,
        score_run_id=score_run_id,
        template_id=template_id,
        template_version_no=template_version,
        sections=sections,
        rendered_template=rendered_template,
    )


compose = compose_report
build_report_document = compose_report
