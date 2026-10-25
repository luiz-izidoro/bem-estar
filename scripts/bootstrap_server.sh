#!/usr/bin/env bash
set -euo pipefail
# Idempotent staging helper for the target Ubuntu host. Run from repository root as the deploy user.
[[ $EUID -ne 0 ]] || { echo "Run as the deploy user, not root." >&2; exit 1; }
DEPLOY_USER="${DEPLOY_USER:-$(id -un)}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_ROOT="/opt/bem-estar/releases"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RELEASE="$RELEASE_ROOT/$STAMP"

sudo apt-get update
sudo apt-get install -y sqlite3 curl rsync python3-venv nodejs npm
command -v uv >/dev/null 2>&1 || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

sudo id bem-estar >/dev/null 2>&1 || sudo useradd --system --home /var/lib/bem-estar --shell /usr/sbin/nologin bem-estar
sudo install -d -o bem-estar -g bem-estar -m 750 /var/lib/bem-estar /var/lib/bem-estar/raw /var/backups/bem-estar
sudo install -d -o root -g bem-estar -m 750 /etc/bem-estar
sudo install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 755 "$RELEASE_ROOT"
mkdir -p "$RELEASE"
rsync -a --delete --exclude .git --exclude .venv --exclude dashboard/node_modules --exclude generated-config "$ROOT/" "$RELEASE/"
cd "$RELEASE"

# Lockfiles are committed; refresh them explicitly when dependencies change.
[[ -f uv.lock ]] || { echo "Missing uv.lock. Commit it before staging a release." >&2; exit 2; }
[[ -f dashboard/package-lock.json ]] || { echo "Missing dashboard/package-lock.json. Commit it before staging a release." >&2; exit 2; }
uv sync --frozen --extra dev --python 3.14

cd dashboard
npm ci
npm run build
cd ..

./scripts/verify_release.sh
sudo ln -sfn "$RELEASE" /opt/bem-estar/current-next
sudo chown -h root:root /opt/bem-estar/current-next

echo "Staged and verified release at $RELEASE"
echo "Next: install /etc/bem-estar env files, review Caddy, then run scripts/install_release.sh $RELEASE"
