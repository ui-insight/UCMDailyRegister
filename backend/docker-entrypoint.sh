#!/usr/bin/env bash
set -euo pipefail

# When starting the server, run migrations and seed reference data first.
# Other commands (shell, one-off python, alembic revision, etc.) run without
# the startup preamble.
if [[ "${1:-}" == "uvicorn" ]]; then
  echo "[entrypoint] alembic upgrade head"
  alembic upgrade head

  echo "[entrypoint] seeding reference data"
  python -m app.db.seed

  echo "[entrypoint] starting server"
fi

exec "$@"
