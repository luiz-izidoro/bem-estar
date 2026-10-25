from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from bemestar.adapters.hae.parser import HAEParser
from bemestar.adapters.hae.raw_store import RawStore
from bemestar.application.metrics_service import MetricsService
from bemestar.application.repositories import Repository
from bemestar.infrastructure.config import Settings
from bemestar.infrastructure.models import IngestionRequest

logger = logging.getLogger(__name__)


class IngestionProcessor:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings
        self.repo = Repository(session)
        self.raw = RawStore(settings.raw_dir)
        self.parser = HAEParser(settings.timezone)

    def process(self, ingestion: IngestionRequest) -> None:
        """Process a job that has already been claimed by the worker."""
        try:
            raw_bytes = self.raw.read(ingestion.raw_path)
            payload = json.loads(raw_bytes)
            batch = self.parser.parse(payload)

            inserted, updated, ignored = self.repo.insert_health_samples(
                list(batch.health_samples), ingestion.id
            )
            workout_created = 0
            workout_updated = 0
            workout_samples_inserted = 0
            workout_samples_updated = 0
            workout_samples_ignored = 0
            for workout in batch.workouts:
                _, workout_status, ws_inserted, ws_updated, ws_ignored = self.repo.upsert_workout(
                    workout, ingestion.id
                )
                workout_created += int(workout_status == "inserted")
                workout_updated += int(workout_status == "updated")
                if workout_status == "ignored":
                    workout_samples_ignored += 1
                workout_samples_inserted += ws_inserted
                workout_samples_updated += ws_updated
                workout_samples_ignored += ws_ignored

            ingestion.records_received = batch.record_count
            ingestion.records_inserted = inserted + workout_created + workout_samples_inserted
            ingestion.records_updated = updated + workout_updated + workout_samples_updated
            ingestion.records_ignored = ignored + workout_samples_ignored
            self.session.flush()

            affected_dates: list[date] = []
            affected_dates.extend(
                date.fromisoformat(sample.local_date) for sample in batch.health_samples
            )
            affected_dates.extend(
                date.fromisoformat(workout.local_date) for workout in batch.workouts
            )
            local_today = datetime.now(ZoneInfo(self.settings.timezone)).date()
            affected_from = min(affected_dates) if affected_dates else local_today
            MetricsService(self.session).recompute_all(
                through=local_today,
                affected_from=affected_from,
            )

            ingestion.status = "processed"
            ingestion.processed_at = datetime.now(UTC).isoformat()
            ingestion.error = None
            self.session.commit()
            logger.info(
                "ingestion processed",
                extra={
                    "ingestion_id": ingestion.id,
                    "inserted": ingestion.records_inserted,
                    "updated": ingestion.records_updated,
                    "ignored": ingestion.records_ignored,
                    "affected_from": affected_from.isoformat(),
                },
            )
        except Exception as exc:
            self.session.rollback()
            failed = self.session.get(IngestionRequest, ingestion.id)
            if failed:
                failed.status = "failed"
                failed.error = f"{type(exc).__name__}: {exc}"[:2000]
                failed.processed_at = datetime.now(UTC).isoformat()
                self.session.commit()
            logger.exception("ingestion failed", extra={"ingestion_id": ingestion.id})
            raise
