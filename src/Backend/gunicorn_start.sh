#!/usr/bin/env bash
# Production entry: Gunicorn + Uvicorn workers. Reads repo-root .env then binds HOST:PORT (defaults 0.0.0.0:8001).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/../.." && pwd)"
cd "$DIR"
if [[ -f "$ROOT/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8001}"
export WEB_CONCURRENCY="${WEB_CONCURRENCY:-2}"
exec gunicorn main:app \
  -k uvicorn.workers.UvicornWorker \
  -w "${WEB_CONCURRENCY}" \
  -b "${HOST}:${PORT}"
