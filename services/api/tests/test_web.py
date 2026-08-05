"""Web scaffold checks (F1, task 5.2).

These run WITHOUT Node/Docker: they assert the source contract of the web
slice (service-name URL, Spanish UI, friendly error handling) and the compose
wiring (web service depends on a healthy api). A Node-capable environment must
still build/run the app itself — documented as a Docker-only verification.
"""

import pathlib
import re

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[3]
WEB = ROOT / "apps" / "web"
COMPOSE = ROOT / "docker-compose.yml"

PAGE = (WEB / "app" / "page.tsx").read_text(encoding="utf-8")
LAYOUT = (WEB / "app" / "layout.tsx").read_text(encoding="utf-8")
PACKAGE = (WEB / "package.json").read_text(encoding="utf-8")


def test_web_scaffold_files_exist():
    expected = [
        "package.json",
        "next.config.mjs",
        "tsconfig.json",
        "Dockerfile",
        "app/layout.tsx",
        "app/page.tsx",
        "app/globals.css",
    ]
    for name in expected:
        assert (WEB / name).is_file(), f"missing web scaffold file: {name}"


def test_page_uses_compose_service_name():
    """The page must call the API over the internal network by service name."""
    assert re.search(r"http://api:\d+", PAGE), "expected API_BASE_URL default http://api:8000"
    assert "localhost:8000" not in PAGE, "host-port URL would bypass the compose network"


def test_page_is_spanish():
    for text in (
        "Estado del servicio",
        "Salud de la API",
        "No se pudo conectar",
        "Intente nuevamente más tarde",
        "Semilla (datos sintéticos)",
    ):
        assert text in PAGE, f"expected Spanish UI text: {text}"


def test_page_never_leaks_stack_trace():
    assert ".stack" not in PAGE
    assert "error.stack" not in PAGE
    # The error branch renders a fixed friendly message, never the exception
    # object or its message. React's error boundary keeps stack traces internal.
    assert 'error ? (' in PAGE
    assert "No se pudo conectar" in PAGE
    assert "err.message" not in PAGE
    assert "error.message" not in PAGE


def test_page_has_spanish_layout_lang():
    assert 'lang="es"' in LAYOUT


def test_package_declares_next_and_react():
    assert '"next"' in PACKAGE and '"react"' in PACKAGE


def test_compose_wires_web_service():
    compose = yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))
    web = compose["services"]["web"]
    assert web["build"]["context"] == "./apps/web"
    assert web["depends_on"]["api"]["condition"] == "service_healthy"
    assert web["environment"]["API_BASE_URL"].startswith("${API_BASE_URL:-http://api:")
    assert web["ports"][0].startswith("${WEB_PORT:-3000}")
    assert "healthcheck" in web
    assert compose["services"]["api"]["depends_on"]["db"]["condition"] == "service_healthy"
