---
id: MOD-CLASSIFIER
title: Beacon Classifier Module
version: 1.0.0
status: DRAFT_FOR_REVIEW
owner: Processing
normative: true
depends_on:
  - DM-MEASUREMENT-WINDOW
  - DM-OBSERVATION
  - ARCH-KA9Q
provides:
  - status-only-observation
consumes:
  - synchronized-measurement-windows
verified_by:
  - TEST-MOD-CLASSIFIER
---

# Purpose

Define deterministic status-driven classification of one beacon measurement window.

# Scope

The module derives local SNR from one signal-channel window and one or more local reference-channel windows, applies hysteresis and produces one immutable `Observation`.

# Responsibilities

- Validate that signal and reference windows cover the same UTC interval.
- Derive local SNR from median signal baseband power minus median reference baseband power.
- Apply signal-present and probable-beacon thresholds with hysteresis.
- Assign measurement quality from coverage, reference count and reference agreement.
- Produce `NO_DATA` when minimum evidence is unavailable.
- Produce `INTERFERENCE` when reference channels disagree beyond policy.

# Definitions

| Term | Definition |
|---|---|
| Derived local SNR | Median signal-channel baseband power minus the median of accepted reference-channel median powers. |
| Accepted reference window | A synchronized reference window meeting minimum coverage and exposing baseband power. |
| Hysteresis | Separate enter and exit thresholds used to avoid rapid state oscillation. |

# Normative Requirements

- **MOD-CLASSIFIER-001:** Classification input SHALL contain one non-empty beacon ID, one signal window and zero or more reference windows.
- **MOD-CLASSIFIER-002:** All supplied windows SHALL have identical start and end timestamps.
- **MOD-CLASSIFIER-003:** Classification SHALL return `NO_DATA` when signal evidence or the configured minimum number of usable reference windows is unavailable.
- **MOD-CLASSIFIER-004:** Derived local SNR SHALL equal median signal baseband power minus median accepted-reference baseband power.
- **MOD-CLASSIFIER-005:** `ka9q_reported_snr_db` SHALL NOT be a classification dependency.
- **MOD-CLASSIFIER-006:** State thresholds SHALL apply configured enter/exit hysteresis deterministically.
- **MOD-CLASSIFIER-007:** Reference disagreement above the configured maximum spread SHALL produce `INTERFERENCE` with degraded quality.
- **MOD-CLASSIFIER-008:** A status-only classifier SHALL NOT emit `VERIFIED_BEACON` or accept verification.
- **MOD-CLASSIFIER-009:** Repeated classification of identical input and configuration SHALL produce equal observations.
- **MOD-CLASSIFIER-010:** The module SHALL perform no persistence, DSP, Morse decoding or network I/O.

# Interfaces

```yaml
input:
  type: ClassificationInput
  fields:
    - beacon_id
    - signal_window
    - reference_windows
    - previous_state
output:
  type: Observation
  measurement_source: status_only
```

# Constraints

Threshold values are configuration data and SHALL be validated at construction time. Phase 0 measurements may tune thresholds without changing this contract.

# Failure Modes

| Condition | Required behavior |
|---|---|
| Empty beacon ID | Reject input. |
| Unsynchronized windows | Reject input. |
| Insufficient signal or reference evidence | Return `NO_DATA`; do not invent measurements. |
| Reference spread exceeds policy | Return `INTERFERENCE`. |
| Invalid configuration ordering | Reject configuration. |

# Traceability

```yaml
implemented_by:
  - src/ka9q_beacon_monitor/processing/classifier.py
verified_by:
  - tests/processing/test_classifier.py
```

# Review Questions

- Is derived local SNR defined exactly once and implemented identically?
- Can any branch produce `VERIFIED_BEACON` without verification?
- Are enter and exit thresholds applied in the intended order?
- Does inadequate evidence always result in `NO_DATA`?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial M4.3 classifier contract. |
