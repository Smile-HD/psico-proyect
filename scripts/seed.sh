#!/usr/bin/env bash
# Seed synthetic data (idempotent; safe to run repeatedly).
# Use --reset to wipe seed-owned rows first, then re-seed.
set -euo pipefail

docker compose run --rm api python -m app.seed "$@"
