# First Production Deploy Runbook — Ubuntu

Target host:

```text
Ubuntu 26.04 LTS x86_64
2 vCPU
3.7 GiB RAM
/opt/bem-estar
Caddy already listening on 80/443
REST target 127.0.0.1:8787
MCP target 127.0.0.1:8788
```

The runbook intentionally keeps Python services under systemd and uses Docker only for Prometheus/Grafana.

## Phase A — DNS

At the DNS provider for `example.com`, create:

```text
Type: A
Name: bemestar
Value: 203.0.113.10
TTL: 300 / Auto
```

Do not add an AAAA record unless the VPS has working IPv6 ingress configured.

Validate:

```bash
getent ahostsv4 bemestar.example.com
```

The result must include `203.0.113.10` before Caddy attempts public certificate issuance.

## Phase B — unpack into a staging workspace

Example:

```bash
mkdir -p ~/src
cd ~/src
unzip <release>.zip
cd <release>
```

Read first:

```bash
cat AGENTS.md
cat docs/17-PORTALS-AND-CREDENTIALS.md
```

## Phase C — create credentials

```bash
python3 scripts/generate_production_config.py \
  --domain bemestar.example.com \
  --username admin
```

Move `ACCESS-CREDENTIALS.txt` to your password manager immediately.

Install the two environment files:

```bash
sudo install -d -o root -g bem-estar -m 0750 /etc/bem-estar
sudo install -o root -g bem-estar -m 0640 generated-config/bem-estar.env /etc/bem-estar/bem-estar.env
sudo install -o root -g bem-estar -m 0640 generated-config/observability.env /etc/bem-estar/observability.env
```

## Phase D — stage dependencies/build

Run:

```bash
./scripts/bootstrap_server.sh
```

This creates a timestamped release under `/opt/bem-estar/releases/`, installs the locked Python dependencies with `uv`, builds the React Dashboard with `npm ci`, and creates `/opt/bem-estar/current-next`.

Both `uv.lock` and `dashboard/package-lock.json` are committed and installed in frozen mode. Update them only when dependencies change, and commit the regenerated files before the next production release.

## Phase E — Caddy

Do not overwrite the live Caddy configuration blindly. Merge the `bemestar.example.com` site from:

```text
deploy/Caddyfile.example
```

Validate before reload:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
sudo journalctl -u caddy -n 100 --no-pager
```

Validate TLS externally:

```bash
curl -I https://bemestar.example.com/healthz
```

Before the REST service is live, a temporary 502 from Caddy is expected; TLS itself must still be valid.

## Phase F — activate staged release

Find the staged target:

```bash
readlink -f /opt/bem-estar/current-next
```

Then:

```bash
cd "$(readlink -f /opt/bem-estar/current-next)"
./scripts/install_release.sh "$PWD"
```

The activation script:

1. runs the full release gate;
2. snapshots the existing SQLite DB if present;
3. stops app processes;
4. installs systemd units;
5. runs Alembic using a non-shell-expanded EnvironmentFile parser;
6. switches `/opt/bem-estar/current`;
7. starts REST/worker/MCP;
8. runs smoke tests;
9. rolls back DB + symlink if activation fails.

## Phase G — observability

Once the core app is healthy:

```bash
cd /opt/bem-estar/current
./scripts/bootstrap_observability.sh
```

Validate:

```bash
sudo docker ps
curl -fsS http://127.0.0.1:9090/-/healthy
curl -I http://127.0.0.1:3000/grafana/login
```

Public portal:

```text
https://bemestar.example.com/grafana/
```

## Phase H — service verification

```bash
sudo systemctl status bem-estar-rest bem-estar-worker bem-estar-mcp bem-estar-maintenance.timer bem-estar-backup.timer --no-pager
curl -fsS https://bemestar.example.com/healthz
curl -fsS https://bemestar.example.com/readyz
```

Useful logs:

```bash
sudo journalctl -u bem-estar-rest -f
sudo journalctl -u bem-estar-worker -f
sudo journalctl -u bem-estar-mcp -f
```

## Phase I — configure HAE

Follow:

```text
docs/16-HAE-WEBHOOK-SETUP.md
```

Create and test each automation separately. Do not start the historical import before normal `Since Last Sync` traffic processes cleanly.

## Phase J — verify portals

### Dashboard

```text
https://bemestar.example.com/
```

### Grafana

```text
https://bemestar.example.com/grafana/
```

### MCP

```text
https://bemestar.example.com/mcp
```

### HAE

```text
https://bemestar.example.com/webhooks/hae/v2
```

## Phase K — first backup drill

Do not call backups "done" until a restore has been tested.

Create backup:

```bash
sudo /opt/bem-estar/current/scripts/backup.sh
```

Inspect:

```bash
sudo find /var/backups/bem-estar -maxdepth 3 -type f -ls
```

For real disaster tolerance, configure `BEMESTAR_RCLONE_REMOTE` to an off-host target. A backup on the same VPS does not protect against VPS/disk/account loss.

## Production acceptance checklist

- [ ] DNS A record correct
- [ ] Caddy certificate valid
- [ ] `/healthz` healthy
- [ ] `/readyz` healthy with >1 GiB free
- [ ] REST systemd active
- [ ] worker systemd active
- [ ] MCP systemd active
- [ ] maintenance timer active
- [ ] backup timer active
- [ ] Grafana login works
- [ ] Prometheus sees Bem Estar target UP
- [ ] Dashboard login works
- [ ] HAE vitals test returns 202 and processes
- [ ] HAE activity test processes
- [ ] HAE sleep test processes
- [ ] HAE workouts test processes
- [ ] `make check` passes
- [ ] `scripts/verify_release.sh` passes
- [ ] backup created
- [ ] restore procedure understood/tested on a disposable copy
- [ ] `ACCESS-CREDENTIALS.txt` moved to password manager and deleted
