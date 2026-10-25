from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from bemestar.application.metric_registry import GROUP_VERSIONS, active_version
from bemestar.application.repositories import Repository
from bemestar.domain.metrics.readiness import (
    ScoreComponent,
    robust_score,
    sleep_duration_score,
    sleep_efficiency_score,
    training_balance_score,
    weighted_score,
)
from bemestar.domain.metrics.training import banister_trimp, training_load_series


def _input_hash(data: object) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str, separators=(",", ":")).encode()
    ).hexdigest()


class MetricsService:
    def __init__(self, session: Session):
        self.repo = Repository(session)
        self.session = session

    def recompute_all(
        self, through: date | None = None, affected_from: date | None = None
    ) -> dict[str, int]:
        """Recompute deterministic metrics.

        Training state is evaluated from the earliest relevant source date so CTL/ATL
        remain mathematically stable, but only dates at/after `affected_from` are
        rewritten when an ingestion tells us where data changed.
        """
        through = through or date.today()
        candidates: list[date] = []
        earliest_workout = self.repo.earliest_workout_date()
        if earliest_workout:
            candidates.append(date.fromisoformat(earliest_workout))
        earliest_sample = self.repo.earliest_metric_date(
            ("heart_rate_variability", "resting_heart_rate", "sleep_analysis")
        )
        if earliest_sample:
            candidates.append(date.fromisoformat(earliest_sample))
        origin = min(candidates) if candidates else through - timedelta(days=90)
        write_from = max(origin, affected_from) if affected_from else origin
        if write_from > through:
            write_from = through

        daily_loads = self._compute_workout_trimp(origin, through, persist_from=write_from)
        training_points = training_load_series(daily_loads, origin, through)
        persisted_training_days = 0
        for point in training_points:
            if point.day < write_from:
                continue
            persisted_training_days += 1
            d = point.day.isoformat()
            common_hash = _input_hash(
                {
                    "day": d,
                    "load": point.load,
                    "ctl": point.ctl,
                    "atl": point.atl,
                    "tsb": point.tsb,
                    "acwr": point.acwr,
                    "ctl_tau": 42,
                    "atl_tau": 7,
                    "acwr_acute": 7,
                    "acwr_chronic": 28,
                }
            )
            version = GROUP_VERSIONS["training"]
            self.repo.upsert_derived(
                "training_load",
                version,
                d,
                point.load,
                "TRIMP",
                {"source": "daily workout TRIMP"},
                inputs_hash=common_hash,
            )
            self.repo.upsert_derived(
                "ctl", version, d, point.ctl, "TRIMP", {"tau_days": 42}, inputs_hash=common_hash
            )
            self.repo.upsert_derived(
                "atl", version, d, point.atl, "TRIMP", {"tau_days": 7}, inputs_hash=common_hash
            )
            self.repo.upsert_derived(
                "tsb",
                version,
                d,
                point.tsb,
                "TRIMP",
                {"form": "pre-day ctl-atl"},
                inputs_hash=common_hash,
            )
            self.repo.upsert_derived(
                "acwr",
                version,
                d,
                point.acwr,
                "ratio",
                {"acute_days": 7, "chronic_days": 28},
                inputs_hash=common_hash,
            )
        self._compute_sleep_and_readiness(write_from, through)
        self.session.flush()
        return {
            "days": (through - write_from).days + 1,
            "training_days_rewritten": persisted_training_days,
            "workout_days": len(daily_loads),
        }

    def _compute_workout_trimp(
        self, start: date, end: date, persist_from: date
    ) -> dict[date, float]:
        profile = self.repo.profile()
        loads: dict[date, float] = {}
        for workout in self.repo.workouts_between(start.isoformat(), end.isoformat()):
            trimp: float | None = None
            reason = None
            if profile.hr_max and profile.hr_rest and workout.avg_hr:
                trimp = banister_trimp(
                    workout.duration_seconds / 60.0,
                    workout.avg_hr,
                    profile.hr_rest,
                    profile.hr_max,
                    profile.trimp_exponential_coefficient,
                )
                workout_day = date.fromisoformat(workout.local_date)
                loads[workout_day] = loads.get(workout_day, 0.0) + trimp
            else:
                reason = "profile hr_max/hr_rest and workout avg_hr are required"
            if date.fromisoformat(workout.local_date) < persist_from:
                continue
            self.repo.upsert_derived(
                "trimp",
                GROUP_VERSIONS["trimp"],
                workout.local_date,
                trimp,
                "TRIMP",
                {
                    "workout": workout.name,
                    "duration_seconds": workout.duration_seconds,
                    "avg_hr": workout.avg_hr,
                    "reason": reason,
                },
                inputs_hash=_input_hash(
                    [
                        workout.external_id,
                        workout.avg_hr,
                        workout.duration_seconds,
                        profile.hr_max,
                        profile.hr_rest,
                        profile.trimp_exponential_coefficient,
                    ]
                ),
                scope_type="workout",
                scope_id=workout.external_id,
            )
        return loads

    def _history(self, metric: str, day: date, days: int = 28) -> list[float]:
        # One value per calendar day prevents a day with many samples from dominating
        # the baseline merely because the exporter produced higher granularity.
        result: list[float] = []
        current = day - timedelta(days=days)
        while current < day:
            value = self.repo.latest_numeric_for_day(metric, current.isoformat())
            if value is not None:
                result.append(value)
            current += timedelta(days=1)
        return result

    def _sleep_point(self, day: str) -> dict[str, Any] | None:
        candidates = self.repo.metric_values("sleep_analysis", day, day)
        parsed: list[dict[str, Any]] = []
        for sample in candidates:
            try:
                parsed.append(json.loads(sample.metadata_json))
            except json.JSONDecodeError:
                continue
        if not parsed:
            return None
        return max(
            parsed,
            key=lambda point: float(
                point.get("totalSleep") or point.get("asleep") or point.get("qty") or 0.0
            ),
        )

    def _derived_value(self, metric: str, day: str) -> float | None:
        rows = self.repo.derived(metric, day, day, version=active_version(metric))
        day_rows = [row for row in rows if row.scope_type == "day"]
        return day_rows[-1].value if day_rows else None

    def _compute_sleep_and_readiness(self, start: date, end: date) -> None:
        profile = self.repo.profile()
        current = start
        while current <= end:
            d = current.isoformat()
            hrv = self.repo.latest_numeric_for_day("heart_rate_variability", d)
            rhr = self.repo.latest_numeric_for_day("resting_heart_rate", d)
            sleep = self._sleep_point(d)
            sleep_hours = None
            asleep = None
            in_bed = None
            if sleep:
                sleep_hours = float(
                    sleep.get("totalSleep") or sleep.get("asleep") or sleep.get("qty") or 0.0
                )
                asleep = float(sleep.get("asleep") or sleep_hours)
                in_bed = float(sleep.get("inBed") or asleep)
            sleep_hash = _input_hash(
                {"day": d, "sleep": sleep, "target": profile.target_sleep_hours}
            )
            self.repo.upsert_derived(
                "sleep_hours",
                GROUP_VERSIONS["sleep"],
                d,
                sleep_hours,
                "h",
                sleep or {},
                inputs_hash=sleep_hash,
            )
            efficiency = (
                sleep_efficiency_score(asleep, in_bed)
                if asleep is not None and in_bed is not None
                else None
            )
            self.repo.upsert_derived(
                "sleep_efficiency_score",
                GROUP_VERSIONS["sleep"],
                d,
                efficiency,
                "score",
                {"asleep": asleep, "in_bed": in_bed},
                inputs_hash=sleep_hash,
            )

            recovery_parts: list[ScoreComponent] = []
            readiness_parts: list[ScoreComponent] = []
            if hrv is not None:
                score, baseline = robust_score(
                    hrv, self._history("heart_rate_variability", current), inverse=False
                )
                recovery_parts.append(ScoreComponent("hrv", score, 0.40, hrv, baseline))
                readiness_parts.append(ScoreComponent("hrv", score, 0.30, hrv, baseline))
            if rhr is not None:
                score, baseline = robust_score(
                    rhr, self._history("resting_heart_rate", current), inverse=True
                )
                recovery_parts.append(ScoreComponent("resting_hr", score, 0.25, rhr, baseline))
                readiness_parts.append(ScoreComponent("resting_hr", score, 0.15, rhr, baseline))
            if sleep_hours is not None:
                duration_score = sleep_duration_score(sleep_hours, profile.target_sleep_hours)
                recovery_parts.append(
                    ScoreComponent(
                        "sleep_duration",
                        duration_score,
                        0.35,
                        sleep_hours,
                        profile.target_sleep_hours,
                    )
                )
                readiness_parts.append(
                    ScoreComponent(
                        "sleep_duration",
                        duration_score,
                        0.25,
                        sleep_hours,
                        profile.target_sleep_hours,
                    )
                )
            if efficiency is not None:
                readiness_parts.append(
                    ScoreComponent("sleep_efficiency", efficiency, 0.10, efficiency, None)
                )
            tsb = self._derived_value("tsb", d)
            if tsb is not None:
                readiness_parts.append(
                    ScoreComponent("training_balance", training_balance_score(tsb), 0.20, tsb, 5.0)
                )

            recovery = weighted_score(recovery_parts)
            recovery_confidence = 100.0 * sum(part.weight for part in recovery_parts)
            morning = weighted_score(readiness_parts)
            readiness_confidence = 100.0 * sum(part.weight for part in readiness_parts)
            live = morning
            todays_load = self._derived_value("training_load", d)
            ctl = self._derived_value("ctl", d)
            penalty = 0.0
            if live is not None and todays_load and ctl is not None:
                penalty = min(20.0, 10.0 * todays_load / max(ctl, 10.0))
                live = max(0.0, live - penalty)

            def parts_payload(parts: list[ScoreComponent]) -> list[dict[str, Any]]:
                return [
                    {
                        "name": part.name,
                        "score": round(part.score, 2),
                        "weight": part.weight,
                        "raw": part.raw,
                        "baseline": part.baseline,
                    }
                    for part in parts
                ]

            recovery_payload = {
                "components": parts_payload(recovery_parts),
                "confidence": recovery_confidence,
            }
            readiness_payload = {
                "components": parts_payload(readiness_parts),
                "hrv": hrv,
                "rhr": rhr,
                "sleep_hours": sleep_hours,
                "efficiency": efficiency,
                "tsb": tsb,
            }
            self.repo.upsert_derived(
                "recovery",
                GROUP_VERSIONS["recovery"],
                d,
                recovery,
                "score",
                recovery_payload,
                inputs_hash=_input_hash(recovery_payload),
            )
            self.repo.upsert_derived(
                "recovery_confidence",
                GROUP_VERSIONS["recovery"],
                d,
                recovery_confidence,
                "%",
                {"available_weight": recovery_confidence / 100.0},
                inputs_hash=_input_hash(recovery_payload),
            )
            self.repo.upsert_derived(
                "readiness_confidence",
                GROUP_VERSIONS["readiness"],
                d,
                readiness_confidence,
                "%",
                {"available_weight": readiness_confidence / 100.0},
                inputs_hash=_input_hash(readiness_payload),
            )
            self.repo.upsert_derived(
                "readiness_morning",
                GROUP_VERSIONS["readiness"],
                d,
                morning,
                "score",
                {"components": parts_payload(readiness_parts), "mode": "morning"},
                inputs_hash=_input_hash(readiness_payload),
            )
            self.repo.upsert_derived(
                "readiness_live",
                GROUP_VERSIONS["readiness"],
                d,
                live,
                "score",
                {
                    "components": parts_payload(readiness_parts),
                    "mode": "live",
                    "same_day_load_penalty": penalty,
                },
                inputs_hash=_input_hash({**readiness_payload, "penalty": penalty}),
            )
            current += timedelta(days=1)
