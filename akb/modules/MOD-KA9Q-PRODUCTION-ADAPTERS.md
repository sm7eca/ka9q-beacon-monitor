---
id: MOD-KA9Q-PRODUCTION-ADAPTERS
version: 1.0.1
status: DRAFT_FOR_REVIEW
title: KA9Q Production Adapters and Phase 0
owner: KA9Q Integration
normative: true
type: contract
depends_on:
  - MILESTONE-M5-PRODUCTION-READINESS
  - MOD-STATUS-RECEIVER
  - MOD-VERIFICATION-ANALYZER
verified_by:
  - TEST-M5-KA9Q-PRODUCTION-ADAPTERS
  - EVIDENCE-M5-PHASE0
provides:
  - selected-release-status-adapter
  - selected-release-verification-adapter
  - phase0-evidence-harness
consumes:
  - ka9q-radiod-status
  - ka9q-verification-streams
review:
  required: true
  passes:
    - adapter-boundary
    - failure-isolation
    - selected-release-compatibility
    - phase0-evidence-integrity
    - m4-regression
---

# Purpose

Define M5.4 production-facing KA9Q adapters and the evidence discipline for Phase 0 without moving version-specific KA9Q behavior into the approved M4 domain modules.

# Scope

This module owns deployment adapters for raw radiod status datagrams and selective verification services, plus tooling and evidence structure for Phase 0. It does not redefine classification, verification acceptance policy, measurement windows, persistence, aggregation, REST resources, or Web UI behavior.

The Python layer deliberately does not copy the volatile KA9Q metadata binary grammar. A selected-release bridge, built and tested against the deployed `ka9q-radio` release, converts one raw status datagram to the narrow normalized JSON schema consumed by `Ka9qStatusBridgeDecoder`. The same deployment-boundary pattern is used for PCM/IQ verification.

# Responsibilities

- Keep selected-release KA9Q parsing behind `StatusDatagramDecoder`.
- Keep PCM/IQ/CW processing behind `VerificationBackend`.
- Fail closed on bridge process errors, malformed output, timeouts, or contract violations.
- Preserve source timestamps when the selected-release bridge provides UTC time; otherwise use receiver UTC arrival time.
- Provide a Phase 0 analyzer that never converts synthetic fixtures into field evidence.
- Record field availability, status cadence and keyed-CW power behavior from real captures.
- Keep Phase 0 assumptions explicitly `UNVERIFIED` until real evidence exists.

# Definitions

| Term | Definition |
|---|---|
| Selected-release bridge | Deployment helper compiled or otherwise validated against the exact deployed `ka9q-radio` release and responsible for version-specific wire/stream decoding. |
| Normalized status JSON | Narrow bridge output mapped directly to `StatusSample`; it is not a replacement domain model. |
| Real capture | Status/PCM/IQ data recorded from the intended radiod/hardware environment with provenance and checksum. |
| Synthetic fixture | Test-only generated input that can verify software behavior but cannot close Phase 0 hardware assumptions. |

# Interfaces

Status path: `radiod UDP multicast -> selected-release bridge -> Ka9qStatusBridgeDecoder -> StatusSample -> Ka9qStatusReceiver`.

Verification path: `VerificationRequest -> selected-release verification bridge -> VerificationEvidence -> VerificationAnalyzer`.

Phase 0 path: `real normalized capture -> analyze_status_capture -> recorded evidence artifact`.

# Constraints

- KA9Q release-specific wire details SHALL remain outside approved M4 domain and processing modules.
- Bridge output SHALL be validated against existing M4 data contracts before publication.
- Bridge stderr and failures SHALL NOT leak secret values into domain objects.
- Synthetic fixtures SHALL NOT be labeled as verified Phase 0 evidence.
- Missing real hardware/radiod evidence SHALL block field-complete approval of M5.4, but SHALL NOT prevent software-only adapter review.
- M4 semantics remain governed by `MILESTONE-M5-001`.

# Normative Requirements

- **MOD-KA9Q-PRODUCTION-ADAPTERS-001:** The status adapter SHALL implement the approved `StatusDatagramDecoder` boundary and SHALL return only validated `StatusSample` objects.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-002:** Version-specific KA9Q metadata decoding SHALL be isolated behind a selected-release bridge and SHALL NOT be duplicated into M4 processing code.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-003:** Status bridge non-zero exit, timeout, malformed JSON, missing required identity/frequency, or invalid field types SHALL fail as a status decode error without terminating the receiver.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-004:** The status adapter SHALL preserve a bridge-supplied UTC timestamp when present and valid. If the timestamp field is absent, it SHALL use the receiver-assigned UTC arrival time. If the timestamp field is present but invalid, the datagram SHALL be rejected fail-closed.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-005:** The verification adapter SHALL implement the approved `VerificationBackend` boundary and SHALL return only validated `VerificationEvidence`.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-006:** Verification bridge timeout, non-zero exit, malformed output, or evidence contract violation SHALL surface as a backend error for isolation by `VerificationAnalyzer`.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-007:** Any verification credential SHALL be supplied to the bridge through deployment-time secret injection and SHALL NOT be written into request JSON, logs, fixtures, or repository artifacts.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-008:** Phase 0 evidence SHALL use structured capture provenance identifying radiod version/revision, hardware, UTC interval, network endpoint, and capture SHA-256. `VERIFIED_CAPTURE` SHALL require complete provenance, non-empty captured samples, supplied capture bytes whose computed SHA-256 matches the provenance, and sample timestamps contained by the recorded UTC interval.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-009:** Phase 0 SHALL measure actual status cadence and observed status-field availability for each selected demodulation mode.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-010:** Phase 0 SHALL characterize `BASEBAND_POWER` under multiple keyed-CW duty cycles at controlled peak RF level and SHALL record the raw evidence used for the conclusion.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-011:** Phase 0 SHALL exercise practical PCM/IQ acquisition through the selected verification bridge and record success/failure with provenance.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-012:** Synthetic tests MAY verify adapter mechanics but SHALL remain `UNVERIFIED` for P0-A-001, P0-A-002 and P0-A-003 unless they are analyzing a separately captured artifact with complete structured provenance and a matching computed capture checksum. Software verification of provenance/checksum integrity does not by itself prove physical capture origin; field-session custody remains an explicit operational assumption until recorded evidence is reviewed.
- **MOD-KA9Q-PRODUCTION-ADAPTERS-013:** M5.4 SHALL preserve all approved M4/M5.1/M5.2/M5.3 semantics and SHALL not introduce autonomous KA9Q channel creation or retuning.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Status bridge unavailable | Reject adapter startup/configuration or decode attempt with actionable error; do not invent status fields. |
| Status bridge rejects datagram | Count/reject through existing receiver error isolation; continue receiving later datagrams. |
| Bridge output violates `StatusSample` | Reject that datagram. |
| Verification bridge times out/fails | Let `VerificationAnalyzer` convert it to deterministic backend-error rejection. |
| Phase 0 capture missing provenance | Keep evidence `UNVERIFIED`. |
| Synthetic capture supplied as field evidence | Keep evidence `UNVERIFIED`; do not close assumption. |
| Selected radiod release changes | Revalidate/rebuild bridge and repeat affected Phase 0 evidence before release. |

# Traceability

This contract implements `MILESTONE-M5-006` and `MILESTONE-M5-007`, preserves `MILESTONE-M5-001`, and is verified by `tests/ka9q/test_production_adapters.py`, `tests/ka9q/test_phase0.py`, full-suite regression, and real Phase 0 evidence recorded under `phase0/`.

# Acceptance Criteria

- Software adapter tests pass and the full repository suite remains green.
- Status and verification bridges fail closed on malformed/failing bridge behavior.
- Synthetic Phase 0 analyzer tests cannot produce `VERIFIED_CAPTURE` without complete structured provenance and checksum-matching capture bytes.
- A real M5.4 field session populates the Phase 0 evidence template before field-complete approval.
- P0-A-001 through P0-A-003 have explicit evidence-backed outcomes or remain `UNVERIFIED` with documented fallback.

# Review Questions

1. Are all volatile KA9Q release details behind the approved adapter boundaries?
2. Can a bridge failure silently create a valid-looking `StatusSample` or accepted verification?
3. Can synthetic fixtures accidentally close a Phase 0 assumption?
4. Is the real-capture provenance sufficient to reproduce the field conclusion?
5. Does M5.4 avoid changing any M4 domain rule or creating/retuning channels autonomously?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.1 | 2026-08-07 | Required structured, checksum-bound Phase 0 provenance and clarified fail-closed handling of present-but-invalid bridge timestamps. |
| 1.0.0 | 2026-08-07 | Initial M5.4 production-adapter and Phase 0 evidence contract. |
