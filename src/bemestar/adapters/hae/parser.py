from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from bemestar.domain.entities import (
    CanonicalHealthSample,
    CanonicalWorkout,
    CanonicalWorkoutSample,
    IngestionBatch,
)


def _hash(parts: dict[str, Any]) -> str:
    encoded = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def parse_datetime(value: str, timezone: ZoneInfo) -> datetime:
    text = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z"):
        try:
            return datetime.strptime(text, fmt).astimezone(UTC)
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone)
        return parsed.astimezone(UTC)
    except ValueError as exc:
        raise ValueError(f"Unsupported HAE datetime: {value!r}") from exc


def _local_date_for(point: dict[str, Any], timezone: ZoneInfo, metric_name: str = "") -> str:
    # Sleep belongs to the waking day. This avoids splitting one overnight sleep
    # session across two calendar days when HAE sends unaggregated sleep stages.
    if metric_name == "sleep_analysis":
        sleep_end = point.get("sleepEnd") or point.get("endDate")
        if isinstance(sleep_end, str) and len(sleep_end) > 10:
            return parse_datetime(sleep_end, timezone).astimezone(timezone).date().isoformat()
    date_only = point.get("date")
    if isinstance(date_only, str) and len(date_only) == 10:
        return date_only
    candidate = (
        point.get("date") or point.get("startDate") or point.get("sleepEnd") or point.get("endDate")
    )
    if isinstance(candidate, str):
        return parse_datetime(candidate, timezone).astimezone(timezone).date().isoformat()
    return datetime.now(timezone).date().isoformat()


def _point_timestamp(point: dict[str, Any], timezone: ZoneInfo) -> tuple[str, str | None]:
    start = point.get("date") or point.get("startDate") or point.get("sleepStart")
    end = point.get("endDate") or point.get("sleepEnd")
    if isinstance(start, str) and len(start) == 10:
        dt = datetime.combine(
            datetime.fromisoformat(start).date(), time(hour=12), tzinfo=timezone
        ).astimezone(UTC)
    elif isinstance(start, str):
        dt = parse_datetime(start, timezone)
    elif isinstance(end, str):
        dt = parse_datetime(end, timezone)
    else:
        dt = datetime.now(UTC)
    end_iso = (
        parse_datetime(end, timezone).isoformat()
        if isinstance(end, str) and len(end) > 10
        else None
    )
    return dt.isoformat(), end_iso


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _quantity(obj: Any, unit: str) -> float | None:
    if not isinstance(obj, dict):
        return _number(obj)
    qty = _number(obj.get("qty"))
    if qty is None:
        return None
    src_unit = str(obj.get("units") or unit or "")
    if src_unit == "mi" and unit == "km":
        return qty * 1.609344
    if src_unit == "ft" and unit == "m":
        return qty * 0.3048
    return qty


def _distance_km(obj: Any) -> float | None:
    if not isinstance(obj, dict):
        return _number(obj)
    qty = _number(obj.get("qty"))
    if qty is None:
        return None
    units = obj.get("units")
    if units == "mi":
        return qty * 1.609344
    if units in {"m", "meter", "meters"}:
        return qty / 1000.0
    return qty


def _energy_kcal(obj: Any) -> float | None:
    if not isinstance(obj, dict):
        return _number(obj)
    qty = _number(obj.get("qty"))
    if qty is None:
        return None
    units = str(obj.get("units") or "kcal").lower()
    if units in {"kj", "kilojoule", "kilojoules"}:
        return qty / 4.184
    return qty


class HAEParser:
    def __init__(self, timezone_name: str):
        self.timezone = ZoneInfo(timezone_name)

    def parse(self, payload: dict[str, Any]) -> IngestionBatch:
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ValueError("HAE payload must contain a data object")
        samples: list[CanonicalHealthSample] = []
        workouts: list[CanonicalWorkout] = []
        for metric in data.get("metrics") or []:
            if isinstance(metric, dict):
                samples.extend(self._parse_metric(metric))
        for workout in data.get("workouts") or []:
            if isinstance(workout, dict):
                workouts.append(self._parse_workout(workout))
        return IngestionBatch(tuple(samples), tuple(workouts))

    def _parse_metric(self, metric: dict[str, Any]) -> list[CanonicalHealthSample]:
        name = str(metric.get("name") or "unknown_metric")
        unit = str(metric.get("units")) if metric.get("units") is not None else None
        result: list[CanonicalHealthSample] = []
        for point in metric.get("data") or []:
            if not isinstance(point, dict):
                continue
            timestamp, end_timestamp = _point_timestamp(point, self.timezone)
            local_date = _local_date_for(point, self.timezone, name)
            value = _number(point.get("qty"))
            if value is None:
                value = _number(point.get("Avg"))
            if value is None and name == "sleep_analysis":
                value = _number(point.get("totalSleep")) or _number(point.get("asleep"))
            text_value = str(point.get("value")) if point.get("value") is not None else None
            source = str(point.get("source")) if point.get("source") is not None else None
            canonical: dict[str, Any] = {
                "metric_name": name,
                "timestamp_utc": timestamp,
                "end_timestamp_utc": end_timestamp,
                "local_date": local_date,
                "value": value,
                "text_value": text_value,
                "unit": unit,
                "source": source,
                "metadata": point,
            }
            identity = {
                "metric_name": name,
                "timestamp_utc": timestamp,
                "end_timestamp_utc": end_timestamp,
                "unit": unit,
            }
            result.append(CanonicalHealthSample(sample_hash=_hash(identity), **canonical))
        return result

    def _parse_workout(self, item: dict[str, Any]) -> CanonicalWorkout:
        start_raw = str(item["start"])
        end_raw = str(item["end"])
        start = parse_datetime(start_raw, self.timezone)
        end = parse_datetime(end_raw, self.timezone)
        external_id = str(
            item.get("id") or _hash({"name": item.get("name"), "start": start_raw, "end": end_raw})
        )
        avg_hr = (
            _number((item.get("avgHeartRate") or {}).get("qty"))
            if isinstance(item.get("avgHeartRate"), dict)
            else None
        )
        max_hr = (
            _number((item.get("maxHeartRate") or {}).get("qty"))
            if isinstance(item.get("maxHeartRate"), dict)
            else None
        )
        heart_rate = item.get("heartRate")
        if isinstance(heart_rate, dict):
            if avg_hr is None and isinstance(heart_rate.get("avg"), dict):
                avg_hr = _number(heart_rate["avg"].get("qty"))
            if max_hr is None and isinstance(heart_rate.get("max"), dict):
                max_hr = _number(heart_rate["max"].get("qty"))
        duration = _number(item.get("duration"))
        if duration is None:
            duration = max(0.0, (end - start).total_seconds())
        samples: list[CanonicalWorkoutSample] = []
        skip_arrays = {"route"}
        for key, value in item.items():
            if key in skip_arrays or not isinstance(value, list):
                continue
            for point in value:
                if not isinstance(point, dict):
                    continue
                date_value = point.get("date") or point.get("timestamp")
                if not isinstance(date_value, str):
                    continue
                ts = parse_datetime(date_value, self.timezone).isoformat()
                sample_dict: dict[str, Any] = {
                    "metric_name": key,
                    "timestamp_utc": ts,
                    "value": _number(point.get("qty")),
                    "min_value": _number(point.get("Min")),
                    "avg_value": _number(point.get("Avg")),
                    "max_value": _number(point.get("Max")),
                    "unit": str(point.get("units")) if point.get("units") is not None else None,
                    "source": str(point.get("source")) if point.get("source") is not None else None,
                    "metadata": point,
                }
                sample_identity = {
                    "workout": external_id,
                    "metric_name": key,
                    "timestamp_utc": ts,
                    "unit": sample_dict["unit"],
                }
                samples.append(
                    CanonicalWorkoutSample(sample_hash=_hash(sample_identity), **sample_dict)
                )
        # Time-series arrays are stored canonically as workout_samples; keeping them again
        # in metadata would roughly double storage for high-frequency workout exports.
        metadata = {k: v for k, v in item.items() if not isinstance(v, list) and k != "route"}
        return CanonicalWorkout(
            external_id=external_id,
            name=str(item.get("name") or "Unknown"),
            start_utc=start.isoformat(),
            end_utc=end.isoformat(),
            local_date=start.astimezone(self.timezone).date().isoformat(),
            duration_seconds=duration,
            location=str(item.get("location")) if item.get("location") is not None else None,
            is_indoor=item.get("isIndoor") if isinstance(item.get("isIndoor"), bool) else None,
            active_energy_kcal=_energy_kcal(
                item.get("activeEnergyBurned") or item.get("activeEnergy")
            ),
            total_energy_kcal=_energy_kcal(item.get("totalEnergy")),
            distance_km=_distance_km(item.get("distance")),
            avg_hr=avg_hr,
            max_hr=max_hr,
            metadata=metadata,
            samples=tuple(samples),
        )
