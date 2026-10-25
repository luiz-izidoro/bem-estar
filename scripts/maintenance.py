#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select

from bemestar.infrastructure.config import get_settings
from bemestar.infrastructure.db import create_db_engine, make_session_factory
from bemestar.infrastructure.models import IngestionRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect/prune old processed HAE RAW payloads")
    parser.add_argument(
        "--prune-raw",
        action="store_true",
        help="Actually delete eligible RAW files; default is dry-run",
    )
    parser.add_argument(
        "--days", type=int, default=None, help="Override BEMESTAR_RAW_RETENTION_DAYS"
    )
    args = parser.parse_args()
    settings = get_settings()
    retention = args.days or settings.raw_retention_days
    cutoff = datetime.now(UTC) - timedelta(days=retention)
    engine = create_db_engine(settings)
    factory = make_session_factory(engine)
    candidates: list[IngestionRequest]
    with factory() as session:
        stmt = select(IngestionRequest).where(
            IngestionRequest.status == "processed",
            IngestionRequest.received_at < cutoff.isoformat(),
        )
        candidates = list(session.scalars(stmt))
        existing = [(row, Path(row.raw_path)) for row in candidates if Path(row.raw_path).is_file()]
        total = sum(path.stat().st_size for _, path in existing)
        print(f"eligible_files={len(existing)} compressed_bytes={total} retention_days={retention}")
        if not args.prune_raw:
            print("dry-run only; use --prune-raw after verifying off-host backup policy")
            return
        for row, path in existing:
            path.unlink()
            row.raw_path = f"pruned://{path.name}"
        session.commit()
        print(f"pruned_files={len(existing)}")


if __name__ == "__main__":
    main()
