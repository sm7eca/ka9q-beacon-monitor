---
id: AKB-STATUS
title: Design Status and Baseline Governance
version: 1.0.3
status: DRAFT_FOR_RE_REVIEW
owner: Architecture Board
type: contract
normative: true
depends_on: [AKB-META, AKB-SCHEMA, AKB-README]
provides:
  - lifecycle-states
  - baseline-gates
  - phase-0-assumption-register
consumes:
  - review-findings
review:
  required: true
  passes: [governance, completeness, risk]
change_control:
  approval: Architecture Board
  mechanism: ADR
---

# Purpose

Define lifecycle states, approval gates, baseline rules, and currently deferred Phase 0 assumptions.

# Scope

Applies to the AKB as a whole and to every normative contract admitted to Design Baseline 1.0.

# Responsibilities

- Define document states.
- Define review decisions.
- Define release gates.
- Track deferred external assumptions without treating them as guaranteed system behavior.

# Definitions

| Term | Definition |
|---|---|
| DRAFT | Authoring is in progress. |
| DRAFT_FOR_REVIEW | Content is complete enough for initial formal review. |
| DRAFT_FOR_RE_REVIEW | Review findings have been addressed and the package awaits re-review. |
| APPROVED | No mandatory changes remain, but the artifact has not yet been frozen as a baseline. |
| APPROVED_WITH_CHANGES | No Critical or High findings remain, but mandatory Medium or lower changes remain. |
| BASELINE | Approved and authoritative for implementation. |
| SUPERSEDED | Replaced by a newer approved version. |
| REJECTED | Declared ineligible by an explicit Architecture Board decision. |

# Normative Requirements

```yaml
requirements:
  - id: AKB-STATUS-001
    statement: A document SHALL enter BASELINE only after all Critical and High findings are closed.
    verification: review-register-audit
  - id: AKB-STATUS-002
    statement: A document with unresolved Medium findings MAY be APPROVED_WITH_CHANGES but SHALL NOT be marked BASELINE unless the Architecture Board accepts each residual risk explicitly.
    verification: approval-record-audit
  - id: AKB-STATUS-003
    statement: The complete Design Baseline 1.0 SHALL include normative requirements, error handling, traceability, data contracts, module contracts, tests, and ADRs.
    verification: manifest-completeness-check
  - id: AKB-STATUS-004
    statement: Phase 0 assumptions SHALL be marked NEEDS_VERIFICATION and SHALL have an owner, verification method, and design fallback before the complete baseline is released.
    verification: assumption-register-audit
  - id: AKB-STATUS-005
    statement: Failure of a Phase 0 assumption SHALL NOT require replacement of the approved high-level architecture unless an ADR explicitly states otherwise.
    verification: architecture-review
  - id: AKB-STATUS-006
    statement: RE_REVIEW_REQUIRED SHALL apply when one or more Critical findings OR one or more High findings remain open.
    verification: decision-rule-test
  - id: AKB-STATUS-007
    statement: REJECTED SHALL be assigned only by an explicit Architecture Board decision with recorded rationale.
    verification: approval-record-audit
  - id: AKB-STATUS-008
    statement: A Foundation package SHALL NOT enter BASELINE unless entry-point dependency consistency satisfies AKB-SCHEMA-009.
    verification: entry-point-dependency-audit
```

# Interfaces

```yaml
review_decisions:
  APPROVED:
    condition: critical == 0 and high == 0 and mandatory_changes == 0
  APPROVED_WITH_CHANGES:
    condition: critical == 0 and high == 0 and mandatory_changes >= 1
  RE_REVIEW_REQUIRED:
    condition: critical >= 1 or high >= 1
  REJECTED:
    condition: architecture_board_decision == REJECTED
```

# Constraints

- Current M1.2 state is `DRAFT_FOR_RE_REVIEW`.
- Implementation code SHALL NOT claim baseline conformance before the complete AKB reaches BASELINE.
- Phase 0 experiments MAY begin before complete baseline approval when explicitly authorized.
- Exactly one automatic review decision SHALL match each non-rejected findings-count combination.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Document marked BASELINE with open High finding | Status SHALL be reverted to DRAFT_FOR_RE_REVIEW. |
| Assumption lacks fallback before complete baseline release | Assumption SHALL be treated as an architecture risk. |
| Normative source omitted from release | Release SHALL fail completeness validation. |
| Review counts match no automatic decision | Governance validation SHALL fail. |
| Review counts match multiple automatic decisions | Governance validation SHALL fail. |

# Phase 0 Assumptions

```yaml
phase_0_assumptions:
  - id: P0-A-001
    statement: DEMOD_SNR availability depends on selected radiod demodulation mode.
    status: NEEDS_VERIFICATION
    owner: KA9Q integration lead
    verification_method: Capture and decode status datagrams from the selected radiod mode.
    fallback: derived_snr_db remains primary; DEMOD_SNR is optional diagnostics only.
  - id: P0-A-002
    statement: BASEBAND_POWER smoothing behavior under keyed CW is not yet characterized.
    status: NEEDS_VERIFICATION
    owner: Signal verification lead
    verification_method: Measure reported power for fixed peak power at multiple keyed-CW duty cycles.
    fallback: verification pipeline performs keying-sensitive analysis.
  - id: P0-A-003
    statement: Actual KA9Q status-cycle rate may differ from nominal configuration.
    status: NEEDS_VERIFICATION
    owner: KA9Q integration lead
    verification_method: Measure status datagram inter-arrival times during the Phase 0 endurance capture.
    fallback: MeasurementWindow uses time-based windows rather than packet-count assumptions.
```

# Traceability

```yaml
traceability:
  governed_by:
    - AKB-META
    - AKB-SCHEMA
    - AKB-REVIEW
  verified_by:
    - TEST-REVIEW-DECISION-RULES
    - TEST-AKB-ASSUMPTION-REGISTER
    - TEST-AKB-ENTRY-ORDER
```

# Review Questions

1. Are lifecycle states objective and enforceable?
2. Does every Critical/High count combination map to RE_REVIEW_REQUIRED?
3. Are Phase 0 assumptions owned, testable, and protected by fallbacks?
4. Is REJECTED clearly separated from automatic finding-count decisions?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial lifecycle and baseline governance contract. |
| 1.0.1 | 2026-08-06 | Corrected decision logic, moved Phase 0 assumptions, and defined Board-only REJECTED state. |
| 1.0.2 | 2026-08-06 | Added entry-point dependency consistency as a Foundation baseline gate. |
| 1.0.3 | 2026-08-06 | Delegated entry-point dependency consistency definition to AKB-SCHEMA-009. |
