#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

[[ -x .venv/bin/python ]] || { echo "Missing .venv. Run uv sync --extra dev first." >&2; exit 2; }
[[ -f uv.lock ]] || { echo "Missing uv.lock. Run uv lock and commit it before production." >&2; exit 2; }
[[ -f dashboard/package-lock.json ]] || { echo "Missing dashboard/package-lock.json. Run npm install once and commit it before production." >&2; exit 2; }

.venv/bin/python -m compileall -q src tests scripts
.venv/bin/ruff check src tests scripts
.venv/bin/mypy
.venv/bin/python scripts/verify_architecture.py
.venv/bin/pytest -q

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT
export BEMESTAR_ENV=development
export BEMESTAR_DATABASE_URL="sqlite:///$TMPDIR/schema.db"
export BEMESTAR_RAW_DIR="$TMPDIR/raw"
.venv/bin/alembic upgrade head >/dev/null
.venv/bin/alembic check >/dev/null

(
  cd dashboard
  npm ls --depth=0 >/dev/null
  npm run build
)

echo "Release verification: PASS"
