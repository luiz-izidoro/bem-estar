from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bemestar.infrastructure.db import Base


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


class IngestionRequest(Base):
    __tablename__ = "ingestion_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    automation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    automation_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    automation_period: Mapped[str | None] = mapped_column(String(100), nullable=True)
    automation_aggregation: Mapped[str | None] = mapped_column(String(100), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stream: Mapped[str] = mapped_column(String(50), index=True)
    received_at: Mapped[str] = mapped_column(String(40), default=utcnow_iso, index=True)
    processing_started_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    processed_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload_size: Mapped[int] = mapped_column(Integer)
    raw_path: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_ignored: Mapped[int] = mapped_column(Integer, default=0)


class HealthSample(Base):
    __tablename__ = "health_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), index=True)
    timestamp_utc: Mapped[str] = mapped_column(String(40), index=True)
    end_timestamp_utc: Mapped[str | None] = mapped_column(String(40), nullable=True)
    local_date: Mapped[str] = mapped_column(String(10), index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    text_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    ingestion_id: Mapped[str] = mapped_column(ForeignKey("ingestion_requests.id"), index=True)

    __table_args__ = (Index("ix_health_metric_date", "metric_name", "local_date"),)


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    start_utc: Mapped[str] = mapped_column(String(40), index=True)
    end_utc: Mapped[str] = mapped_column(String(40))
    local_date: Mapped[str] = mapped_column(String(10), index=True)
    duration_seconds: Mapped[float] = mapped_column(Float)
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_indoor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active_energy_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_energy_kcal: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    ingestion_id: Mapped[str] = mapped_column(ForeignKey("ingestion_requests.id"), index=True)

    samples: Mapped[list[WorkoutSample]] = relationship(
        back_populates="workout", cascade="all, delete-orphan"
    )


class WorkoutSample(Base):
    __tablename__ = "workout_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    workout_id: Mapped[int] = mapped_column(
        ForeignKey("workouts.id", ondelete="CASCADE"), index=True
    )
    metric_name: Mapped[str] = mapped_column(String(100), index=True)
    timestamp_utc: Mapped[str] = mapped_column(String(40), index=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")

    workout: Mapped[Workout] = relationship(back_populates="samples")


class DerivedMetric(Base):
    __tablename__ = "derived_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(100), index=True)
    algorithm_version: Mapped[str] = mapped_column(String(100), index=True)
    local_date: Mapped[str] = mapped_column(String(10), index=True)
    scope_type: Mapped[str] = mapped_column(String(30), default="day")
    scope_id: Mapped[str] = mapped_column(String(255), default="")
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    components_json: Mapped[str] = mapped_column(Text, default="{}")
    inputs_hash: Mapped[str] = mapped_column(String(64), default="")
    computed_at: Mapped[str] = mapped_column(String(40), default=utcnow_iso)

    __table_args__ = (
        UniqueConstraint(
            "metric_name",
            "algorithm_version",
            "local_date",
            "scope_type",
            "scope_id",
            name="uq_derived_metric_version_scope",
        ),
        Index("ix_derived_name_date", "metric_name", "local_date"),
    )


class UserProfile(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    hr_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    hr_rest: Mapped[float | None] = mapped_column(Float, nullable=True)
    trimp_exponential_coefficient: Mapped[float] = mapped_column(Float, default=1.92)
    target_sleep_hours: Mapped[float] = mapped_column(Float, default=8.0)
    locale: Mapped[str] = mapped_column(String(20), default="pt-BR")
    updated_at: Mapped[str] = mapped_column(String(40), default=utcnow_iso)
