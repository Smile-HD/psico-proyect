# Seed synthetic data (idempotent; safe to run repeatedly).
# Use -reset to wipe seed-owned rows first, then re-seed.
$ErrorActionPreference = 'Stop'

docker compose run --rm api python -m app.seed @args
