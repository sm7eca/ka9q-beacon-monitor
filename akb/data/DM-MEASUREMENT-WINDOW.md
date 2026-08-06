---
id: DM-MEASUREMENT-WINDOW
title: Measurement Window Data Contract
version: 1.0.1
status: DRAFT_FOR_RE_REVIEW
owner: Data Architecture
type: entity
normative: true
depends_on:
  - DM-STATUS-SAMPLE
  - ARCH-RUNTIME
provides:
  - measurement-window
  - sample-coverage
consumes:
  - status-sample
traceability:
  verified_by:
    - TEST-DM-MEASUREMENT-WINDOW
---

# Purpose

Define the immutable ten-second temporal container used to group normalized KA9Q `StatusSample` values for one logical channel.

# Scope

This contract owns window boundaries, sample membership, ordering, expected sample count and coverage metrics.

It does not own beacon classification, reference-channel correlation, derived SNR, verification or persistence.

# Responsibilities

- Represent exactly one half-open interval `[start_utc, end_utc)`.
- Group samples belonging to one `channel_id`.
- Reject samples outside the interval.
- Reject samples from another channel.
- Normalize sample ordering by `timestamp_utc`.
- Expose deterministic coverage metrics.

# Definitions

| Term | Definition |
|---|---|
| MeasurementWindow | Immutable collection of zero or more `StatusSample` values for one channel and one ten-second interval. |
| Half-open interval | The start timestamp is included and the end timestamp is excluded. |
| Expected sample count | Rounded product of window duration and configured expected status rate. |
| Coverage ratio | `min(sample_count / expected_sample_count, 1.0)`. |
| Empty window | A valid window with zero samples. |

# Normative Requirements

- **DM-MEASUREMENT-WINDOW-001:** A window SHALL have a duration of exactly 10 seconds.
- **DM-MEASUREMENT-WINDOW-002:** `start_utc` SHALL be timezone-aware UTC.
- **DM-MEASUREMENT-WINDOW-003:** The interval SHALL be `[start_utc, start_utc + 10 seconds)`.
- **DM-MEASUREMENT-WINDOW-004:** Every contained sample SHALL have the same `channel_id` as the window.
- **DM-MEASUREMENT-WINDOW-005:** Every contained sample timestamp SHALL fall inside the interval.
- **DM-MEASUREMENT-WINDOW-006:** Samples SHALL be exposed in ascending timestamp order.
- **DM-MEASUREMENT-WINDOW-007:** `expected_status_rate_hz` SHALL be greater than zero.
- **DM-MEASUREMENT-WINDOW-008:** Coverage SHALL be capped at 100 percent when duplicate or excess samples are received.
- **DM-MEASUREMENT-WINDOW-009:** An empty window SHALL be representable and SHALL NOT by itself assert `NO_DATA`; the observation builder owns that decision.
- **DM-MEASUREMENT-WINDOW-010:** The contract SHALL NOT calculate beacon classification, derived SNR or identity confidence.

# Interfaces

```yaml
entity: MeasurementWindow
fields:
  channel_id:
    type: string
    required: true
  start_utc:
    type: datetime-utc
    required: true
  end_utc:
    type: derived-datetime-utc
    expression: start_utc + 10s
  samples:
    type: ordered-tuple<StatusSample>
    required: true
    default: []
  expected_status_rate_hz:
    type: positive-float
    required: true
    default: 2.0
derived_fields:
  sample_count: integer
  expected_sample_count: integer
  coverage_ratio: float-0-to-1
  coverage_percent: float-0-to-100
  first_sample_utc: datetime-utc|null
  last_sample_utc: datetime-utc|null
```

# Constraints

- Sample timestamps equal to `end_utc` belong to the next window.
- The data contract permits duplicate timestamps; duplicate handling policy belongs to the window builder or status cache.
- Median helper functions may summarize raw KA9Q fields but SHALL NOT convert them into beacon semantics.

# Failure Modes

| Condition | Required behavior |
|---|---|
| Empty or blank channel ID | Reject construction. |
| Non-UTC or naive start timestamp | Reject construction. |
| Non-positive expected status rate | Reject construction. |
| Sample from another channel | Reject construction. |
| Sample outside interval | Reject construction. |
| No samples | Construct a valid empty window with zero coverage. |

# Traceability

```yaml
governed_by:
  - ARCH-RUNTIME
consumes:
  - DM-STATUS-SAMPLE
verified_by:
  - TEST-DM-MEASUREMENT-WINDOW
implemented_by:
  - src/ka9q_beacon_monitor/model/measurement_window.py
```

# Review Questions

- Are interval boundary semantics unambiguous?
- Is the ownership boundary between window metrics and observation semantics preserved?
- Can the expected count be reproduced for any configured status rate?
- Are empty and partial windows represented without silently inventing beacon state?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial MeasurementWindow contract. |

| 1.0.1 | 2026-08-06 | M3.1 consistency and executable-test patch. |
