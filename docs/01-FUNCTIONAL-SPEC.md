# Functional Specification

## 1. Product objective

Bem Estar is a private personal health/training platform that receives Apple Health data from Health Auto Export (HAE), preserves the original evidence, normalizes it into a stable internal model, calculates reproducible metrics, exposes the result through a bilingual personal dashboard and an MCP server, and optionally generates conservative LLM-based summaries.

The project is **not a medical device** and must not present metric outputs as diagnosis or treatment.

## 2. Primary actors

- **Owner:** authenticates to the dashboard and configures physiological inputs.
- **HAE:** pushes JSON v2 health metrics/workouts over HTTPS.
- **Worker:** processes durable ingestion jobs and recomputes deterministic metrics.
- **MCP client:** an MCP-capable AI client with valid authorization.
- **AI developer agent:** evolves the repository under `AGENTS.md` constraints.

## 3. Functional requirements

### FR-ING-001 — HAE webhook
The system shall accept `POST` JSON from HAE at `/webhooks/hae/v2` and the compatibility alias `/v1/health-auto-export`.

### FR-ING-002 — authentication
The webhook shall require a dedicated bearer secret distinct from dashboard and MCP secrets.

### FR-ING-003 — fast acknowledgement
The synchronous webhook path shall authenticate, bound request size, validate the envelope, persist compressed raw payload + ingestion row, and return `202`. Parsing/calculation shall not occur in the HTTP request.

### FR-ING-004 — batching and streams
The same endpoint shall accept logical streams: `vitals`, `activity`, `sleep`, `workouts`, `history`, `reconciliation` through `X-Bemestar-Stream`. Unknown/missing values are inferred conservatively.

### FR-ING-005 — raw replay
Accepted payloads shall be stored gzip-compressed on local persistent storage for audit/replay, subject to configurable retention.

### FR-ING-006 — idempotency
Exact retries shall be accepted without duplicating ingestion work. Canonical samples shall use deterministic hashes. Workouts shall use HAE workout IDs where supplied.

### FR-DATA-001 — canonical samples
Health metrics shall be stored independently of HAE's external schema with UTC timestamps and a user-local date.

### FR-DATA-002 — workouts
Workout summaries and time-series samples shall be normalized separately.

### FR-DATA-003 — provenance
Every canonical record shall trace back to an ingestion request; every derived metric shall carry algorithm version and calculation components.

### FR-MET-001 — training
The system shall support per-workout TRIMP, daily load, CTL (42-day time constant), ATL (7-day), pre-day TSB, and 7:28 ACWR.

### FR-MET-002 — sleep
The system shall preserve HAE sleep metadata and derive sleep duration and efficiency score.

### FR-MET-003 — recovery/readiness
The system shall derive versioned recovery, morning readiness, and live readiness from available HRV, resting HR, sleep and training-balance components. Missing components shall be reweighted, never fabricated.

### FR-MET-004 — explicit profile
TRIMP shall not infer HRmax/HRrest. Those inputs must be explicitly configured by the owner. Algorithm coefficient is explicit/versioned.

### FR-API-001 — dashboard API
Authenticated REST endpoints shall provide today's summary, metric history, workouts, ingestion state, profile settings, recomputation, and daily insights.

### FR-UI-001 — PWA
The dashboard shall be mobile-first, installable as a PWA, and available in PT-BR and English. API health data shall not be stored in the service-worker cache.

### FR-MCP-001 — remote MCP
The system shall expose MCP Python SDK v2 over stateless Streamable HTTP at `/mcp`, protected independently of HAE/dashboard auth.

### FR-MCP-002 — primitives
The MCP surface shall use resources for context, tools for model-selected queries/actions, and prompts for user-selected analysis workflows.

### FR-AI-001 — provider abstraction
LLM insight generation shall depend on a provider port. The default shall remain deterministic and functional with no LLM configured. An OpenAI-compatible adapter may be enabled by environment variables.

### FR-NOT-001 — notification port
The domain/application shall not depend on a notification vendor. An outbound notification port shall exist for future failure/health/training notifications.

### FR-OBS-001 — metrics
REST shall expose Prometheus metrics on localhost. Grafana/Prometheus shall be optional operational services.

### FR-OPS-001 — backup
Scripts shall support SQLite-safe backup, raw/config backup, integrity verification, and documented restore.

## 4. Non-functional requirements

- NFR-01: target 4 GiB RAM / 2 vCPU without Kubernetes, Kafka, Redis, Celery, or PostgreSQL.
- NFR-02: one API worker and one ingestion worker by default; SQLite WAL.
- NFR-03: application processes bind only to loopback; Caddy owns internet ingress.
- NFR-04: raw payload contents are never logged.
- NFR-05: health data does not leave the server unless the owner explicitly configures an LLM/notification provider.
- NFR-06: all metric semantic changes require version bumps + regression tests.
- NFR-07: the old Bem Estar deployment is not overwritten by bootstrap scripts automatically.

## 5. Initial acceptance criteria

1. A fixture HAE v2 metrics payload receives `202`, becomes a processed ingestion, and yields canonical samples.
2. Reposting the same request does not duplicate samples.
3. A workout fixture is normalized and visible over REST/MCP.
4. Metrics recomputation is deterministic for a fixed database/profile.
5. Dashboard can log in and display today's cards on a 390px viewport.
6. MCP lists tools/resources/prompts with a valid token and rejects missing/wrong tokens.
7. `make check` passes.
8. Backup can be restored into an empty test directory and SQLite integrity check succeeds.
