#!/usr/bin/env bash
# Create .env from .env.example when missing (dev-only defaults).
set -euo pipefail

if [ -f .env ]; then
  echo ".env already exists; leaving it untouched."
else
  cp .env.example .env
  echo "Created .env from .env.example (dev-only defaults — override before real use)."
fi
