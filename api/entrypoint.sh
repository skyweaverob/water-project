#!/bin/sh
# API entrypoint for Railway.
# Idempotent schema bootstrap on every boot, then exec uvicorn so signals propagate.
set -e

echo "[entrypoint] provisioning schema (idempotent)..."
python -m app.scripts.create_all || {
  echo "[entrypoint] WARNING: create_all failed (likely missing pgvector); continuing"
}

echo "[entrypoint] starting uvicorn on port ${PORT:-8000}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
