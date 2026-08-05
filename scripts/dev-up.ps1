# Build and start the dev stack (api + db + redis + web).
$ErrorActionPreference = 'Stop'

docker compose up -d --build
