# Audit Report — Audited Bootstrap Release

Date: 2026-09-15

This audit was performed after the first bootstrap package and focused on failure modes that basic happy-path tests did not cover.

## Corrected findings

### 1. HAE logical identity depended on provenance/value

**Risk:** a value corrected by a later reconciliation could be inserted as a second point; HAE/iOS changes that omit `source` could also produce a duplicate.

**Correction:** health/workout sample hashes now identify the logical metric/time slot and exclude `source` and mutable value. Reconciliation updates mutable fields in-place. `source` remains stored as provenance.

**Regression coverage:** parser identity tests + `tests/integration/test_reconciliation.py`.

### 2. Overnight sleep could land on the starting day

**Risk:** fine-grained sleep stages could split the user's overnight session across daily readiness buckets.

**Correction:** Sleep Analysis uses the local waking/end date when present.

### 3. Worker crash could leave jobs in `processing` forever

**Risk:** ingestion queue stalls silently after a process/host failure.

**Correction:** worker uses a lease/claim operation and returns stale jobs to `pending` after the configured lease (default 900 s).

### 4. In-memory rate limiter was unbounded

**Risk:** many distinct source keys could grow process memory.

**Correction:** LRU-bounded key cardinality with configurable `BEMESTAR_RATE_LIMITER_MAX_KEYS`.

### 5. Request body limit was checked after full buffering

**Risk:** chunked requests without useful Content-Length could consume more memory than intended before a 413 response.

**Correction:** webhook reads the ASGI stream incrementally and stops beyond the configured limit. Caddy additionally enforces a 25 MB HAE request body ceiling.

### 6. Prometheus path labels could be attacker-controlled

**Risk:** arbitrary paths create unbounded label cardinality.

**Correction:** metrics use resolved route templates or bounded category labels (`/api/*`, `/webhooks/*`, `/unmatched`).

### 7. Login path leaked some username timing information

**Risk:** password KDF was skipped by Python short-circuit when username was wrong.

**Correction:** password verification always runs; username comparison uses constant-time comparison.

### 8. Low-disk behavior was implicit

**Risk:** accepting HAE payloads until the filesystem is exhausted can corrupt operations and interfere with other services on the target host.

**Correction:** `/readyz` checks a configurable free-space floor (default 1 GiB); webhook rejects new payloads with 507 below the floor. RAW retention defaults to 180 days.

### 9. Metric version selection depended on DB row order

**Risk:** after adding an experimental/new algorithm, Dashboard/MCP could surface the wrong version.

**Correction:** explicit `metric_registry.py` defines active versions. Old versions remain queryable in storage.

### 10. Derived metric provenance did not refresh completely

**Risk:** `computed_at` and some `inputs_hash` fields could not accurately explain recomputation.

**Correction:** all derived upserts update `computed_at`; deterministic input hashes are attached to training/sleep/recovery/readiness outputs.

### 11. Recompute rewrote the full history after every HAE batch

**Risk:** avoidable SQLite writes and increasing contention as history grows.

**Correction:** training state is still evaluated from its correct historical origin, but only dates from the first affected date are rewritten. Earliest source lookup uses SQL `MIN()` rather than loading full history into memory.

### 12. Raw HRV/RHR baselines could overweight high-granularity days

**Risk:** days with more exported points influence robust baseline more than other days.

**Correction:** baseline history now uses one daily median per day.

### 13. Invalid physiological profile could be saved

**Risk:** `hr_max <= hr_rest` makes HR-reserve TRIMP invalid.

**Correction:** boundary schema rejects this combination.

### 14. Optional LLM outage could break insight UI

**Risk:** external provider failure becomes a user-facing API failure.

**Correction:** provider falls back to deterministic insight and logs the external failure without logging health payload content.

### 15. MCP period comparison counted points rather than days

**Risk:** raw high-frequency metrics made “7-day” comparisons point-count dependent.

**Correction:** MCP aggregates raw metric values to daily median before period comparison.

### 16. Shell-sourcing production env is unsafe for generated secrets

**Risk:** PBKDF2 hashes contain `$`; `source` performs shell expansion and can mutate credentials.

**Correction:** production migration launcher parses `KEY=VALUE` without shell expansion (`scripts/run_with_env.py`).

### 17. Deployment cutover lacked a robust rollback path

**Risk:** a migration/service/smoke failure after symlink switch can leave production half-upgraded.

**Correction:** activation now runs release verification, captures a DB snapshot, installs units from absolute release paths, migrates before symlink switch, then rolls back DB + previous symlink on activation failure.

### 18. Backups copied the secret environment by default

**Risk:** every local DB backup unnecessarily multiplied credential copies.

**Correction:** secrets are excluded by default (`BEMESTAR_BACKUP_SECRETS=0`). Off-host secret storage should be handled through a password manager/secret backup policy, not every SQLite snapshot.

### 19. Restore could destroy the only current DB before validation

**Risk:** operator picks the wrong backup.

**Correction:** restore makes a pre-restore safety snapshot first and checks `/readyz` after startup.

### 20. RAW retention was configured but not scheduled

**Risk:** the 180-day policy existed only as a setting and disk usage would continue growing indefinitely.

**Correction:** daily `bem-estar-maintenance.timer` prunes only successfully processed RAW payloads older than retention while keeping canonical data and ingestion audit rows.

### 21. Observability credentials were release-local

**Risk:** Grafana credentials become coupled to an ephemeral release directory.

**Correction:** observability reads `/etc/bem-estar/observability.env`, separate from Git/release folders.

## Deliberately retained constraints

- SQLite remains appropriate for this single-user/single-host workload.
- No Redis/Celery/Kafka/Kubernetes was introduced.
- MCP static Bearer mode remains the bootstrap path for clients that can configure it directly. OAuth/OIDC must be added through a real external Authorization Server when a hosted MCP client requires it; anonymous MCP is not an acceptable workaround.
- RAW data remains local, compressed and private; 180-day retention is the default compromise for the server's current free space.
- Volumetric DDoS is not solved by an application rate limiter. The app provides brute-force/abuse mitigation; network-level protection remains an edge/provider concern.

## Validation status

See `VALIDATION.md` for commands and environment limitations.
