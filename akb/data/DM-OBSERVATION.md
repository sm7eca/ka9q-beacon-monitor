---
id: DM-OBSERVATION
title: Observation Data Contract
version: 1.0.1
status: DRAFT_FOR_RE_REVIEW
owner: Data Architecture
type: entity
normative: true
depends_on:
  - DM-MEASUREMENT-WINDOW
  - ARCH-RUNTIME
  - ARCH-EVENTS
provides:
  - observation-contract
  - classification-snr-policy
consumes:
  - measurement-window-result
review:
  required: true
  passes:
    - data-model-integrity
    - requirement-traceability
    - testability-and-acceptance
---

# Purpose

Define the immutable `Observation` produced exactly once for one beacon and one closed measurement window.

# Scope

This contract owns detection state, measurement source, objective quality levels, diagnostic SNR values and the deterministic classification-SNR selection rule.

It does not own threshold classification logic, interval aggregation, persistence mapping or verification algorithms.

# Responsibilities

- Represent one beacon result for one closed window.
- Separate status-derived evidence from accepted verification evidence.
- Preserve optional KA9Q-reported SNR as diagnostic information only.
- Prevent `NO_DATA` from being interpreted as absence of RF energy.

# Definitions

| Term | Definition |
|---|---|
| Observation | Immutable result for one beacon and one closed measurement window. |
| DetectionState | `NO_SIGNAL`, `SIGNAL_PRESENT`, `PROBABLE_BEACON`, `VERIFIED_BEACON`, `INTERFERENCE`, or `NO_DATA`. |
| MeasurementSource | `STATUS_ONLY`, `VERIFIED_PCM`, `VERIFIED_IQ`, `VERIFIED_CW`, or `VERIFIED_MORSE`. |
| QualityLevel | `INVALID`, `DEGRADED`, `NOMINAL`, or `HIGH`. |
| classification_snr_db | The only SNR value permitted as input to classification thresholds. |

# Normative Requirements

- **DM-OBSERVATION-001:** One and only one Observation SHALL represent each beacon and closed MeasurementWindow.
- **DM-OBSERVATION-002:** Observation SHALL be immutable after construction.
- **DM-OBSERVATION-003:** All timestamps SHALL be timezone-aware UTC values and `window_end_utc` SHALL be later than `window_start_utc`.
- **DM-OBSERVATION-004:** When `verification_accepted` is true, `classification_snr_db` SHALL equal `verification_snr_db`.
- **DM-OBSERVATION-005:** When verification is not accepted, `classification_snr_db` SHALL equal `derived_local_snr_db`.
- **DM-OBSERVATION-006:** `ka9q_reported_snr_db` SHALL be optional diagnostic data and SHALL NOT be required for classification.
- **DM-OBSERVATION-007:** `VERIFIED_BEACON` SHALL require accepted verification and a non-status-only measurement source.
- **DM-OBSERVATION-008:** `NO_DATA` SHALL expose no classification SNR and SHALL use `measurement_quality = INVALID`.
- **DM-OBSERVATION-009:** Numeric optional fields SHALL be finite when present.
- **DM-OBSERVATION-010:** The model SHALL use objective `measurement_quality`, `verification_quality`, and `identification_quality`; it SHALL NOT define an undocumented aggregate confidence score.

# Interfaces

```yaml
entity: Observation
fields:
  beacon_id: stable beacon identifier
  window_start_utc: inclusive UTC timestamp
  window_end_utc: exclusive UTC timestamp
  detection_state: DetectionState
  measurement_source: MeasurementSource
  derived_local_snr_db: optional finite float
  verification_snr_db: optional finite float
  ka9q_reported_snr_db: optional finite float, diagnostic only
  measurement_quality: QualityLevel
  verification_quality: QualityLevel
  identification_quality: QualityLevel
  verification_accepted: boolean
  frequency_offset_hz: optional finite float
  identified_callsign: optional non-empty string
  reason_code: non-empty stable reason string
computed:
  classification_snr_db:
    rule:
      - if detection_state == NO_DATA: null
      - else if verification_accepted: verification_snr_db
      - else: derived_local_snr_db
```

# Constraints

- The contract SHALL contain no beacon threshold policy.
- The contract SHALL contain no averaging or aggregation algorithm.
- The contract SHALL not infer identity from signal presence alone.
- A missing `ka9q_reported_snr_db` SHALL be valid in plain linear/CW operation.

# Failure Modes

| Condition | Required behavior |
|---|---|
| Empty beacon ID | Reject construction. |
| Non-UTC timestamp | Reject construction. |
| Invalid interval | Reject construction. |
| Accepted verification without verification SNR | Reject construction. |
| `VERIFIED_BEACON` without accepted verification | Reject construction. |
| `NO_DATA` with classification evidence | Reject construction. |
| NaN or infinity | Reject construction. |

# Traceability

```yaml
governs:
  - MOD-OBSERVATION-BUILDER
  - MOD-CLASSIFIER
  - DM-DATABASE
verified_by:
  - TEST-DM-OBSERVATION
implementation:
  - src/ka9q_beacon_monitor/model/observation.py
```

# Review Questions

- Is the classification-SNR rule deterministic for every state?
- Can KA9Q diagnostic SNR accidentally affect classification?
- Are status evidence and accepted verification evidence distinguishable?
- Is identity quality separate from measurement quality?
- Can `NO_DATA` be mistaken for `NO_SIGNAL`?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial Observation contract. |

| 1.0.1 | 2026-08-06 | M3.1 consistency and executable-test patch. |
