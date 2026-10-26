# Contributing

Thanks for considering a contribution. This project handles personal health data, so changes
must preserve privacy, determinism and auditability.

## Language

Repository documentation, code comments, commit messages, API contracts and CLI output are
**English**. The dashboard and user-facing product strings are bilingual (PT-BR/EN) by design;
localized strings and their tests are product features, not documentation.

## Development setup

Requirements: Python 3.12–3.14, SQLite, and Node.js 22+ for the dashboard.

```bash
git clone <repository-url>
cd bem-estar
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
python scripts/generate_secrets.py
# merge the generated secret values into .env
alembic upgrade head
pytest
```

Dashboard:

```bash
cd dashboard
npm ci
npm run dev
```

## Quality gates

```bash
make check          # ruff, format check, mypy, architecture, tests
make dashboard-build
```

`scripts/verify_release.sh` is the stricter deployment gate and additionally requires
`uv.lock`, `dashboard/package-lock.json`, an empty-database migration and a dashboard build.

## Architecture rules

Read [`AGENTS.md`](AGENTS.md) before changing layers. In short:

- `domain/` has pure rules and metric math; it must not import frameworks, I/O or settings.
- `application/` orchestrates use cases and owns ports.
- `interfaces/` and `adapters/` translate; they do not implement metric formulas.
- SQLAlchemy stays in `infrastructure/` and the single persistence gateway.

Metric or formula changes require a new algorithm version, golden tests and an update to
`docs/04-METRICS-SPEC.md`. Architectural changes require an ADR in `docs/adr/`.

## Tests and fixtures

- Use synthetic fixtures only. Never commit real health exports, tokens or reports.
- Every bug fix should include a regression test.
- Use tolerances for float comparisons; never exact equality for metric assertions.

## Commits and pull requests

- Use Conventional Commits (`feat(ingestion): ...`, `fix(metrics): ...`, `docs: ...`).
- Keep one coherent change per commit.
- Fill in the pull request template and state any contract, migration or security impact.
- Do not include secrets, personal paths, real health data or generated credentials.
- Update documentation when public behavior changes.

## Security

Do not open public issues for vulnerabilities. See [`SECURITY.md`](SECURITY.md).

## License

By contributing, you agree that your contribution is licensed under the MIT License
(see [`LICENSE`](LICENSE)).
