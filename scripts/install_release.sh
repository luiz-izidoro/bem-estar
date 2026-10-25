#!/usr/bin/env bash
set -euo pipefail
# Activate a fully built/verified staged release. Run as the deploy user, never root.
RELEASE="${1:-$(pwd)}"
ENV_FILE="${BEMESTAR_ENV_FILE:-/etc/bem-estar/bem-estar.env}"
CURRENT_LINK="/opt/bem-estar/current"
PREVIOUS_TARGET=""
ROLLBACK_DB=""

[[ -f "$RELEASE/pyproject.toml" ]] || { echo "Not a Bem Estar release: $RELEASE" >&2; exit 2; }
[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE" >&2; exit 2; }
[[ $EUID -ne 0 ]] || { echo "Run as the deploy user, not root." >&2; exit 2; }
[[ -x "$RELEASE/.venv/bin/alembic" ]] || { echo "Missing .venv; bootstrap the staged release first." >&2; exit 2; }
[[ -d "$RELEASE/dashboard/dist" ]] || { echo "dashboard/dist is missing; build dashboard first." >&2; exit 2; }

if [[ -L "$CURRENT_LINK" ]]; then
  PREVIOUS_TARGET="$(readlink -f "$CURRENT_LINK")"
fi

rollback() {
  status=$?
  if [[ $status -eq 0 ]]; then return 0; fi
  echo "Release activation failed; attempting rollback..." >&2
  sudo systemctl stop bem-estar-rest.service bem-estar-worker.service bem-estar-mcp.service 2>/dev/null || true
  if [[ -n "$ROLLBACK_DB" && -f "$ROLLBACK_DB/bemestar.db" ]]; then
    sudo install -o bem-estar -g bem-estar -m 600 "$ROLLBACK_DB/bemestar.db" /var/lib/bem-estar/bemestar.db
  fi
  if [[ -n "$PREVIOUS_TARGET" && -d "$PREVIOUS_TARGET" ]]; then
    sudo ln -sfn "$PREVIOUS_TARGET" "$CURRENT_LINK"
    sudo chown -h root:root "$CURRENT_LINK"
  else
    sudo rm -f "$CURRENT_LINK"
  fi
  sudo systemctl daemon-reload
  sudo systemctl start bem-estar-rest.service bem-estar-worker.service bem-estar-mcp.service 2>/dev/null || true
  exit "$status"
}
cd "$RELEASE"
"$RELEASE/scripts/verify_release.sh"
trap rollback ERR

if [[ -f /var/lib/bem-estar/bemestar.db ]]; then
  BACKUP_OUTPUT="$(sudo BEMESTAR_BACKUP_RAW=0 BEMESTAR_BACKUP_SECRETS=0 "$RELEASE/scripts/backup.sh")"
  ROLLBACK_DB="${BACKUP_OUTPUT##*: }"
fi

sudo systemctl stop bem-estar-rest.service bem-estar-worker.service bem-estar-mcp.service 2>/dev/null || true
sudo install -m 0644 "$RELEASE/deploy/systemd/bem-estar-rest.service" /etc/systemd/system/
sudo install -m 0644 "$RELEASE/deploy/systemd/bem-estar-worker.service" /etc/systemd/system/
sudo install -m 0644 "$RELEASE/deploy/systemd/bem-estar-mcp.service" /etc/systemd/system/
sudo install -m 0644 "$RELEASE/deploy/systemd/bem-estar-backup.service" /etc/systemd/system/
sudo install -m 0644 "$RELEASE/deploy/systemd/bem-estar-backup.timer" /etc/systemd/system/
sudo install -m 0644 "$RELEASE/deploy/systemd/bem-estar-maintenance.service" /etc/systemd/system/
sudo install -m 0644 "$RELEASE/deploy/systemd/bem-estar-maintenance.timer" /etc/systemd/system/

sudo -u bem-estar "$RELEASE/scripts/run_with_env.py" "$ENV_FILE" "$RELEASE/.venv/bin/alembic" upgrade head
sudo ln -sfn "$RELEASE" "$CURRENT_LINK"
sudo chown -h root:root "$CURRENT_LINK"
sudo systemctl daemon-reload
sudo systemctl enable --now bem-estar-rest.service bem-estar-worker.service bem-estar-mcp.service bem-estar-backup.timer bem-estar-maintenance.timer
sleep 2
"$RELEASE/scripts/smoke_test.sh" http://127.0.0.1:8787

trap - ERR
echo "Release activated: $RELEASE"
echo "Previous release: ${PREVIOUS_TARGET:-none}"
echo "Caddy is intentionally not modified automatically; validate and reload deploy/Caddyfile.example separately."
