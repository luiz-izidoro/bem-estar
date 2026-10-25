from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy.orm import Session

from bemestar.application.metric_registry import active_version
from bemestar.application.repositories import Repository


class DashboardService:
    def __init__(self, session: Session):
        self.repo = Repository(session)

    def day_summary(self, day: date) -> dict[str, object]:
        d = day.isoformat()
        derived: dict[str, float | None] = {}
        versions: dict[str, str] = {}
        components: dict[str, object] = {}
        for row in self.repo.derived_for_day(d):
            if row.scope_type != "day":
                continue
            expected_version = active_version(row.metric_name)
            if expected_version is not None and row.algorithm_version != expected_version:
                continue
            derived[row.metric_name] = row.value
            versions[row.metric_name] = row.algorithm_version
            try:
                components[row.metric_name] = json.loads(row.components_json)
            except json.JSONDecodeError:
                components[row.metric_name] = {}
        raw = {}
        for metric in (
            "heart_rate_variability",
            "resting_heart_rate",
            "vo2_max",
            "body_fat_percentage",
            "step_count",
            "active_energy",
        ):
            raw[metric] = self.repo.latest_numeric_for_day(metric, d)
        # HAE currently documents the weight metric as `weight_&_body_mass`; retain
        # aliases for historical exporters without mutating canonical metric names.
        weight = None
        for alias in ("weight_&_body_mass", "weight_body_mass", "body_mass"):
            weight = self.repo.latest_numeric_for_day(alias, d)
            if weight is not None:
                break
        raw["weight_body_mass"] = weight
        workouts = self.repo.workouts_between(d, d)
        return {
            "date": d,
            "derived": derived,
            "raw": raw,
            "versions": versions,
            "components": components,
            "workouts": [
                {
                    "id": w.external_id,
                    "name": w.name,
                    "start": w.start_utc,
                    "duration_seconds": w.duration_seconds,
                    "distance_km": w.distance_km,
                    "avg_hr": w.avg_hr,
                }
                for w in workouts
            ],
        }

    def metric_history(
        self, metric: str, days: int, end: date | None = None
    ) -> list[dict[str, object]]:
        end = end or date.today()
        start = end - timedelta(days=max(1, days) - 1)
        derived = self.repo.derived(
            metric, start.isoformat(), end.isoformat(), version=active_version(metric)
        )
        if derived:
            return [
                {
                    "date": x.local_date,
                    "value": x.value,
                    "unit": x.unit,
                    "version": x.algorithm_version,
                }
                for x in derived
                if x.scope_type == "day"
            ]
        raw = self.repo.metric_values(metric, start.isoformat(), end.isoformat())
        return [
            {"date": x.local_date, "timestamp": x.timestamp_utc, "value": x.value, "unit": x.unit}
            for x in raw
        ]
