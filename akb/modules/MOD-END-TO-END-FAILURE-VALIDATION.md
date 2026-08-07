---
id: MOD-END-TO-END-FAILURE-VALIDATION
version: 1.0.0
status: DRAFT_FOR_REVIEW
title: End-to-End and Failure Validation
owner: System Validation
normative: true
type: contract
depends_on:
  - MILESTONE-M5-PRODUCTION-READINESS
  - MOD-MAIN-APPLICATION
  - MOD-KA9Q-PRODUCTION-ADAPTERS
verified_by:
  - TEST-M5-END-TO-END
  - EVIDENCE-M5-FAILURE-VALIDATION
provides:
  - replay-validation
  - fault-injection-validation
  - recovery-evidence
consumes:
  - approved-runtime-composition
  - approved-production-adapters
review:
  required: true
  passes:
    - end-to-end-path
    - failure-injection
    - recovery
    - evidence-integrity
    - regression
---

# Purpose

Define M5.5 executable validation for the approved system composition, including deterministic replay, production-adapter boundary integration, persistence, aggregation, API/Web output, fault injection, recovery, and bounded performance evidence.

# Scope

M5.5 validates already-approved behavior. It SHALL NOT redefine classifier thresholds, verification policy, persistence semantics, aggregation rules, API resources, Web UI behavior, or Phase-0 hardware claims.

# Responsibilities

- Exercise normalized replay through the actual `BeaconRuntime` composition root.
- Verify data reaches persistence, aggregation, API, and Web UI surfaces.
- Exercise production adapter boundaries without claiming synthetic input is field evidence.
- Inject operational failures and verify isolation/recovery behavior.
- Record repeatable performance measurements as evidence, not as new domain thresholds.
- Keep Phase-0 hardware assumptions `UNVERIFIED` unless separately supported by M5.4 field evidence.

# Definitions

| Term | Definition |
|---|---|
| Replay | Repository-controlled normalized `StatusSample` input processed through the normal runtime pipeline. |
| Fault injection | Deliberate failure of a dependency or input boundary to verify documented recovery behavior. |
| Recovery evidence | Executed test result demonstrating that the system remains safe and can resume expected processing after the injected fault is removed. |
| Live adapter integration | Execution through the M5.4 production adapter boundary; synthetic bridge fixtures do not constitute field evidence. |

# Interfaces

Replay path: `JSONL replay -> StatusSample -> BeaconRuntime -> MeasurementBuilder -> Classifier -> VerificationAnalyzer -> Repository -> IntervalAggregator -> API/Web`.

Adapter validation path: `raw fixture -> production status bridge boundary -> StatusSample -> runtime`.

# Constraints

- M4/M5.1-M5.4 contracts remain normative and unchanged.
- Synthetic adapter tests SHALL NOT change Phase-0 field-evidence status.
- Tests SHALL use deterministic UTC timestamps and repository-controlled fixtures.
- Fault-injection tests SHALL demonstrate both failure behavior and recovery where recovery is meaningful.
- Performance evidence SHALL report workload and elapsed time; it SHALL NOT invent an acceptance threshold not defined elsewhere.

# Normative Requirements

- **MOD-END-TO-END-FAILURE-VALIDATION-001:** A deterministic replay SHALL traverse the approved runtime pipeline without bypassing measurement, classification, verification, persistence, or aggregation.
- **MOD-END-TO-END-FAILURE-VALIDATION-002:** Replay validation SHALL prove persisted observations are retrievable through the approved REST API and represented by the approved Web UI surface.
- **MOD-END-TO-END-FAILURE-VALIDATION-003:** Replay validation SHALL prove interval summaries are persisted and exposed through the approved REST API.
- **MOD-END-TO-END-FAILURE-VALIDATION-004:** A production status-adapter integration test SHALL execute the M5.4 adapter boundary while remaining explicitly synthetic/non-field evidence.
- **MOD-END-TO-END-FAILURE-VALIDATION-005:** Network interruption or radiod restart simulation SHALL not corrupt persisted data and processing SHALL resume after the receiver/dependency is restored.
- **MOD-END-TO-END-FAILURE-VALIDATION-006:** Malformed adapter input SHALL be rejected without terminating subsequent valid processing.
- **MOD-END-TO-END-FAILURE-VALIDATION-007:** Storage write failure SHALL be surfaced through runtime error accounting, SHALL not be reported as persisted, and subsequent recovery SHALL permit later valid persistence.
- **MOD-END-TO-END-FAILURE-VALIDATION-008:** Process restart validation SHALL reopen persisted state from the same repository and preserve API-visible data.
- **MOD-END-TO-END-FAILURE-VALIDATION-009:** Partial dependency outage SHALL preserve liveness while readiness fails closed when the configured readiness dependency reports failure.
- **MOD-END-TO-END-FAILURE-VALIDATION-010:** Replay evidence SHALL record submitted samples, persisted observations, persisted summaries, pipeline errors, elapsed duration, and derived throughput.
- **MOD-END-TO-END-FAILURE-VALIDATION-011:** M5.5 SHALL preserve all approved M4/M5.1-M5.4 production code semantics and SHALL not mark Phase-0 assumptions verified.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Network interruption / radiod restart | Existing persisted data remains intact; processing can resume after restoration. |
| Malformed input | Reject input, isolate error, continue with later valid data. |
| Storage failure | Surface pipeline error; do not claim failed write persisted; recover after storage returns. |
| Process restart | Reopen repository and expose previously persisted records. |
| Partial dependency outage | Liveness remains process-local; readiness fails closed. |
| Incomplete field evidence | Keep Phase-0 assumptions `UNVERIFIED`. |

# Traceability

Implements `MILESTONE-M5-008` and `MILESTONE-M5-009`, preserves `MILESTONE-M5-001`, and is verified by `tests/validation/` plus the full repository regression suite.

# Acceptance Criteria

- All M5.5 focused tests pass.
- Full repository regression remains green.
- Replay proves persistence, aggregation, API and UI integration.
- Each required operational failure has an executable test demonstrating safe behavior and recovery where applicable.
- No M5.4 field-evidence status is upgraded by synthetic validation.

# Review Questions

1. Does replay use the real runtime composition root rather than a parallel mock pipeline?
2. Are persistence, aggregation, API and UI all observed after replay?
3. Do fault tests prove recovery, not merely error detection?
4. Can any synthetic M5.5 test accidentally close a Phase-0 assumption?
5. Are performance results evidence-only rather than invented release thresholds?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-07 | Initial M5.5 end-to-end and failure-validation contract. |
