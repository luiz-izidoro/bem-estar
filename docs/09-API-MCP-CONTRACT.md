# REST + MCP Contract

## REST

Public ingress paths are protected except health/readiness and HAE token-auth endpoint.

### Auth

- `POST /auth/login`
- `POST /auth/logout`
- `GET /api/v1/me`

### Dashboard data

- `GET /api/v1/dashboard/today?day=YYYY-MM-DD`
- `GET /api/v1/metrics/{metric}?days=30`
- `GET /api/v1/workouts?days=30`
- `GET /api/v1/ingestions?limit=20`
- `GET /api/v1/insights/daily?language=pt-BR`

### Profile/admin

- `GET /api/v1/settings/profile`
- `PUT /api/v1/settings/profile` (CSRF)
- `POST /api/v1/admin/recompute` (CSRF)

### Ingestion

- `POST /webhooks/hae/v2` bearer HAE token
- `POST /v1/health-auto-export` compatibility alias

### Operations

- `GET /healthz`
- `GET /readyz`
- `GET /metrics` (loopback only; do not route through Caddy)

## MCP v2

Transport: stateless Streamable HTTP at `/mcp`; JSON responses enabled.

### Tools

- `get_health_summary(day?)`
- `get_metric_history(metric, days=30)`
- `analyze_sleep(day?)`
- `analyze_training_load(day?)`
- `analyze_workouts(days=14)`
- `compare_periods(metric, current_days=7, previous_days=7)`
- `get_ingestion_status(limit=10)`
- `recompute_metrics()`

`recompute_metrics` is the only mutation-like MCP action in v0.1; it does not alter raw/canonical source data.

### Resources

- `bemestar://today`
- `bemestar://day/{day}`
- `bemestar://metric/{metric}`

### Prompts

- `daily_review(language="pt-BR")`
- `weekly_training_review(language="pt-BR")`
- `sleep_review(language="pt-BR")`

## Contract evolution

Additive fields are allowed in `0.x`. Breaking endpoint/tool changes require ADR and a migration note. Metric semantic changes are not API version changes; they are algorithm version changes and must remain discoverable in returned data.
