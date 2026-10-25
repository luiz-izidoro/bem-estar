from __future__ import annotations

ACTIVE_METRIC_VERSIONS: dict[str, str] = {
    "trimp": "banister-trimp-v1",
    "training_load": "training-load-v1",
    "ctl": "training-load-v1",
    "atl": "training-load-v1",
    "tsb": "training-load-v1",
    "acwr": "training-load-v1",
    "sleep_hours": "sleep-v1",
    "sleep_efficiency_score": "sleep-v1",
    "recovery": "recovery-v1",
    "recovery_confidence": "recovery-v1",
    "readiness_confidence": "readiness-v1",
    "readiness_morning": "readiness-v1",
    "readiness_live": "readiness-v1",
}

GROUP_VERSIONS: dict[str, str] = {
    "trimp": "banister-trimp-v1",
    "training": "training-load-v1",
    "sleep": "sleep-v1",
    "recovery": "recovery-v1",
    "readiness": "readiness-v1",
}


def active_version(metric_name: str) -> str | None:
    return ACTIVE_METRIC_VERSIONS.get(metric_name)
