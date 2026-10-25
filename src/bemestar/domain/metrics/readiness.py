from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from statistics import median


@dataclass(frozen=True, slots=True)
class ScoreComponent:
    name: str
    score: float
    weight: float
    raw: float | None = None
    baseline: float | None = None


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def robust_score(
    value: float, history: Iterable[float], inverse: bool = False
) -> tuple[float, float | None]:
    values = [float(v) for v in history if v is not None]
    if len(values) < 7:
        return 50.0, median(values) if values else None
    base = median(values)
    deviations = [abs(v - base) for v in values]
    mad = median(deviations) or max(abs(base) * 0.05, 1e-6)
    z = (value - base) / (1.4826 * mad)
    if inverse:
        z *= -1
    return clamp(50.0 + 15.0 * z), base


def sleep_duration_score(hours: float, target_hours: float) -> float:
    # Intentionally transparent, not a clinical model.
    return clamp(100.0 - abs(hours - target_hours) * 18.0)


def sleep_efficiency_score(asleep_hours: float, in_bed_hours: float) -> float | None:
    if in_bed_hours <= 0:
        return None
    efficiency = 100.0 * asleep_hours / in_bed_hours
    return clamp((efficiency - 65.0) / 0.30)


def training_balance_score(tsb: float) -> float:
    # A small positive balance is treated as optimal for readiness; extreme positive/negative values lose points.
    return clamp(100.0 - abs(tsb - 5.0) * 2.2)


def weighted_score(components: Iterable[ScoreComponent]) -> float | None:
    parts = [c for c in components if c.score is not None and c.weight > 0]
    if not parts:
        return None
    total_weight = sum(c.weight for c in parts)
    return sum(c.score * c.weight for c in parts) / total_weight
