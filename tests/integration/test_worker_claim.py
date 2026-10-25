from __future__ import annotations

from datetime import UTC, datetime, timedelta

from bemestar.application.repositories import Repository
from bemestar.infrastructure.config import Settings
from bemestar.infrastructure.db import Base, create_db_engine, make_session_factory
from bemestar.infrastructure.models import IngestionRequest


def test_claim_recovers_stale_processing_job(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'db.sqlite'}", raw_dir=tmp_path / "raw"
    )
    engine = create_db_engine(settings)
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    stale = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    with factory() as session:
        session.add(
            IngestionRequest(
                id="job-1",
                idempotency_key="key-1",
                stream="history",
                payload_hash="a" * 64,
                payload_size=1,
                raw_path="/tmp/missing",
                status="processing",
                processing_started_at=stale,
            )
        )
        session.commit()

    with factory() as session:
        claimed = Repository(session).claim_next_ingestion(lease_seconds=60)
        assert claimed is not None
        assert claimed.id == "job-1"
        assert claimed.status == "processing"
        assert claimed.processing_started_at is not None
        assert claimed.error == "recovered stale processing lease"
