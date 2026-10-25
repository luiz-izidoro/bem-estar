# AGENTS.md — AI agent operating contract

This file is normative for AI coding agents working in this repository.

## Mission

Evolve Bem Estar without eroding architecture, metric reproducibility, privacy, or operational simplicity. Prefer a small, explicit, boring design over clever abstractions.

## Non-negotiable architecture

Dependency direction:

```text
interfaces -> application -> domain
adapters    -> application -> domain
infrastructure may be used by adapters/interfaces bootstrap only
```

The **domain layer must never import** FastAPI, SQLAlchemy, MCP, HTTP clients, filesystem code, environment settings, or dashboard concerns.

The **application layer must not import interfaces**. It may depend on protocols/ports and domain code.

The **MCP and REST adapters must never implement metric formulas**. They call application services.

The **HAE adapter must not leak HAE-shaped dictionaries past normalization**. Convert them into canonical commands/entities first.

## Change protocol

### No ADR required

- bug fix that preserves contracts
- tests
- docs
- UI-only change
- adding an adapter that satisfies an existing port
- performance improvement with unchanged semantics

### ADR required before code

- moving responsibilities between layers
- replacing SQLite / persistence strategy
- adding a message broker/cache/microservice
- changing authentication model
- changing public REST/MCP contracts incompatibly
- introducing a framework into `domain/`
- changing raw retention semantics

Create `docs/adr/NNNN-title.md` using the existing template and include alternatives/rejected options.

### Metric change protocol

Active algorithm registry: `src/bemestar/application/metric_registry.py`. New versions may coexist in storage, but Dashboard/API/MCP must resolve the explicit active version through this registry; never rely on database row order.


Never silently change a health/training metric formula.

1. Create a new algorithm version (`readiness-v1` -> `readiness-v2`).
2. Add/adjust golden regression fixtures.
3. Document the exact formula and migration impact in `docs/04-METRICS-SPEC.md`.
4. Keep old results queryable unless an explicit migration removes them.
5. Do not infer physiological parameters that have not been configured.

## Definition of Done

A task is complete only when applicable items pass:

- `ruff check src tests`
- `python scripts/verify_architecture.py`
- `pytest`
- `scripts/verify_release.sh` before production activation
- migrations work on an empty database
- migrations are forward-only and do not destroy health data by default
- API schema remains coherent
- new public behavior is documented
- secrets do not enter Git
- raw health payloads are not logged
- error logs identify ingestion IDs, not health payload contents
- dashboard is usable at 390px viewport width
- both EN and PT-BR strings exist for new dashboard text

## Coding standards

- Python: typed, small functions, explicit names, Pydantic only at boundaries.
- Prefer dataclasses / plain types in domain code.
- SQLAlchemy is confined to `infrastructure/` plus the single persistence gateway `application/repositories.py`; never scatter ORM queries through interfaces or metric/domain modules.
- Use UTC for timestamps at rest; keep a separate `local_date` for user-facing daily aggregation.
- All dedupe keys must be deterministic and documented.
- Never use float equality for metric assertions; use tolerances.
- Never swallow exceptions. Translate them at interface boundaries or fail the job visibly.
- Do not add a dependency when the standard library is sufficient and the dependency does not materially reduce risk.

## Data safety

- Do not delete raw payloads or canonical records as part of a refactor.
- Do not mutate old derived metrics in place when semantics change; create a new algorithm version.
- Backup before schema migrations in production.
- Never expose `/var/lib/bem-estar` or raw paths via Caddy.
- Never print tokens/password hashes.

## HAE ingestion rules

Webhook request path must remain fast:

```text
AUTH -> size check -> durable raw write -> ingestion row -> 202
```

Parsing and metric recomputation belong in the worker.

HAE retries/reconciliation are expected. Idempotency is therefore a feature, not an error condition. A logical sample identity must not depend on HAE `source`, because that field may be absent on newer iOS exports; corrections must update the canonical slot rather than create a duplicate.

## MCP rules

- Use MCP Python SDK **v2** APIs (`MCPServer`, not legacy `FastMCP`).
- Deploy over stateless Streamable HTTP.
- Resources expose context/data; tools perform model-selected queries/actions; prompts are user-selected workflows.
- Any mutation tool must remain narrow and clearly named.
- MCP uses its own bearer token, never the HAE token or dashboard session secret.

## Agent workflow

Before editing:

1. Read the relevant functional spec and ADRs.
2. Locate the owning layer/module.
3. State the contract being changed in the task notes/commit message.
4. Add or update tests first for formula/contract changes.

During editing:

- Prefer one coherent vertical slice per commit.
- Avoid drive-by refactors.
- Keep the project runnable after each commit.

Before finishing:

```bash
make check
```

Before any production cutover, additionally run:

```bash
./scripts/verify_release.sh
```

Never bypass the lockfile/build/migration gates just to activate a release.

If a check cannot run, explain exactly why and leave a reproducible command for the human/next agent.

## Git conventions

Use Conventional Commit style:

- `feat(ingestion): ...`
- `fix(metrics): ...`
- `refactor(api): ...`
- `docs(architecture): ...`
- `test(hae): ...`
- `chore(deploy): ...`

Do not rewrite shared history. Do not force-push unless explicitly instructed.
