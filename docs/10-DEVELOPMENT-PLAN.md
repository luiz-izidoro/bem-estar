# Development Plan / Backlog

The bootstrap intentionally contains a complete vertical foundation, not every final visualization. Work from this order and keep each milestone releasable.

## M0 — Bootstrap (included)

- repository and architecture guardrails
- SQLAlchemy/Alembic canonical schema
- HAE v2 webhook + raw inbox
- polling worker
- HAE metric/workout parser
- deterministic metric engine v1
- REST auth/API
- MCP v2 server
- React PWA shell
- Prometheus/Grafana baseline
- systemd/Caddy deployment assets
- backup/runbook/docs/tests

Exit: fixture ingestion end-to-end passes.

## M1 — Production cutover

1. run `make check` on target server
2. configure DNS `bemestar.example.com`
3. stage release without overwriting old deployment
4. configure secrets/profile
5. test HAE manual export
6. enable four incremental streams
7. enable reconciliation
8. observe 72h

## M2 — Historical import and parity

- ingest full desired HAE history in bounded batches
- import/compare selected outputs from legacy Bem Estar
- create golden tests for known historical days/workouts
- resolve metric discrepancies explicitly
- only then mark legacy app read-only

## M3 — Dashboard depth

- Overview trend charts
- Sleep page with stages/consistency
- Training page: calendar, TRIMP/CTL/ATL/TSB/ACWR
- Workout detail page + minute HR series
- Recovery/readiness component drill-down
- Data health/ingestion admin
- expand Settings UI beyond the included HR/profile/language controls
- offline shell only; never offline-cache API health data

## M4 — AI insights

- harden `LLMProvider` contract
- provider selection (OpenAI-compatible/M365 proxy/local)
- daily/weekly structured prompt templates
- redact unnecessary fields before outbound call
- token/cost telemetry without content logging
- cache insight by input hash/provider/model

## M5 — Notifications

- implement notification provider(s)
- ingestion failure alert
- stale-data alert
- optional low-readiness/training-load summaries with configurable thresholds
- quiet hours and deduplication

## M6 — MCP production auth

For hosted clients requiring OAuth discovery:

- choose a real OAuth 2.1 IdP
- implement JWT/introspection `TokenVerifier`
- exact audience/resource validation
- test multiple MCP clients independently
- remove/disable static bootstrap token when migration is complete

Do not build a home-grown OAuth authorization server unless there is a strong documented reason.

## M7 — Operations hardening

- systemd timers for backup/retention
- encrypted off-host backup
- Grafana alerts
- dependency update automation
- restore drill automation
- raw retention dry-run/cleanup

## Technical debt explicitly deferred

- PostgreSQL: no evidence it is needed
- Redis/Celery: no evidence it is needed
- Kubernetes: not appropriate for this host/product
- event broker: polling SQLite queue is enough for one worker
- native iOS app: REST contract intentionally allows it later

## Definition of success

The project is successful when adding a source, UI view, metric or LLM provider does not require changing unrelated layers, and when any historical score can be explained by versioned code + retained inputs.
