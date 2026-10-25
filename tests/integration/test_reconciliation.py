from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from sqlalchemy import select

from bemestar.adapters.hae.raw_store import RawStore
from bemestar.application.ingestion_service import IngestionProcessor
from bemestar.infrastructure.config import Settings
from bemestar.infrastructure.db import Base, create_db_engine, make_session_factory
from bemestar.infrastructure.models import HealthSample, IngestionRequest

FIXTURE = Path(__file__).parents[1] / "fixtures" / "hae_v2_sample.json"


def _job(store: RawStore, raw: bytes, key: str) -> IngestionRequest:
    digest = hashlib.sha256(raw).hexdigest()
    path = store.write(raw, digest, "reconciliation")
    return IngestionRequest(
        id=str(uuid.uuid4()),
        idempotency_key=key,
        stream="reconciliation",
        payload_hash=digest,
        payload_size=len(raw),
        raw_path=str(path),
        status="processing",
    )


def test_reconciliation_updates_value_without_creating_duplicate(tmp_path: Path) -> None:
    settings = Settings(
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        raw_dir=tmp_path / "raw",
        timezone="America/Sao_Paulo",
    )
    engine = create_db_engine(settings)
    Base.metadata.create_all(engine)
    factory = make_session_factory(engine)
    store = RawStore(settings.raw_dir)

    original_payload = json.loads(FIXTURE.read_text())
    original_raw = json.dumps(original_payload).encode()
    with factory() as session:
        job = _job(store, original_raw, "original")
        session.add(job)
        session.commit()
        IngestionProcessor(session, settings).process(job)

    corrected = json.loads(FIXTURE.read_text())
    corrected["data"]["metrics"][0]["data"][0]["qty"] = 77.7
    corrected["data"]["metrics"][0]["data"][0].pop("source", None)
    corrected_raw = json.dumps(corrected).encode()
    with factory() as session:
        job = _job(store, corrected_raw, "corrected")
        session.add(job)
        session.commit()
        job_id = job.id
        IngestionProcessor(session, settings).process(job)

    with factory() as session:
        rows = list(
            session.scalars(
                select(HealthSample).where(HealthSample.metric_name == "heart_rate_variability")
            )
        )
        assert len(rows) == 1
        assert rows[0].value == 77.7
        assert (
            rows[0].source == "Apple Watch"
        )  # missing newer-export provenance must not erase older provenance
        job = session.get(IngestionRequest, job_id)
        assert job is not None
        assert job.records_updated >= 1
