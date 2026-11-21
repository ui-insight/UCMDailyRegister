#!/usr/bin/env bash
# Scheduled recovery point for one UCM News environment on the shared VM.
# See docs/backup-and-recovery.md.
#
# Usage:
#   scripts/backup.sh <prod|dev>          # take and verify one recovery point
#   scripts/backup.sh <prod|dev> --check  # exit 1 if the last success is too old
#
# Each run writes a new directory that is never reused:
#   ~/backups/ucmnews-<env>/scheduled/<UTC stamp>/
#     database.dump   pg_dump custom format, checked with pg_restore --list
#     uploads.tgz     the uploads Docker volume
#     MANIFEST.txt    revision, release, sizes and SHA-256 checksums
# and updates last-success (or last-failure) in ~/backups/ucmnews-<env>/.
#
# Encryption: when BACKUP_GPG_RECIPIENT names a public key in the devops
# keyring (fingerprint), the verified dump and archive are encrypted to it as
# database.dump.gpg and uploads.tgz.gpg and the plaintext files are removed.
# Only the PUBLIC key lives on this server; the private key that a restore
# needs is held off-server (docs/backup-and-recovery.md). It can be set in
# ~/.config/ucmnews-backup.env so cron picks it up. If the variable is set but
# the key is missing or encryption fails, the run fails rather than leaving
# plaintext behind.
#
# The database is dumped before the uploads are archived, so every image the
# dump references is already on disk when the archive is taken. pg_dump runs
# inside the insight-db container so it matches the server version.
#
# Off-host copy: when BACKUP_OFFHOST_HOST (an ssh destination such as
# backup@other-iids-host) and BACKUP_OFFHOST_DIR are set, each verified recovery
# point is copied there with rsync over ssh (key auth, BatchMode) to
# <dir>/ucmnews-<env>/scheduled/<stamp>/, and the remote SHA-256 checksums are
# compared with the local ones. Plaintext recovery points are not copied unless
# BACKUP_OFFHOST_ALLOW_PLAINTEXT=1 is set as a recorded decision, because the
# copy then carries readable personal information to a second host. A failed
# copy keeps the local recovery point, writes last-offhost-failure and exits 3.
#
# Nothing is pruned: backup expiry is pending Data Owner approval
# (docs/governance/decisions.md). Environment files are not copied here; they
# hold secrets and need their own controlled, encrypted backup.

set -euo pipefail
umask 077

ENV_NAME="${1:-}"
MODE="${2:-}"
case "$ENV_NAME" in
  prod) DB_NAME="ucm_newsletter";     PROJECT="ucmnews-prod" ;;
  dev)  DB_NAME="ucm_newsletter_dev"; PROJECT="ucmnews-dev" ;;
  *) echo "Usage: backup.sh <prod|dev> [--check]" >&2; exit 2 ;;
esac

VOLUME="${PROJECT}_uploads"
BACKEND="${PROJECT}-backend-1"
DB_CONTAINER="${DB_CONTAINER:-insight-db}"
BACKUP_ROOT="${BACKUP_ROOT:-$HOME/backups/ucmnews-$ENV_NAME}"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-26}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Optional settings file for cron (BACKUP_GPG_RECIPIENT=<fingerprint>).
CONFIG_FILE="${BACKUP_CONFIG:-$HOME/.config/ucmnews-backup.env}"
if [[ -f "$CONFIG_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
fi
GPG_RECIPIENT="${BACKUP_GPG_RECIPIENT:-}"
OFFHOST_HOST="${BACKUP_OFFHOST_HOST:-}"
OFFHOST_DIR="${BACKUP_OFFHOST_DIR:-}"
OFFHOST_ALLOW_PLAINTEXT="${BACKUP_OFFHOST_ALLOW_PLAINTEXT:-0}"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=20)
if [[ -n "$OFFHOST_HOST" && -z "$OFFHOST_DIR" ]] || [[ -z "$OFFHOST_HOST" && -n "$OFFHOST_DIR" ]]; then
  echo "Set both BACKUP_OFFHOST_HOST and BACKUP_OFFHOST_DIR, or neither" >&2
  exit 2
fi

mkdir -p "$BACKUP_ROOT/scheduled"
chmod 700 "$BACKUP_ROOT" "$BACKUP_ROOT/scheduled"

if [[ "$MODE" == "--check" ]]; then
  marker="$BACKUP_ROOT/last-success"
  if [[ ! -f "$marker" ]]; then
    echo "NO BACKUP: $marker does not exist" >&2
    exit 1
  fi
  age_s=$(( $(date +%s) - $(stat -c %Y "$marker") ))
  if (( age_s > MAX_AGE_HOURS * 3600 )); then
    echo "STALE BACKUP: last success $((age_s / 3600))h ago" >&2
    exit 1
  fi
  echo "OK: last success $((age_s / 3600))h ago"
  cat "$marker"
  if [[ -n "$OFFHOST_HOST" ]]; then
    off="$BACKUP_ROOT/last-offhost-success"
    if [[ ! -f "$off" ]]; then
      echo "NO OFF-HOST COPY: $off does not exist" >&2
      exit 1
    fi
    off_age_s=$(( $(date +%s) - $(stat -c %Y "$off") ))
    if (( off_age_s > MAX_AGE_HOURS * 3600 )); then
      echo "STALE OFF-HOST COPY: last success $((off_age_s / 3600))h ago" >&2
      exit 1
    fi
    echo "OK: last off-host copy $((off_age_s / 3600))h ago"
    cat "$off"
  fi
  exit 0
elif [[ -n "$MODE" ]]; then
  echo "Unknown option: $MODE" >&2
  exit 2
fi

# One run per environment at a time.
exec 9>"$BACKUP_ROOT/.lock"
flock -n 9 || { echo "Another $ENV_NAME backup is running" >&2; exit 1; }

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$BACKUP_ROOT/scheduled/$STAMP"
START=$(date +%s)

fail() {
  echo "$(date -u +%FT%TZ) FAILURE $ENV_NAME: $*" | tee "$BACKUP_ROOT/last-failure" >&2
  # An incomplete recovery point must not be mistaken for a good one.
  rm -rf -- "$DEST"
  exit 1
}

mkdir "$DEST" || fail "could not create $DEST"
echo "==> $(date -u +%FT%TZ) backup $ENV_NAME ($DB_NAME, $VOLUME) -> $DEST"

# 1. Database.
docker exec "$DB_CONTAINER" pg_dump -U postgres -Fc "$DB_NAME" > "$DEST/database.dump" \
  || fail "pg_dump $DB_NAME"
[[ -s "$DEST/database.dump" ]] || fail "empty dump"

# 2. The archive must be readable and carry the schema version. Capture the
# listing first: grep -q would close the pipe early and fail under pipefail.
TOC="$(docker exec -i "$DB_CONTAINER" pg_restore --list < "$DEST/database.dump")" \
  || fail "pg_restore --list could not read the dump"
grep -q "TABLE DATA public alembic_version" <<< "$TOC" \
  || fail "alembic_version missing from the dump"
TABLES="$(grep -c "TABLE DATA" <<< "$TOC" || true)"

# 3. Uploads, through a read-only mount.
docker run --rm -v "$VOLUME:/src:ro" alpine:3 tar czf - -C /src . > "$DEST/uploads.tgz" \
  || fail "tar of volume $VOLUME"
UPLOAD_FILES="$(tar tzf "$DEST/uploads.tgz" | grep -vc '/$' || true)"

# 4. Manifest. No secrets.
SCHEMA="$(docker exec "$DB_CONTAINER" psql -U postgres -d "$DB_NAME" -tAc \
  'select version_num from alembic_version')" || SCHEMA="unknown"
IMAGE="$(docker inspect "$BACKEND" --format '{{.Image}}' 2>/dev/null || echo unknown)"
CHECKOUT="$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
{
  echo "environment=$ENV_NAME"
  echo "created_utc=$STAMP"
  echo "database=$DB_NAME@$DB_CONTAINER"
  echo "alembic_revision=$SCHEMA"
  echo "table_data_entries=$TABLES"
  echo "backend_image=$IMAGE"
  echo "server_checkout=$CHECKOUT"
  echo "uploads_volume=$VOLUME"
  echo "uploads_files=$UPLOAD_FILES"
  (cd "$DEST" && sha256sum database.dump uploads.tgz) | sed 's/^/sha256 /'
} > "$DEST/MANIFEST.txt" || fail "write manifest"

# 5. Encrypt to the off-server key, then drop the plaintext. Checksums of the
# plaintext stay in the manifest so a decrypted restore can be verified.
ENCRYPTED="no"
if [[ -n "$GPG_RECIPIENT" ]]; then
  gpg --batch --list-keys "$GPG_RECIPIENT" > /dev/null 2>&1 \
    || fail "backup encryption key $GPG_RECIPIENT is not in the devops keyring"
  for f in database.dump uploads.tgz; do
    gpg --batch --yes --trust-model always --recipient "$GPG_RECIPIENT" \
      --output "$DEST/$f.gpg" --encrypt "$DEST/$f" \
      || fail "gpg encryption of $f"
    [[ -s "$DEST/$f.gpg" ]] || fail "empty $f.gpg"
    shred -u "$DEST/$f" 2>/dev/null || rm -f "$DEST/$f"
  done
  ENCRYPTED="gpg:$GPG_RECIPIENT"
  {
    echo "encrypted=$ENCRYPTED"
    (cd "$DEST" && sha256sum database.dump.gpg uploads.tgz.gpg) | sed 's/^/sha256 /'
  } >> "$DEST/MANIFEST.txt" || fail "write manifest"
else
  echo "encrypted=no" >> "$DEST/MANIFEST.txt" || fail "write manifest"
fi

ELAPSED=$(( $(date +%s) - START ))
{
  echo "$(date -u +%FT%TZ) SUCCESS $ENV_NAME in ${ELAPSED}s"
  echo "recovery_point=$DEST"
  echo "tables=$TABLES schema=$SCHEMA uploads_files=$UPLOAD_FILES"
  echo "encrypted=$ENCRYPTED"
} | tee "$BACKUP_ROOT/last-success"
rm -f "$BACKUP_ROOT/last-failure"

# 6. Off-host copy of the finished recovery point. The local point is already
# recorded as a success; a failed copy is reported separately.
if [[ -n "$OFFHOST_HOST" ]]; then
  offhost_fail() {
    echo "$(date -u +%FT%TZ) OFF-HOST FAILURE $ENV_NAME $STAMP: $*" \
      | tee "$BACKUP_ROOT/last-offhost-failure" >&2
    exit 3
  }
  if [[ "$ENCRYPTED" == "no" && "$OFFHOST_ALLOW_PLAINTEXT" != "1" ]]; then
    offhost_fail "recovery point is not encrypted; set BACKUP_GPG_RECIPIENT or BACKUP_OFFHOST_ALLOW_PLAINTEXT=1"
  fi
  REMOTE_DIR="$OFFHOST_DIR/ucmnews-$ENV_NAME/scheduled/$STAMP"
  # Paths are quoted for the remote shell; stamps and env names hold no spaces.
  ssh "${SSH_OPTS[@]}" "$OFFHOST_HOST" "umask 077 && mkdir -p '$REMOTE_DIR'" \
    || offhost_fail "could not create $OFFHOST_HOST:$REMOTE_DIR"
  rsync -a --chmod=D700,F600 -e "ssh ${SSH_OPTS[*]}" "$DEST/" "$OFFHOST_HOST:$REMOTE_DIR/" \
    || offhost_fail "rsync to $OFFHOST_HOST:$REMOTE_DIR"
  LOCAL_SUMS="$(cd "$DEST" && sha256sum -- * | sort -k2)"
  REMOTE_SUMS="$(ssh "${SSH_OPTS[@]}" "$OFFHOST_HOST" "cd '$REMOTE_DIR' && sha256sum -- * | sort -k2")" \
    || offhost_fail "could not checksum $OFFHOST_HOST:$REMOTE_DIR"
  [[ "$LOCAL_SUMS" == "$REMOTE_SUMS" ]] || offhost_fail "checksum mismatch at $OFFHOST_HOST:$REMOTE_DIR"
  {
    echo "$(date -u +%FT%TZ) OFF-HOST SUCCESS $ENV_NAME"
    echo "copy=$OFFHOST_HOST:$REMOTE_DIR"
    echo "encrypted=$ENCRYPTED"
  } | tee "$BACKUP_ROOT/last-offhost-success"
  rm -f "$BACKUP_ROOT/last-offhost-failure"
fi
