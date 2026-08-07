---
id: MOD-OPERATIONS-RELEASE-CANDIDATE
version: 1.0.1
status: DRAFT_FOR_RE_REVIEW
title: Operations and Release Candidate
owner: System Architecture
normative: true
type: contract
depends_on: [MILESTONE-M5-PRODUCTION-READINESS]
provides: [release-manifest, backup-restore, operations-runbook]
consumes: [approved-m5-review-decisions, phase0-evidence]
review:
  required: true
  passes: [operations-readiness, backup-restore, release-gate-consistency, traceability]
---
# Purpose
Define M5.6 operations handover and release-candidate gating.
# Scope
Runbooks, backup/restore, release manifest and final software/field release gates.
# Responsibilities
Provide auditable recovery procedures and a machine-readable release decision.
# Definitions
| Term | Definition |
|---|---|
| Software release ready | All required software reviews are APPROVED. |
| Field release ready | Software ready and all required Phase-0 assumptions VERIFIED. |
# Interfaces
Consumes approved M5.1-M5.5 outputs and deployment package; produces runbook and release manifest.
# Constraints
Phase-0 evidence SHALL NOT be inferred from software tests.
# Normative Requirements
- **MOD-OPERATIONS-RELEASE-CANDIDATE-001:** Backup SHALL use a consistent SQLite backup and record SHA-256.
- **MOD-OPERATIONS-RELEASE-CANDIDATE-002:** Restore SHALL verify checksum and database integrity before atomic replacement.
- **MOD-OPERATIONS-RELEASE-CANDIDATE-003:** Operations documentation SHALL cover install, startup, shutdown, restart, upgrade, rollback, backup, restore and incident recovery.
- **MOD-OPERATIONS-RELEASE-CANDIDATE-004:** Release manifest SHALL include version, revision, package checksum/size, configuration schema version, repository migration state and M5 review decisions.
- **MOD-OPERATIONS-RELEASE-CANDIDATE-005:** Any non-APPROVED required review SHALL block software release readiness.
- **MOD-OPERATIONS-RELEASE-CANDIDATE-006:** Any required Phase-0 assumption not VERIFIED SHALL block field release readiness without blocking an otherwise valid software-ready decision.
- **MOD-OPERATIONS-RELEASE-CANDIDATE-007:** Release blockers SHALL be explicit and machine-readable.
- **MOD-OPERATIONS-RELEASE-CANDIDATE-008:** M5.6 SHALL NOT redefine M4 domain semantics or mark field evidence verified.
# Failure Modes
| Failure | Required behavior |
|---|---|
| Backup checksum mismatch | Reject restore; preserve current database. |
| Backup integrity failure | Reject restore; preserve current database. |
| Incomplete software review | Block software and field release. |
| Unverified Phase 0 | Permit software-ready only; block field release. |
# Traceability
Derived from MILESTONE-M5-005, -010 and -012.
# Acceptance Criteria
Tests prove backup/restore and both release-gate states; runbook is repository controlled.
# Review Questions
1. Are release blockers fail-closed? 2. Is field evidence kept distinct from software evidence?
# Change History
| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-07 | Initial M5.6 contract. |
| 1.0.1 | 2026-08-07 | Added concept tags and clarified re-review status after M5.6 findings. |
