#!/usr/bin/env bash
# Run the pytest suite inside the api container.
# The repo is mounted read-only at /repo so contract tests (test_scripts,
# test_web) can inspect docker-compose.yml, scripts/, apps/web, and .env.example.
set -euo pipefail

docker compose run --rm -v "${PWD}:/repo:ro" api pytest /repo/services/api/tests "$@"
