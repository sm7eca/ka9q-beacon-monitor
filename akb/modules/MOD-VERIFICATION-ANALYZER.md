---
id: MOD-VERIFICATION-ANALYZER
title: Verification Analyzer
version: 1.0.0
status: DRAFT_FOR_REVIEW
owner: Runtime Architecture
type: contract
normative: true
depends_on:
  - DM-OBSERVATION
  - MOD-CLASSIFIER
provides:
  - verification-request
  - verified-observation
consumes:
  - probable-beacon-observation
  - verification-evidence
verified_by:
  - TEST-MOD-VERIFICATION-ANALYZER
---

# Purpose

Define selective verification orchestration for observations classified as `PROBABLE_BEACON`.

# Scope

This contract owns verification request construction, evidence acceptance policy, failure isolation, and creation of verified or rejected `Observation` values. It does not own KA9Q RTP transport, FFT processing, CW detection algorithms, or Morse decoding algorithms; those are supplied through a replaceable verification backend.

# Responsibilities

- Request low-level verification only for `PROBABLE_BEACON` observations.
- Correlate evidence to beacon and measurement window.
- Apply deterministic SNR, frequency-offset, quality, CW, and callsign gates.
- Upgrade an observation to `VERIFIED_BEACON` only when all gates pass.
- Isolate backend failures without terminating the runtime pipeline.

# Definitions

| Term | Definition |
|---|---|
| Verification backend | Replaceable provider that performs low-level PCM/IQ/CW/Morse analysis. |
| Accepted verification | Evidence satisfying every policy gate and identity check. |
| Rejected verification | Evidence retained as diagnostic metadata without upgrading detection state. |

# Normative Requirements

- **MOD-VERIFICATION-ANALYZER-001:** The analyzer SHALL invoke its backend only for observations in `PROBABLE_BEACON` state.
- **MOD-VERIFICATION-ANALYZER-002:** A verification request SHALL preserve beacon ID and exact window boundaries.
- **MOD-VERIFICATION-ANALYZER-003:** Evidence with a mismatched beacon ID or window SHALL be rejected.
- **MOD-VERIFICATION-ANALYZER-004:** Accepted evidence SHALL require detected CW, finite verification SNR at or above policy threshold, and absolute frequency offset within policy.
- **MOD-VERIFICATION-ANALYZER-005:** `INVALID` or `DEGRADED` verification quality SHALL NOT produce `VERIFIED_BEACON`.
- **MOD-VERIFICATION-ANALYZER-006:** Morse verification SHALL require an identified callsign when configured by policy.
- **MOD-VERIFICATION-ANALYZER-007:** When an expected callsign is provided, normalized evidence callsign SHALL match it exactly.
- **MOD-VERIFICATION-ANALYZER-008:** Accepted evidence SHALL create an immutable `Observation` with `verification_accepted=true`, a verified measurement source, and `VERIFIED_BEACON` state.
- **MOD-VERIFICATION-ANALYZER-009:** Rejected evidence SHALL preserve `PROBABLE_BEACON`, keep `measurement_source=STATUS_ONLY`, and expose a deterministic reason code.
- **MOD-VERIFICATION-ANALYZER-010:** Backend exceptions SHALL be isolated and represented by reason code `verification_backend_error`.
- **MOD-VERIFICATION-ANALYZER-011:** The analyzer SHALL NOT implement persistence, web presentation, status classification, KA9Q multicast transport, or low-level DSP algorithms.

# Interfaces

```yaml
input:
  observation: Observation
  expected_callsign: string|null
backend:
  analyze(request: VerificationRequest): awaitable VerificationEvidence
output:
  observation: Observation
```

# Constraints

- Verification is selective, not continuous for all channels.
- KA9Q-reported DEMOD SNR is not used as an acceptance dependency.
- Policy values must be finite; maximum absolute frequency offset must be non-negative.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Backend raises | Return rejected probable observation with `verification_backend_error`. |
| Evidence identity mismatch | Reject without upgrading state. |
| CW absent | Reject with `cw_not_detected`. |
| SNR missing or below threshold | Reject with deterministic SNR reason code. |
| Frequency offset missing or outside policy | Reject with deterministic frequency reason code. |
| Callsign missing/mismatched | Reject when callsign policy applies. |

# Traceability

```yaml
implemented_by:
  - src/ka9q_beacon_monitor/processing/verification_analyzer.py
verified_by:
  - tests/processing/test_verification_analyzer.py
```

# Review Questions

- Are all acceptance gates explicit and deterministic?
- Can backend failure or mismatched evidence upgrade an observation?
- Is low-level DSP kept behind the backend interface?
- Is a verified observation valid under `DM-OBSERVATION`?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial M4.4 verification analyzer contract. |
