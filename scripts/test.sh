#!/usr/bin/env bash
# Run the pytest suite inside the api container.
set -euo pipefail

docker compose run --rm api pytest "$@"
