#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./deploy.sh <dev|prod>

Builds the Docker Compose stack for the selected environment, applies Alembic
migrations inside the backend container, and runs smoke checks against the
served app before exiting successfully.
EOF
}

if [[ $# -ne 1 ]]; then
  usage >&2
  exit 1
fi

ENVIRONMENT="$1"

case "$ENVIRONMENT" in
  dev)
    ENV_FILE=".env"
    PROJECT_NAME="ucmnews-dev"
    HOST_PORT="9290"
    PUBLIC_URL="https://ucmnews-dev.insight.uidaho.edu"
    ;;
  prod)
    ENV_FILE=".env.prod"
    PROJECT_NAME="ucmnews-prod"
    HOST_PORT="9280"
    PUBLIC_URL="https://ucmnews.insight.uidaho.edu"
    ;;
  *)
    usage >&2
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Expected environment file '$ENV_FILE' in $SCRIPT_DIR" >&2
  exit 1
fi

COMPOSE=(docker compose --env-file "$ENV_FILE" -p "$PROJECT_NAME")
BASE_URL="http://127.0.0.1:${HOST_PORT}"

env_file_value() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    return 0
  fi
  line="${line#*=}"
  line="${line%\"}"
  line="${line#\"}"
  line="${line%\'}"
  line="${line#\'}"
  printf '%s' "$line"
}

retry() {
  local attempts="$1"
  shift
  local delay_seconds="$1"
  shift

  local attempt=1
  until "$@"; do
    if (( attempt >= attempts )); then
      return 1
    fi
    sleep "$delay_seconds"
    ((attempt++))
  done
}

smoke_check() {
  local label="$1"
  local url="$2"

  echo "Checking ${label}: ${url}"
  retry 12 2 curl -fsS "$url" >/dev/null
}

smoke_check_trusted_role() {
  local label="$1"
  local url="$2"
  local role
  local secret

  role="$(env_file_value TRUSTED_ROLE_HEADER_ROLE)"
  secret="$(env_file_value TRUSTED_ROLE_HEADER_SECRET)"

  echo "Checking ${label}: ${url}"
  if [[ -n "$role" && -n "$secret" ]]; then
    retry 12 2 curl -fsS \
      -H "X-Trusted-User-Role: ${role}" \
      -H "X-Trusted-Auth-Secret: ${secret}" \
      "$url" >/dev/null
    return
  fi

  echo "Skipping ${label}: TRUSTED_ROLE_HEADER_ROLE/SECRET not configured"
}

echo "Deploying ${ENVIRONMENT} with project ${PROJECT_NAME}"
"${COMPOSE[@]}" up -d --build

# Migrations and seeding run automatically in the backend container entrypoint.
# See backend/docker-entrypoint.sh.

echo "Container status"
"${COMPOSE[@]}" ps

echo "Running smoke checks"
smoke_check "frontend root" "${BASE_URL}/"
smoke_check "SPA route" "${BASE_URL}/dashboard"
smoke_check "health API" "${BASE_URL}/api/v1/health"
smoke_check "settings API" "${BASE_URL}/api/v1/settings/ai"
smoke_check_trusted_role "submissions API" "${BASE_URL}/api/v1/submissions/?limit=1"

echo "Deployment checks passed for ${ENVIRONMENT}"
echo "Public URL: ${PUBLIC_URL}"
