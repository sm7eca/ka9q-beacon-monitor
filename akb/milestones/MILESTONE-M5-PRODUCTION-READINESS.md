---
id: MILESTONE-M5-PRODUCTION-READINESS
version: 1.0.1
status: DRAFT_FOR_REVIEW
title: M5 Production Readiness and Field Validation
owner: System Architecture
normative: true
type: contract
depends_on:
  - MOD-MAIN-APPLICATION
verified_by:
  - REVIEW-M5-START
provides:
  - production-readiness-scope
  - field-validation-plan
  - release-gates
consumes:
  - approved-m4-application
review:
  required: true
  passes:
    - scope-completeness
    - dependency-boundary
    - operational-readiness
    - field-validation
    - release-gate-consistency
---

# Purpose

Define the M5 milestone that turns the approved M4 application into a deployable, observable, field-validated system without changing the approved domain rules.

# Scope

M5 covers production configuration, secrets handling, observability, deployment packaging, real KA9Q adapter integration, Phase 0 radio verification, operational procedures, end-to-end acceptance, and release readiness.

M5 does not redefine classifier thresholds, verification policy, persistence semantics, aggregation rules, REST resources, Web UI behavior, or M4 module ownership.

# Responsibilities

- Define validated runtime configuration and secret boundaries.
- Add health, metrics, logs, and operational diagnostics.
- Package the application for repeatable installation and service operation.
- Implement and verify real KA9Q status and verification adapters.
- Execute Phase 0 tests for actual radiod status fields, timing, and keyed-CW behavior.
- Establish backup, retention, recovery, upgrade, and rollback procedures.
- Run end-to-end acceptance tests against representative RF and replay fixtures.
- Produce an auditable release candidate and operations handover.

# Definitions

| Term | Definition |
|---|---|
| Production readiness | Evidence that the system can be installed, operated, observed, upgraded, recovered, and validated in its intended environment. |
| Phase 0 | Hardware- and radiod-facing verification of assumptions that cannot be proven by unit tests alone. |
| Deployment adapter | Environment-specific implementation of an approved M4 protocol boundary. |
| Release candidate | A version that has passed all M5 gates and is ready for final operational approval. |

# Interfaces

Inputs: approved M4 composition root, deployment environment, radiod multicast/status streams, verification audio/IQ services, beacon configuration, and operational policies.

Outputs: deployable package, validated adapters, observability interfaces, operations documentation, acceptance evidence, and release decision material.

# Constraints

- Preservation of approved M4 boundaries and semantics is governed by MILESTONE-M5-001.
- Deployment-specific behavior SHALL remain behind explicit adapter interfaces.
- Credentials and secrets SHALL NOT be committed to the repository or embedded in generated artifacts.
- Hardware-dependent claims SHALL be marked unverified until supported by captured evidence.
- Every production-impacting configuration item SHALL be validated before services start.
- M5 deliverables SHALL remain reproducible from repository-controlled inputs.

# Normative Requirements

- **MILESTONE-M5-001:** M5 SHALL preserve the approved M4 module boundaries and domain semantics.
- **MILESTONE-M5-002:** Runtime configuration SHALL be schema-validated and fail closed before external services start.
- **MILESTONE-M5-003:** Secrets SHALL be supplied through explicit deployment mechanisms and SHALL NOT be stored in source control.
- **MILESTONE-M5-004:** The running system SHALL expose actionable health, structured logs, metrics, and version/build identity.
- **MILESTONE-M5-005:** Installation, startup, shutdown, restart, upgrade, rollback, backup, and recovery SHALL be documented and testable.
- **MILESTONE-M5-006:** Real KA9Q status decoding and verification adapters SHALL be implemented behind the existing approved protocol boundaries.
- **MILESTONE-M5-007:** Phase 0 SHALL verify actual status-field availability, multicast behavior, timestamp behavior, power smoothing, and keyed-CW duty-cycle effects.
- **MILESTONE-M5-008:** End-to-end tests SHALL cover replay input, live adapter integration, persistence, aggregation, API, and Web UI output.
- **MILESTONE-M5-009:** Operational failure scenarios SHALL include network interruption, radiod restart, malformed input, storage failure, process restart, and partial dependency outage.
- **MILESTONE-M5-010:** Release approval SHALL require complete traceability from M5 requirements to executable tests or recorded field evidence.
- **MILESTONE-M5-011:** Every M5 sub-milestone SHALL have its own AKB contract, review request, and `review_milestones.json` entry before implementation review.
- **MILESTONE-M5-012:** M5 completion SHALL produce a release-candidate manifest with versions, checksums, configuration schema version, migration state, and review decisions.
- **MILESTONE-M5-013:** The deployment package SHALL be reproducibly buildable and installable from repository-controlled inputs without manual post-install steps.

# Delivery Plan

| Sub-milestone | Primary outcome |
|---|---|
| M5.1 Configuration and Secrets | Validated configuration model, environment loading, secret boundaries, startup validation. |
| M5.2 Observability and Diagnostics | Structured logging, metrics, build identity, readiness/liveness and diagnostic status. |
| M5.3 Deployment Packaging | Repeatable package/container/service definition, installation, upgrade and rollback. |
| M5.4 KA9Q Production Adapters and Phase 0 | Real decoder/backend adapters and captured hardware/radiod evidence. |
| M5.5 End-to-End and Failure Validation | Replay/live system tests, fault injection, recovery and performance evidence. |
| M5.6 Operations and Release Candidate | Runbooks, backup/restore, release manifest, final review and handover. |

# Failure Modes

| Failure | Required behavior |
|---|---|
| Invalid production configuration | Reject startup before opening external resources. |
| Missing secret | Reject startup without logging the secret value. |
| Unsupported radiod/status behavior | Mark assumption unverified and block release where it affects correctness. |
| Adapter failure | Surface actionable diagnostics and preserve isolation required by M4 contracts. |
| Storage or migration failure | Fail safely, preserve prior data, and provide documented recovery steps. |
| Incomplete acceptance evidence | Keep milestone in review-required state. |

# Traceability

This milestone depends on the approved M4 composition root and governs all M5 sub-milestones. Each sub-milestone SHALL link its requirements to executable tests, deployment verification, or recorded Phase 0 evidence.

# Acceptance Criteria

- The M5 scope and sub-milestone sequence are approved before new production-facing code is accepted.
- Every sub-milestone has a named owner, AKB contract, tests/evidence plan, and review-package configuration.
- No M4 contract is weakened or duplicated.
- Hardware assumptions are separated from software-only verification.
- Release gates are objective and traceable.

# Review Questions

1. Does M5 include every activity needed to operate the system safely in the intended environment?
2. Are hardware-dependent assumptions separated clearly from software contracts?
3. Is the proposed sub-milestone order dependency-correct?
4. Are release gates measurable rather than aspirational?
5. Are security, recovery, upgrade, and rollback responsibilities explicit?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.1 | 2026-08-07 | Added the M5.3 packaging reproducibility requirement and delegated the M4-preservation constraint to MILESTONE-M5-001. |
| 1.0.0 | 2026-08-07 | Initial M5 production-readiness milestone definition. |
