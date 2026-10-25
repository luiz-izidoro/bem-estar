#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /var/backups/bem-estar/db/<timestamp>" >&2
  exit 2
fi
SOURCE="$1"
DB_PATH="${BEMESTAR_DB_PATH:-/var/lib/bem-estar/bemestar.db}"
RAW_DIR="${BEMESTAR_RAW_DIR:-/var/lib/bem-estar/raw}"
SAFETY_ROOT="${BEMESTAR_RESTORE_SAFETY_DIR:-/var/backups/bem-estar/pre-restore}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
[[ -f "$SOURCE/bemestar.db" ]] || { echo "Missing bemestar.db" >&2; exit 1; }
(cd "$SOURCE" && sha256sum -c SHA256SUMS)

sudo systemctl stop bem-estar-rest bem-estar-worker bem-estar-mcp || true
if [[ -f "$DB_PATH" ]]; then
  sudo mkdir -p "$SAFETY_ROOT/$STAMP"
  sudo sqlite3 "$DB_PATH" ".timeout 10000" ".backup '$SAFETY_ROOT/$STAMP/bemestar.db'"
  echo "Safety snapshot: $SAFETY_ROOT/$STAMP/bemestar.db"
fi
sudo install -o bem-estar -g bem-estar -m 600 "$SOURCE/bemestar.db" "$DB_PATH"
if [[ -f "$SOURCE/raw.tgz" ]]; then
  sudo rm -rf "$RAW_DIR"
  sudo mkdir -p "$(dirname "$RAW_DIR")"
  sudo tar -C "$(dirname "$RAW_DIR")" -xzf "$SOURCE/raw.tgz"
  sudo chown -R bem-estar:bem-estar "$RAW_DIR"
fi
sudo systemctl start bem-estar-rest bem-estar-worker bem-estar-mcp
curl -fsS http://127.0.0.1:8787/readyz >/dev/null
echo "Restore complete and /readyz is healthy."
