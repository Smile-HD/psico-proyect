#!/usr/bin/env bash
# Tear down the dev stack and remove volumes (full clean slate).
set -euo pipefail

docker compose down -v
