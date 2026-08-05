# Apply schema migrations (idempotent: running at head is a no-op).
$ErrorActionPreference = 'Stop'

docker compose run --rm api alembic upgrade head
