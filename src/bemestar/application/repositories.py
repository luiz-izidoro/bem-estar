from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from statistics import median
from typing import Any, cast

from sqlalchemy import Select, func, select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from bemestar.domain.entities import CanonicalHealthSample, CanonicalWorkout
from bemestar.infrastructure.models import (
    DerivedMetric,
    HealthSample,
    IngestionRequest,
    UserProfile,
    Workout,
    WorkoutSample,
    utcnow_iso,
)


class Repository:
    def __init__(self, session: Session):
        self.session = session

    def get_ingestion_by_key(self, key: str) -> IngestionRequest | None:
        return self.session.scalar(
            select(IngestionRequest).where(IngestionRequest.idempotency_key == key)
        )

    def recent_ingestions(self, limit: int = 20) -> list[IngestionRequest]:
        return list(
            self.session.scalars(
                select(IngestionRequest).order_by(IngestionRequest.received_at.desc()).limit(limit)
            )
        )

    def claim_next_ingestion(self, lease_seconds: int = 900) -> IngestionRequest | None:
        """Atomically claim one pending job and recover stale processing leases.

        SQLite serializes the short write transaction, which is sufficient for this
        personal single-host deployment and remains safe if a second worker is started.
        """
        stale_before = (datetime.now(UTC) - timedelta(seconds=lease_seconds)).isoformat()
        self.session.execute(
            update(IngestionRequest)
            .where(
                IngestionRequest.status == "processing",
                IngestionRequest.processing_started_at.is_not(None),
                IngestionRequest.processing_started_at < stale_before,
            )
            .values(
                status="pending",
                processing_started_at=None,
                error="recovered stale processing lease",
            )
        )
        candidate = self.session.scalar(
            select(IngestionRequest.id)
            .where(IngestionRequest.status == "pending")
            .order_by(IngestionRequest.received_at)
            .limit(1)
        )
        if candidate is None:
            self.session.commit()
            return None
        started = utcnow_iso()
        result = self.session.execute(
            update(IngestionRequest)
            .where(IngestionRequest.id == candidate, IngestionRequest.status == "pending")
            .values(status="processing", processing_started_at=started)
        )
        self.session.commit()
        if not cast(CursorResult[Any], result).rowcount:
            return None
        return self.session.get(IngestionRequest, candidate)

    def insert_health_samples(
        self, samples: list[CanonicalHealthSample], ingestion_id: str
    ) -> tuple[int, int, int]:
        """Upsert logical sample slots and return inserted/updated/ignored counts.

        `sample_hash` intentionally excludes provenance and value so a reconciliation
        can correct a value in-place (and iOS 27 source omission does not duplicate it).
        """
        if not samples:
            return 0, 0, 0
        # HAE may theoretically emit more than one provenance row for the same
        # canonical slot. Collapse the request deterministically before touching
        # the unique index; the last payload occurrence wins.
        original_count = len(samples)
        samples = list({item.sample_hash: item for item in samples}.values())
        in_batch_duplicates = original_count - len(samples)
        hashes = [item.sample_hash for item in samples]
        existing: dict[str, HealthSample] = {}
        for offset in range(0, len(hashes), 800):
            chunk = hashes[offset : offset + 800]
            rows = self.session.scalars(
                select(HealthSample).where(HealthSample.sample_hash.in_(chunk))
            )
            existing.update({row.sample_hash: row for row in rows})

        inserted = updated = 0
        ignored = in_batch_duplicates
        for item in samples:
            metadata_json = json.dumps(item.metadata, separators=(",", ":"), ensure_ascii=False)
            row = existing.get(item.sample_hash)
            if row is None:
                self.session.add(
                    HealthSample(
                        sample_hash=item.sample_hash,
                        metric_name=item.metric_name,
                        timestamp_utc=item.timestamp_utc,
                        end_timestamp_utc=item.end_timestamp_utc,
                        local_date=item.local_date,
                        value=item.value,
                        text_value=item.text_value,
                        unit=item.unit,
                        source=item.source,
                        metadata_json=metadata_json,
                        ingestion_id=ingestion_id,
                    )
                )
                inserted += 1
                continue

            new_values = {
                "metric_name": item.metric_name,
                "timestamp_utc": item.timestamp_utc,
                "end_timestamp_utc": item.end_timestamp_utc,
                "local_date": item.local_date,
                "value": item.value,
                "text_value": item.text_value,
                "unit": item.unit,
                "source": item.source if item.source is not None else row.source,
                "metadata_json": metadata_json,
            }
            changed = any(getattr(row, key) != value for key, value in new_values.items())
            if changed:
                for key, value in new_values.items():
                    setattr(row, key, value)
                row.ingestion_id = ingestion_id
                updated += 1
            else:
                ignored += 1
        self.session.flush()
        return inserted, updated, ignored

    def upsert_workout(
        self, workout: CanonicalWorkout, ingestion_id: str
    ) -> tuple[Workout, str, int, int, int]:
        payload = {
            "external_id": workout.external_id,
            "name": workout.name,
            "start_utc": workout.start_utc,
            "end_utc": workout.end_utc,
            "local_date": workout.local_date,
            "duration_seconds": workout.duration_seconds,
            "location": workout.location,
            "is_indoor": None if workout.is_indoor is None else int(workout.is_indoor),
            "active_energy_kcal": workout.active_energy_kcal,
            "total_energy_kcal": workout.total_energy_kcal,
            "distance_km": workout.distance_km,
            "avg_hr": workout.avg_hr,
            "max_hr": workout.max_hr,
            "metadata_json": json.dumps(
                workout.metadata, separators=(",", ":"), ensure_ascii=False
            ),
            "ingestion_id": ingestion_id,
        }
        existing = self.session.scalar(
            select(Workout).where(Workout.external_id == workout.external_id)
        )
        if existing is None:
            existing = Workout(**payload)
            self.session.add(existing)
            self.session.flush()
            workout_status = "inserted"
        else:
            comparison = {
                k: v for k, v in payload.items() if k not in {"external_id", "ingestion_id"}
            }
            changed = any(getattr(existing, key) != value for key, value in comparison.items())
            if changed:
                for key, value in payload.items():
                    if key != "external_id":
                        setattr(existing, key, value)
                workout_status = "updated"
            else:
                workout_status = "ignored"
            self.session.flush()

        incoming_samples = list({sample.sample_hash: sample for sample in workout.samples}.values())
        sample_inserted = sample_updated = 0
        sample_ignored = len(workout.samples) - len(incoming_samples)
        hashes = [sample.sample_hash for sample in incoming_samples]
        existing_samples: dict[str, WorkoutSample] = {}
        for offset in range(0, len(hashes), 800):
            chunk = hashes[offset : offset + 800]
            if not chunk:
                continue
            rows = self.session.scalars(
                select(WorkoutSample).where(WorkoutSample.sample_hash.in_(chunk))
            )
            existing_samples.update({row.sample_hash: row for row in rows})
        for sample in incoming_samples:
            metadata_json = json.dumps(sample.metadata, separators=(",", ":"), ensure_ascii=False)
            row = existing_samples.get(sample.sample_hash)
            if row is None:
                self.session.add(
                    WorkoutSample(
                        sample_hash=sample.sample_hash,
                        workout_id=existing.id,
                        metric_name=sample.metric_name,
                        timestamp_utc=sample.timestamp_utc,
                        value=sample.value,
                        min_value=sample.min_value,
                        avg_value=sample.avg_value,
                        max_value=sample.max_value,
                        unit=sample.unit,
                        source=sample.source,
                        metadata_json=metadata_json,
                    )
                )
                sample_inserted += 1
                continue
            new_values = {
                "workout_id": existing.id,
                "metric_name": sample.metric_name,
                "timestamp_utc": sample.timestamp_utc,
                "value": sample.value,
                "min_value": sample.min_value,
                "avg_value": sample.avg_value,
                "max_value": sample.max_value,
                "unit": sample.unit,
                "source": sample.source if sample.source is not None else row.source,
                "metadata_json": metadata_json,
            }
            changed = any(getattr(row, key) != value for key, value in new_values.items())
            if changed:
                for key, value in new_values.items():
                    setattr(row, key, value)
                sample_updated += 1
            else:
                sample_ignored += 1
        self.session.flush()
        return existing, workout_status, sample_inserted, sample_updated, sample_ignored

    def metric_values(self, metric: str, start_date: str, end_date: str) -> list[HealthSample]:
        stmt = (
            select(HealthSample)
            .where(
                HealthSample.metric_name == metric,
                HealthSample.local_date >= start_date,
                HealthSample.local_date <= end_date,
            )
            .order_by(HealthSample.timestamp_utc)
        )
        return list(self.session.scalars(stmt))

    def earliest_metric_date(self, metrics: tuple[str, ...]) -> str | None:
        return self.session.scalar(
            select(func.min(HealthSample.local_date)).where(HealthSample.metric_name.in_(metrics))
        )

    def workouts_between(self, start_date: str, end_date: str) -> list[Workout]:
        stmt = (
            select(Workout)
            .where(Workout.local_date >= start_date, Workout.local_date <= end_date)
            .order_by(Workout.start_utc)
        )
        return list(self.session.scalars(stmt))

    def earliest_workout_date(self) -> str | None:
        return self.session.scalar(select(func.min(Workout.local_date)))

    def upsert_derived(
        self,
        metric_name: str,
        algorithm_version: str,
        local_date: str,
        value: float | None,
        unit: str | None,
        components: dict[str, object],
        inputs_hash: str = "",
        scope_type: str = "day",
        scope_id: str = "",
    ) -> None:
        payload = {
            "metric_name": metric_name,
            "algorithm_version": algorithm_version,
            "local_date": local_date,
            "scope_type": scope_type,
            "scope_id": scope_id,
            "value": value,
            "unit": unit,
            "components_json": json.dumps(components, separators=(",", ":"), ensure_ascii=False),
            "inputs_hash": inputs_hash,
            "computed_at": utcnow_iso(),
        }
        stmt = (
            sqlite_insert(DerivedMetric)
            .values(**payload)
            .on_conflict_do_update(
                index_elements=[
                    DerivedMetric.metric_name,
                    DerivedMetric.algorithm_version,
                    DerivedMetric.local_date,
                    DerivedMetric.scope_type,
                    DerivedMetric.scope_id,
                ],
                set_={
                    k: v
                    for k, v in payload.items()
                    if k
                    not in {
                        "metric_name",
                        "algorithm_version",
                        "local_date",
                        "scope_type",
                        "scope_id",
                    }
                },
            )
        )
        self.session.execute(stmt)

    def derived(
        self, metric: str, start_date: str, end_date: str, version: str | None = None
    ) -> list[DerivedMetric]:
        stmt: Select[Any] = select(DerivedMetric).where(
            DerivedMetric.metric_name == metric,
            DerivedMetric.local_date >= start_date,
            DerivedMetric.local_date <= end_date,
        )
        if version:
            stmt = stmt.where(DerivedMetric.algorithm_version == version)
        return list(self.session.scalars(stmt.order_by(DerivedMetric.local_date)))

    def derived_for_day(self, day: str) -> list[DerivedMetric]:
        return list(
            self.session.scalars(
                select(DerivedMetric)
                .where(DerivedMetric.local_date == day)
                .order_by(DerivedMetric.metric_name)
            )
        )

    def profile(self) -> UserProfile:
        profile = self.session.get(UserProfile, 1)
        if profile is None:
            profile = UserProfile(id=1)
            self.session.add(profile)
            self.session.flush()
        return profile

    def latest_numeric_for_day(self, metric: str, day: str) -> float | None:
        values = [s.value for s in self.metric_values(metric, day, day) if s.value is not None]
        return float(median(values)) if values else None
