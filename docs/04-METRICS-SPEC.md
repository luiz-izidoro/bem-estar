# Metrics Specification

This document is normative. Formula changes require a version bump, tests, and documentation update.

## 1. Raw daily inputs

- HRV: median available `heart_rate_variability` value for the local day.
- Resting HR: median available `resting_heart_rate` value for the local day.
- Sleep: HAE aggregated `sleep_analysis`; choose the candidate with the largest total sleep for the day when duplicates exist.
- Workouts: HAE v2 workout summary, preferably including average HR and one-minute workout metrics.

## 2. TRIMP — `banister-trimp-v1`

Requires explicit owner profile values `hr_max` and `hr_rest`, plus workout average HR. No estimate is made when missing.

```text
HRr = clamp((avgHR - HRrest) / (HRmax - HRrest), 0, 1.2)
TRIMP = duration_minutes × HRr × 0.64 × exp(k × HRr)
```

`k` is the explicit profile field `trimp_exponential_coefficient`; default bootstrap value is 1.92 but must be reviewed/configured by the owner before using training-load outputs for decisions. The code treats it as an algorithm parameter, not an inferred personal attribute.

If required inputs are absent, per-workout TRIMP is stored as `null` with a reason component. It is never invented.

## 3. Training load — `training-load-v1`

Daily load = sum of available workout TRIMP.

Exponential moving models:

```text
alpha_CTL = 1 - exp(-1 / 42)
alpha_ATL = 1 - exp(-1 / 7)
CTL_today = CTL_prev + alpha_CTL × (load_today - CTL_prev)
ATL_today = ATL_prev + alpha_ATL × (load_today - ATL_prev)
TSB_today = CTL_prev - ATL_prev   # pre-day form
```

Warm-up starts at zero at the earliest available training/sample date. Early-history CTL/ATL must therefore be interpreted as warming up until enough history exists.

### ACWR

```text
acute = sum(last 7 daily loads)
chronic_weekly = sum(last 28 daily loads) / 4
ACWR = acute / chronic_weekly
```

ACWR is `null` until 28 rolling values exist or chronic load is zero. The product must not label a numeric ACWR as injury probability; it is a training-load descriptor.

## 4. Sleep — `sleep-v1`

`sleep_hours`: HAE `totalSleep`, falling back to `asleep`.

Efficiency percentage:

```text
efficiency = asleep / inBed × 100
```

Dashboard score (non-clinical UX normalization):

```text
sleep_efficiency_score = clamp((efficiency - 65) / 0.30, 0, 100)
```

Sleep duration score:

```text
score = clamp(100 - abs(hours - target_sleep_hours) × 18, 0, 100)
```

## 5. Robust baseline score

For HRV and RHR, use previous 28 days; minimum 7 observations.

```text
baseline = median(history)
MAD = median(abs(x - baseline))
robust_sigma = 1.4826 × MAD
z = (today - baseline) / robust_sigma
score = clamp(50 + 15z, 0, 100)
```

For resting HR, invert `z` so lower-than-baseline values score higher. If fewer than seven observations exist, return neutral score 50 and expose baseline availability in components.

## 6. Recovery — `recovery-v1`

Available components are reweighted proportionally:

| Component | Weight |
|---|---:|
| HRV baseline score | 0.40 |
| resting-HR baseline score | 0.25 |
| sleep-duration score | 0.35 |

A score can exist with missing components, but components/provenance are always returned. `recovery_confidence` reports the percentage of configured component weight actually present.

## 7. Readiness — `readiness-v1`

Morning weights:

| Component | Weight |
|---|---:|
| HRV | 0.30 |
| resting HR | 0.15 |
| sleep duration | 0.25 |
| sleep efficiency | 0.10 |
| training balance (TSB) | 0.20 |

Training balance score:

```text
clamp(100 - abs(TSB - 5) × 2.2, 0, 100)
```

Missing components are omitted and remaining weights normalized. `readiness_confidence` reports the percentage of configured component weight actually present.

### Morning vs live

`readiness_morning` uses the day-start component set and pre-day TSB.

`readiness_live` begins from morning readiness and applies an explicit same-day training-load penalty when training load and CTL are available:

```text
penalty = min(20, 10 × today_load / max(CTL, 10))
readiness_live = max(0, readiness_morning - penalty)
```

This distinction is deliberately visible in stored components.

## 8. Interpretation constraints

- Do not call readiness/recovery a medical assessment.
- Prefer multi-day trends over one-day scores.
- UI/MCP must expose algorithm version when useful.
- Any change to formula/weights = new version.
- Before production trust, compare outputs with historical project values and create golden tests.
