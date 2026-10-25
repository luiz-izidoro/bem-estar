from __future__ import annotations

import json
from pathlib import Path

from bemestar.adapters.hae.parser import HAEParser

FIXTURE = Path(__file__).parents[1] / "fixtures" / "hae_v2_sample.json"


def test_parse_hae_v2_metrics_and_workout() -> None:
    payload = json.loads(FIXTURE.read_text())
    batch = HAEParser("America/Sao_Paulo").parse(payload)

    assert len(batch.health_samples) == 5
    hrv = next(x for x in batch.health_samples if x.metric_name == "heart_rate_variability")
    assert hrv.value == 52.4
    assert hrv.local_date == "2026-09-15"

    heart_rate = next(x for x in batch.health_samples if x.metric_name == "heart_rate")
    assert heart_rate.value == 63.0

    assert len(batch.workouts) == 1
    workout = batch.workouts[0]
    assert workout.external_id == "fixture-running-1"
    assert workout.distance_km == 5.2
    assert workout.avg_hr == 153
    assert workout.max_hr == 176
    assert len(workout.samples) == 3
    assert {x.metric_name for x in workout.samples} == {"heartRateData", "stepCount"}
    assert "heartRateData" not in workout.metadata
    assert "stepCount" not in workout.metadata


def test_parser_is_deterministic_for_same_payload() -> None:
    payload = json.loads(FIXTURE.read_text())
    parser = HAEParser("America/Sao_Paulo")
    first = parser.parse(payload)
    second = parser.parse(payload)
    assert [x.sample_hash for x in first.health_samples] == [
        x.sample_hash for x in second.health_samples
    ]
    assert [x.sample_hash for x in first.workouts[0].samples] == [
        x.sample_hash for x in second.workouts[0].samples
    ]


def test_source_is_provenance_not_identity_for_ios27_compatibility() -> None:
    payload = json.loads(FIXTURE.read_text())
    parser = HAEParser("America/Sao_Paulo")
    first = parser.parse(payload)

    changed = json.loads(FIXTURE.read_text())
    first_point = changed["data"]["metrics"][0]["data"][0]
    first_point.pop("source", None)
    second = parser.parse(changed)

    assert first.health_samples[0].sample_hash == second.health_samples[0].sample_hash


def test_corrected_value_keeps_same_logical_sample_identity() -> None:
    payload = json.loads(FIXTURE.read_text())
    parser = HAEParser("America/Sao_Paulo")
    first = parser.parse(payload)

    changed = json.loads(FIXTURE.read_text())
    changed["data"]["metrics"][0]["data"][0]["qty"] = 99.0
    second = parser.parse(changed)

    assert first.health_samples[0].sample_hash == second.health_samples[0].sample_hash
    assert first.health_samples[0].value != second.health_samples[0].value


def test_sleep_is_assigned_to_waking_day() -> None:
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "sleep_analysis",
                    "units": "h",
                    "data": [
                        {
                            "sleepStart": "2026-09-14 23:00:00 -0300",
                            "sleepEnd": "2026-09-15 07:00:00 -0300",
                            "asleep": 7.5,
                            "inBed": 8.0,
                        }
                    ],
                }
            ]
        }
    }
    sample = HAEParser("America/Sao_Paulo").parse(payload).health_samples[0]
    assert sample.local_date == "2026-09-15"
