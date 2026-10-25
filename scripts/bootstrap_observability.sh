#!/usr/bin/env bash
set -euo pipefail

# Install/start optional Prometheus + Grafana on the target Ubuntu host.
# Core Bem Estar services do not depend on Docker.
[[ $EUID -ne 0 ]] || { echo "Run as the deploy user, not root; sudo is used where required." >&2; exit 2; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OBS="$ROOT/observability"
ENV_FILE="${BEMESTAR_OBSERVABILITY_ENV_FILE:-/etc/bem-estar/observability.env}"

[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE. Generate it with scripts/generate_production_config.py and install it first." >&2; exit 2; }

if ! command -v docker >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-v2
  sudo systemctl enable --now docker
fi

if ! sudo docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 is required (docker compose)." >&2
  exit 2
fi

cd "$OBS"
sudo docker compose --env-file "$ENV_FILE" pull
sudo docker compose --env-file "$ENV_FILE" up -d
sudo docker compose --env-file "$ENV_FILE" ps

echo "Prometheus: http://127.0.0.1:9090 (loopback only)"
echo "Grafana:    http://127.0.0.1:3000/grafana/ (publish via Caddy)"
