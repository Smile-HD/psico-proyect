#!/usr/bin/env bash
# Build and start the dev stack (api + db + redis + web).
set -euo pipefail

docker compose up -d --build
