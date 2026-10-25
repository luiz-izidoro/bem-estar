# Validation Report

Generated: 2026-10-25
Release line: `0.2.0`

## Passed in this environment

```text
python -m compileall -q src tests scripts migrations       PASS
ruff check src tests scripts                               PASS
ruff format --check src tests scripts                      PASS
mypy (strict, 37 source files)                             PASS
python scripts/verify_architecture.py                      PASS
pytest -q                                                  PASS — 29 tests
pytest --cov (fail_under=70)                               PASS — 70.86%
.env.example CSV list parsing regression                   PASS
deterministic insight formatting regression                PASS
fresh temporary SQLite: alembic upgrade head               PASS
same DB: alembic check                                     PASS — no schema drift
bash -n scripts/*.sh                                       PASS
dashboard: npm ci && npm run build                         PASS
scripts/verify_release.sh                                  PASS
Python 3.12 and 3.14 test runs                             PASS
```

Coverage is measured with branch coverage over `src/bemestar`; the minimum enforced by
`pyproject.toml` is 70%.

## Audit corrections included

See `docs/19-AUDIT-REPORT.md`. The audited release fixes/guards:

- streaming webhook body ceiling + Caddy 25 MB edge ceiling;
- bounded rate-limiter key cardinality and bounded Prometheus route labels;
- constant-work password verification path for unknown usernames;
- disk readiness/507 ingest safety floor;
- stale ingestion lease recovery;
- reconciliation that updates logical slots rather than duplicating corrections;
- HAE `source` treated as provenance rather than identity (important for newer iOS exports where it may be omitted);
- sleep assigned to waking day;
- explicit active derived-metric versions;
- updated `computed_at` / deterministic input hashes;
- less wasteful affected-period metric rewrites;
- daily-median HRV/RHR baseline history;
- heart-rate profile validation;
- LLM failure fallback;
- MCP period comparison aggregated by calendar day;
- safe EnvironmentFile execution without shell expansion;
- transactional-ish release cutover with DB/symlink rollback;
- backups excluding app secrets by default;
- pre-restore safety snapshot;
- dedicated persistent observability credentials;
- daily RAW-retention timer.

## Operational drills executed (2026-10-25)

- **MCP Streamable HTTP:** isolated server and database; unauthenticated `/mcp` returned 401,
  protected-resource metadata returned 200, and an authenticated client listed 8 tools, read
  `bemestar://today`, listed 3 prompts and called `get_health_summary` successfully.
- **Backup:** `scripts/backup.sh` created a SQLite backup and `SHA256SUMS`; `sha256sum -c` passed,
  `PRAGMA integrity_check` returned `ok`, and the restored copy matched the source hash with 5
  health samples and 493 derived metric rows.
- **Caddy:** `caddy validate --config deploy/Caddyfile.example --adapter caddyfile` returned
  `Valid configuration`; the example was normalized with `caddy fmt`.
- **Docker Compose:** `docker compose -f observability/docker-compose.yml config` parsed
  successfully; the running Prometheus (`/-/healthy`) and Grafana (`/grafana/api/health`) endpoints
  reported healthy.

## Target-server gates

These checks require a real host, device or public DNS and are therefore **not** marked as passed by
this report:

- real Health Auto Export traffic from an iPhone;
- production `restore.sh` wrapper (systemd stop/start and service-owner install), since the data
  restore itself was verified separately;
- public DNS/TLS validation and Caddy reload for the real hostname;
- off-host backup copy with rclone.

The target host must run:

```bash
./scripts/bootstrap_server.sh
```

and the staged release must pass:

```bash
./scripts/verify_release.sh
```

before `scripts/install_release.sh` can activate it.

## External documentation

The upstream references used during implementation are recorded in `docs/12-SOURCES.md`. They
were checked on 2026-09-15; re-check versions before a production upgrade.
