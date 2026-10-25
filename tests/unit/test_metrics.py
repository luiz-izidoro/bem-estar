from __future__ import annotations

from datetime import date, timedelta

import pytest

from bemestar.domain.metrics.readiness import (
    ScoreComponent,
    robust_score,
    sleep_duration_score,
    sleep_efficiency_score,
    weighted_score,
)
from bemestar.domain.metrics.training import banister_trimp, training_load_series


def test_banister_trimp_reference_case() -> None:
    value = banister_trimp(40, 153, 61, 190, 1.92)
    assert value == pytest.approx(71.799, rel=0.002)


def test_training_load_series_is_stable_and_tsb_is_preday() -> None:
    start = date(2026, 1, 1)
    loads = {start + timedelta(days=i): 50.0 for i in range(28)}
    points = training_load_series(loads, start, start + timedelta(days=27))
    assert len(points) == 28
    assert points[0].tsb == 0.0
    assert points[-1].ctl > 0
    assert points[-1].atl > points[-1].ctl
    assert points[-1].acwr is not None


def test_readiness_helpers_have_explicit_bounds() -> None:
    score, baseline = robust_score(60, [50, 51, 52, 53, 54, 55, 56, 57])
    assert baseline == 53.5
    assert 0 <= score <= 100
    assert sleep_duration_score(8, 8) == 100
    assert sleep_efficiency_score(7.2, 8.0) == pytest.approx(83.333333, rel=1e-5)
    assert weighted_score([ScoreComponent("a", 100, 0.5), ScoreComponent("b", 0, 0.5)]) == 50
