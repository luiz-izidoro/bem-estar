#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${BEMESTAR_ENV_FILE:-/etc/bem-estar/bem-estar.env}"
BACKUP_DIR="${BEMESTAR_BACKUP_DIR:-/var/backups/bem-estar}"
RETENTION_DAYS="${BEMESTAR_BACKUP_RETENTION_DAYS:-30}"
DB_PATH="${BEMESTAR_DB_PATH:-/var/lib/bem-estar/bemestar.db}"
RAW_DIR="${BEMESTAR_RAW_DIR:-/var/lib/bem-estar/raw}"
BACKUP_RAW="${BEMESTAR_BACKUP_RAW:-0}"
BACKUP_SECRETS="${BEMESTAR_BACKUP_SECRETS:-0}"
RCLONE_REMOTE="${BEMESTAR_RCLONE_REMOTE:-}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
TARGET="$BACKUP_DIR/db/$STAMP"
mkdir -p "$TARGET"

[[ -f "$DB_PATH" ]] || { echo "Database not found: $DB_PATH" >&2; exit 1; }
sqlite3 "$DB_PATH" ".timeout 10000" ".backup '$TARGET/bemestar.db'"
if [[ "$BACKUP_SECRETS" == "1" && -f "$ENV_FILE" ]]; then
  install -m 600 "$ENV_FILE" "$TARGET/bem-estar.env"
fi

# RAW is already gzip-compressed and immutable. Duplicating a full year on the target host
# server every day is deliberately disabled. Set BEMESTAR_BACKUP_RAW=1 only when the
# local capacity has been reviewed, or configure BEMESTAR_RCLONE_REMOTE for true off-host backup.
if [[ "$BACKUP_RAW" == "1" && -d "$RAW_DIR" ]]; then
  tar -C "$(dirname "$RAW_DIR")" -czf "$TARGET/raw.tgz" "$(basename "$RAW_DIR")"
fi
sha256sum "$TARGET"/* > "$TARGET/SHA256SUMS"
find "$BACKUP_DIR/db" -mindepth 1 -maxdepth 1 -type d -mtime "+$RETENTION_DAYS" -exec rm -rf -- {} +

if [[ -n "$RCLONE_REMOTE" ]]; then
  command -v rclone >/dev/null 2>&1 || { echo "BEMESTAR_RCLONE_REMOTE is set but rclone is unavailable" >&2; exit 1; }
  rclone copy "$TARGET" "$RCLONE_REMOTE/db/$STAMP" --immutable
  if [[ -d "$RAW_DIR" ]]; then
    rclone copy "$RAW_DIR" "$RCLONE_REMOTE/raw" --immutable
  fi
fi

echo "Backup created: $TARGET"
