---
id: DM-INTERVAL-SUMMARY
title: Interval Summary Data Contract
version: 1.0.1
status: DRAFT_FOR_RE_REVIEW
type: entity
normative: true
depends_on:
  - DM-OBSERVATION
provides:
  - interval-summary
  - summary-state
consumes:
  - observation
---

# Purpose

Define the immutable 30-minute result generated for one beacon from persisted or in-memory Observation objects.

# Scope

This contract owns interval membership, coverage, aggregate signal statistics, summary state and summary quality. It does not own SQL, scheduling, API rendering or beacon verification.

# Responsibilities

- Produce one summary for one beacon and one fixed interval.
- Count expected, received, valid, audible and verified observations.
- Calculate coverage and audible percentages.
- Calculate median and maximum classification SNR.
- Calculate median frequency offset when available.
- Assign one deterministic final state and one objective quality value.

# Definitions

| Term | Definition |
|---|---|
| Valid observation | An Observation whose detection state is not `NO_DATA`. |
| Audible observation | An Observation in `SIGNAL_PRESENT`, `PROBABLE_BEACON` or `VERIFIED_BEACON`. |
| Verified observation | An Observation in `VERIFIED_BEACON`. |
| Data coverage | Valid observations divided by expected observations, limited to 100 percent. |
| Audible percentage | Audible observations divided by valid observations. |

# Normative Requirements

- DM-INTERVAL-SUMMARY-001: A summary SHALL identify exactly one beacon.
- DM-INTERVAL-SUMMARY-002: Interval membership SHALL use `interval_start <= observation.window_start < interval_end`.
- DM-INTERVAL-SUMMARY-003: Expected observation count SHALL equal interval duration divided by the configured observation period.
- DM-INTERVAL-SUMMARY-004: `NO_DATA` observations SHALL be excluded from valid-observation statistics.
- DM-INTERVAL-SUMMARY-005: `SIGNAL_PRESENT`, `PROBABLE_BEACON` and `VERIFIED_BEACON` SHALL count as audible.
- DM-INTERVAL-SUMMARY-006: Coverage below 20 percent SHALL produce final state `NO_DATA` by default.
- DM-INTERVAL-SUMMARY-007: Interference exceeding 50 percent of valid observations SHALL produce `INTERFERED`.
- DM-INTERVAL-SUMMARY-008: `STRONG` SHALL require at least 50 percent audible and median classification SNR at or above 15 dB by default.
- DM-INTERVAL-SUMMARY-009: `AUDIBLE` SHALL require at least 50 percent audible and median classification SNR at or above 6 dB by default.
- DM-INTERVAL-SUMMARY-010: `WEAK` SHALL require at least 10 percent audible and median classification SNR at or above 3 dB by default.
- DM-INTERVAL-SUMMARY-011: Thresholds SHALL be configurable by the aggregation component without changing this entity schema.
- DM-INTERVAL-SUMMARY-012: The entity SHALL be immutable after construction.
- DM-INTERVAL-SUMMARY-013: Rules DM-INTERVAL-SUMMARY-006 through -010 SHALL be evaluated in listed order; the first matching rule wins.

# Interfaces

```yaml
entity: IntervalSummary
fields:
  beacon_id: string
  interval_start_utc: datetime
  interval_end_utc: datetime
  expected_observation_count: integer
  observation_count: integer
  valid_observation_count: integer
  verified_observation_count: integer
  audible_observation_count: integer
  data_coverage_percent: float
  audible_percent: float
  median_classification_snr_db: float|null
  maximum_classification_snr_db: float|null
  median_frequency_offset_hz: float|null
  final_state: SummaryState
  quality: QualityLevel
summary_states:
  - no_data
  - not_heard
  - weak
  - audible
  - strong
  - interfered
```

# Constraints

- All timestamps SHALL be timezone-aware.
- Interval end SHALL be later than interval start.
- Expected observation count SHALL be positive.
- Count fields SHALL be non-negative and internally consistent.
- Percentage fields SHALL be finite and within 0 through 100.
- Optional numeric values SHALL be finite when present.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Invalid interval | Construction SHALL fail. |
| Invalid count relationship | Construction SHALL fail. |
| No sufficient valid data | Summary SHALL be `NO_DATA`; fabrication of signal values is forbidden. |
| Observations for another beacon | They SHALL be ignored by aggregation. |
| Observations outside interval | They SHALL be ignored by aggregation. |

# Traceability

```yaml
governs:
  - MOD-AGGREGATOR
  - DM-DATABASE
verified_by:
  - TEST-DM-INTERVAL-SUMMARY
```

# Review Questions

- Are audible-state membership rules consistent with DM-OBSERVATION?
- Are default thresholds consistent with the approved system architecture?
- Can every output field be calculated deterministically from input observations and configuration?
- Is missing data represented without implying absence of RF energy?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial IntervalSummary contract. |

| 1.0.1 | 2026-08-06 | M3.1 consistency and executable-test patch. |
