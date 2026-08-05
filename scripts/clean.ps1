# Tear down the dev stack and remove volumes (full clean slate).
$ErrorActionPreference = 'Stop'

docker compose down -v
