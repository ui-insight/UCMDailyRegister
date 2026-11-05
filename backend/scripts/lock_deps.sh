#!/usr/bin/env sh
# Regenerate the backend lock files from pyproject.toml.
#
#   requirements.lock      runtime + postgres extra (what the Docker image installs)
#   requirements-dev.lock  runtime + postgres + dev extras (what CI installs)
#
# Run from backend/ after changing dependencies in pyproject.toml:
#   pip install uv==0.9.5 && ./scripts/lock_deps.sh
# Existing pins are kept unless pyproject.toml forces a change. To move every
# package to its newest allowed version, pass --upgrade; for one package,
# --upgrade-package NAME.
#
# --check regenerates into a temporary copy and fails if the committed locks
# are out of date with pyproject.toml (used by CI).
set -eu
cd "$(dirname "$0")/.."

compile() {
  out="$1"; shift
  UV_CUSTOM_COMPILE_COMMAND="./scripts/lock_deps.sh" uv pip compile pyproject.toml \
    --universal --python-version 3.11 --generate-hashes --quiet \
    --output-file "$out" "$@"
}

if [ "${1:-}" = "--check" ]; then
  here=$(pwd)
  tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
  cp pyproject.toml requirements.lock requirements-dev.lock "$tmp/"
  (
    cd "$tmp"
    compile requirements.lock --extra postgres
    compile requirements-dev.lock --extra postgres --extra dev --constraint requirements.lock
  )
  status=0
  for f in requirements.lock requirements-dev.lock; do
    if ! diff -u "$here/$f" "$tmp/$f"; then status=1; fi
  done
  if [ "$status" -ne 0 ]; then
    echo "Lock files are out of date with pyproject.toml. Run ./scripts/lock_deps.sh and commit the result." >&2
  fi
  exit "$status"
fi

compile requirements.lock --extra postgres "$@"
compile requirements-dev.lock --extra postgres --extra dev --constraint requirements.lock "$@"
