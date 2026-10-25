from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True, slots=True)
class TrainingLoadPoint:
    day: date
    load: float
    ctl: float
    atl: float
    tsb: float
    acwr: float | None


def banister_trimp(
    duration_minutes: float,
    avg_hr: float,
    hr_rest: float,
    hr_max: float,
    exponential_coefficient: float,
) -> float:
    """Banister-style heart-rate reserve TRIMP.

    Formula:
      HRr = (avg_hr - hr_rest) / (hr_max - hr_rest)
      TRIMP = duration_minutes * HRr * 0.64 * exp(k * HRr)

    The coefficient is configuration, never inferred by this function.
    """
    if duration_minutes <= 0 or hr_max <= hr_rest:
        return 0.0
    hrr = (avg_hr - hr_rest) / (hr_max - hr_rest)
    hrr = max(0.0, min(hrr, 1.2))
    return duration_minutes * hrr * 0.64 * math.exp(exponential_coefficient * hrr)


def training_load_series(
    daily_loads: Mapping[date, float],
    start: date,
    end: date,
    ctl_tau_days: float = 42.0,
    atl_tau_days: float = 7.0,
) -> list[TrainingLoadPoint]:
    alpha_ctl = 1.0 - math.exp(-1.0 / ctl_tau_days)
    alpha_atl = 1.0 - math.exp(-1.0 / atl_tau_days)
    ctl = 0.0
    atl = 0.0
    rolling: list[float] = []
    result: list[TrainingLoadPoint] = []
    current = start
    while current <= end:
        load = float(daily_loads.get(current, 0.0))
        tsb = ctl - atl  # pre-day form: fitness minus fatigue before today's load
        ctl = ctl + alpha_ctl * (load - ctl)
        atl = atl + alpha_atl * (load - atl)
        rolling.append(load)
        if len(rolling) > 28:
            rolling.pop(0)
        acute = sum(rolling[-7:])
        chronic_weekly = sum(rolling) / 4.0 if len(rolling) >= 28 else 0.0
        acwr = acute / chronic_weekly if chronic_weekly > 0 else None
        result.append(TrainingLoadPoint(current, load, ctl, atl, tsb, acwr))
        current += timedelta(days=1)
    return result
