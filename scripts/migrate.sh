#!/usr/bin/env bash
# Apply schema migrations (idempotent: running at head is a no-op).
set -euo pipefail

docker compose run --rm api alembic upgrade head
