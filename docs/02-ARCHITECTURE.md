# Architecture

## Architectural style

**Modular monolith, ports/adapters (hexagonal) with process separation at inbound interfaces.**

The application is one codebase and one database. API, worker and MCP are separate processes for isolation, not separate services with independent business models.

```mermaid
flowchart TB
    AW[Apple Watch] --> AH[Apple Health]
    AH --> HAE[Health Auto Export]
    HAE -->|HTTPS POST JSON v2| CADDY[Caddy / TLS]
    CADDY -->|/webhooks/hae/v2| REST[REST :8787]
    CADDY -->|/mcp| MCP[MCP :8788]
    CADDY -->|/| WEB[React PWA static]
    CADDY -->|/grafana| GRAFANA[Grafana]

    REST --> RAW[(Raw gzip inbox)]
    REST --> DB[(SQLite WAL)]
    WORKER[Ingestion worker] --> RAW
    WORKER --> DB
    WORKER --> APP[Application services]
    REST --> APP
    MCP --> APP
    APP --> DOMAIN[Domain / metric rules]
    APP --> DB
    PROM[Prometheus] -->|scrape /metrics| REST
    GRAFANA --> PROM
```

## Request lifecycle

```mermaid
sequenceDiagram
    participant H as HAE
    participant C as Caddy
    participant A as REST API
    participant R as Raw Store
    participant D as SQLite
    participant W as Worker
    participant M as Metric Engine

    H->>C: POST /webhooks/hae/v2
    C->>A: reverse proxy
    A->>A: bearer + size + JSON envelope
    A->>R: atomic gzip write
    A->>D: INSERT ingestion(pending)
    A-->>H: 202 Accepted + ingestion_id
    W->>D: claim pending
    W->>R: read raw payload
    W->>W: HAE v2 -> canonical
    W->>D: idempotent samples/workouts
    W->>M: recompute deterministic metrics
    M->>D: versioned derived metrics
    W->>D: ingestion=processed
```

## Dependency direction

```mermaid
flowchart LR
    API[interfaces/api] --> APP[application]
    MCP[interfaces/mcp] --> APP
    WORKER[interfaces/worker] --> APP
    HAE[adapters/hae] --> APP
    LLM[adapters/llm] --> PORTS[application ports]
    APP --> DOM[domain]
    REPO[application repository facade] --> DB[infrastructure database]
```

`domain/` must remain framework-free. See `AGENTS.md`.

## Why not microservices

The target is one owner, one 4 GiB VM, one source, low write concurrency, and analytics that benefit from transactional proximity. Microservices would add network failure modes, secret distribution, deployment coordination, observability overhead, and resource consumption without providing a scaling benefit.

## Why SQLite

- single-owner workload
- WAL supports concurrent readers + one writer
- low operational overhead
- native backup API
- easy to inspect/recover
- repository/application seams preserve a future PostgreSQL migration path

Revisit only if measured write contention, database size, or multi-user requirements justify it. This requires an ADR.

## Why separate MCP process

MCP and REST share application code but not process lifecycle. Benefits:

- MCP SDK upgrades cannot break webhook availability.
- MCP auth/transport changes remain isolated.
- resource limits/restarts can differ.
- REST remains small and boring.

## Why no in-request parsing

HAE background execution has device/network constraints. Returning `202` after durable acceptance minimizes mobile timeout risk and makes server processing replayable.

## Runtime topology on target VM

```text
Caddy :80/:443
  ├─ /api, /auth, /webhooks, /healthz, /readyz -> 127.0.0.1:8787
  ├─ /mcp -> 127.0.0.1:8788
  ├─ /grafana -> 127.0.0.1:3000
  └─ / -> /opt/bem-estar/current/dashboard/dist

systemd
  ├─ bem-estar-rest.service
  ├─ bem-estar-worker.service
  └─ bem-estar-mcp.service

Docker (optional operational plane only)
  ├─ prometheus (host network, 127.0.0.1:9090)
  └─ grafana    (host network, 127.0.0.1:3000)

Persistent
  ├─ /var/lib/bem-estar/bemestar.db
  ├─ /var/lib/bem-estar/raw/
  └─ /var/backups/bem-estar/
```
