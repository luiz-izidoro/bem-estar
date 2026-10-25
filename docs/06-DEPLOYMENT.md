# Deployment — target Ubuntu VM

Target: Ubuntu 26.04 LTS, `deploy` sudo NOPASSWD, root SSH disabled, Caddy already present, existing `/opt/bem-estar/current` deployment.

## Zero-surprise migration rule

**Do not unzip over `/opt/bem-estar/current`.** Stage a new release first:

```bash
sudo mkdir -p /opt/bem-estar/releases/2026-09-bootstrap
sudo chown -R deploy:deploy /opt/bem-estar/releases/2026-09-bootstrap
unzip <release>.zip -d /opt/bem-estar/releases/2026-09-bootstrap
cd /opt/bem-estar/releases/2026-09-bootstrap/<release>
```

Run tests and a local smoke test before changing the `current` symlink.

## Runtime layout

```text
/opt/bem-estar/releases/<release>/
/opt/bem-estar/current -> releases/<release>
/etc/bem-estar/bem-estar.env
/var/lib/bem-estar/bemestar.db
/var/lib/bem-estar/raw/
/var/backups/bem-estar/
```

## Python

The repository supports Python 3.12–3.14. The examples target Python 3.14. Use a release-local venv:

```bash
cd /opt/bem-estar/releases/<release>
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
pip install -e .
```

For developer workflow, `uv` is recommended; production does not depend on it.

## Config

```bash
sudo mkdir -p /etc/bem-estar /var/lib/bem-estar/raw /var/backups/bem-estar
sudo cp .env.example /etc/bem-estar/bem-estar.env
sudo chmod 600 /etc/bem-estar/bem-estar.env
sudo chown bem-estar:bem-estar /etc/bem-estar/bem-estar.env
sudo chown -R bem-estar:bem-estar /var/lib/bem-estar /var/backups/bem-estar
python scripts/generate_secrets.py > /tmp/bem-estar-secrets.env
# manually merge the four generated secret lines into /etc/bem-estar/bem-estar.env
rm -f /tmp/bem-estar-secrets.env
```

Set production paths:

```text
BEMESTAR_ENV=production
BEMESTAR_DATABASE_URL=sqlite:////var/lib/bem-estar/bemestar.db
BEMESTAR_RAW_DIR=/var/lib/bem-estar/raw
BEMESTAR_PUBLIC_BASE_URL=https://bemestar.example.com
```

## Database

Before migration of any existing future database:

```bash
sudo -u bem-estar /opt/bem-estar/current/scripts/backup.sh
```

For first deployment:

```bash
set -a
source /etc/bem-estar/bem-estar.env
set +a
.venv/bin/alembic upgrade head
```

## Dashboard

Requires Node 22+ only at build time:

```bash
cd dashboard
npm ci
npm run build
```

The resulting `dashboard/dist` is static and served by Caddy; Node does not run in production.

## systemd

Copy units from `deploy/systemd/`, run daemon reload, then start in this order:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now bem-estar-rest.service
curl http://127.0.0.1:8787/healthz
curl http://127.0.0.1:8787/readyz
sudo systemctl enable --now bem-estar-worker.service
sudo systemctl enable --now bem-estar-mcp.service
```

## Caddy

Do not replace the entire existing Caddyfile blindly. Merge the site block from `deploy/Caddyfile.example`. Validate:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Configure DNS `bemestar.example.com` to the VM only after the service works on loopback.

## Cutover

1. old service still running
2. stage new release and tests
3. backup old data/config
4. stop old Bem Estar service
5. update `/opt/bem-estar/current` symlink atomically
6. migrate
7. start REST/worker/MCP
8. merge/reload Caddy
9. run smoke test
10. HAE manual export
11. observe one full ingestion cycle

Rollback is symlink + service rollback; do not downgrade a migrated DB without restoring its matching backup.
