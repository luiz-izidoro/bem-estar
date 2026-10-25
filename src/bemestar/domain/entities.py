from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class CanonicalHealthSample:
    sample_hash: str
    metric_name: str
    timestamp_utc: str
    local_date: str
    value: float | None
    unit: str | None
    source: str | None
    end_timestamp_utc: str | None = None
    text_value: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CanonicalWorkoutSample:
    sample_hash: str
    metric_name: str
    timestamp_utc: str
    value: float | None
    min_value: float | None
    avg_value: float | None
    max_value: float | None
    unit: str | None
    source: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CanonicalWorkout:
    external_id: str
    name: str
    start_utc: str
    end_utc: str
    local_date: str
    duration_seconds: float
    location: str | None
    is_indoor: bool | None
    active_energy_kcal: float | None
    total_energy_kcal: float | None
    distance_km: float | None
    avg_hr: float | None
    max_hr: float | None
    metadata: dict[str, Any]
    samples: tuple[CanonicalWorkoutSample, ...] = ()


@dataclass(frozen=True, slots=True)
class IngestionBatch:
    health_samples: tuple[CanonicalHealthSample, ...]
    workouts: tuple[CanonicalWorkout, ...]

    @property
    def record_count(self) -> int:
        return (
            len(self.health_samples)
            + len(self.workouts)
            + sum(len(w.samples) for w in self.workouts)
        )
