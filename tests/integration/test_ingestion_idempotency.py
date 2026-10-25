from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select

from bemestar.adapters.hae.raw_store import RawStore
from bemestar.application.ingestion_service import IngestionProcessor
from bemestar.infrastructure.config import Settings
from bemestar.infrastructure.db import Base, create_db_engine, make_session_factory
from bemestar.infrastructure.models import HealthSample, IngestionRequest, Workout

FIXTURE = Path(__file__).parents[1] / "fixtures" / "hae_v2_sample.json"


def _ingestion(raw_store: RawStore, raw: bytes, key: str) -> IngestionRequest:
    import hashlib

    digest = hashlib.sha256(raw).hexdigest()
    path = raw_store.write(raw, digest, "history")
    return IngestionRequest(
        id=str(uuid.uuid4()),
        idempotency_key=key,
        stream="history",
        payload_hash=digest,
        payload_size=len(raw),
        raw_path=str(path),
        status="pending",
    )


def test_replayed_records_do_not_duplicate_canonical_data(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    settings = Settings(
        database_url=f"sqlite:///{db_path}", raw_dir=tmp_path / "raw", timezone="America/Sao_Paulo"
    )
    engine = create_db_engine(settings)
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    raw = FIXTURE.read_bytes()
    store = RawStore(settings.raw_dir)

    with factory() as session:
        first = _ingestion(store, raw, "first")
        session.add(first)
        session.commit()
        IngestionProcessor(session, settings).process(first)

    with factory() as session:
        second = _ingestion(store, raw, "second")
        session.add(second)
        session.commit()
        second_id = second.id
        IngestionProcessor(session, settings).process(second)

    with factory() as session:
        samples = list(session.scalars(select(HealthSample)))
        workouts = list(session.scalars(select(Workout)))
        assert len(samples) == 5
        assert len(workouts) == 1
        replay = session.get(IngestionRequest, second_id)
        assert replay is not None
        assert replay.records_inserted == 0
        assert replay.records_updated == 0
        assert replay.records_ignored == 9  # 5 health + 1 workout + 3 workout samples
