---
id: AKB-REVIEW
title: Human and AI Review Contract
version: 1.0.3
status: DRAFT_FOR_RE_REVIEW
owner: Architecture Board
type: contract
normative: true
depends_on: [AKB-META, AKB-SCHEMA, AKB-README, AKB-STATUS]
provides:
  - review-process
  - finding-schema
  - decision-rules
consumes:
  - review-package
review:
  required: true
  passes: [reviewability, determinism, completeness]
change_control:
  approval: Architecture Board
  mechanism: ADR
---

# Purpose

Define a common review process and output schema for human and AI reviewers.

# Scope

Applies to architecture, requirements, data, modules, operations, interfaces, tests, and ADRs.

# Responsibilities

- Define mandatory review passes.
- Define finding severity and required evidence.
- Define decision rules.
- Prevent unsupported redesign or invention by AI reviewers.

# Definitions

| Term | Definition |
|---|---|
| CRITICAL | Unsafe, internally impossible, or blocks implementation entirely. |
| HIGH | Requires architecture or contract change before implementation. |
| MEDIUM | Required design clarification or robustness improvement. |
| LOW | Editorial, local, or low-impact improvement. |
| QUESTION | Domain decision or missing evidence; not a confirmed defect. |

# Normative Requirements

```yaml
requirements:
  - id: AKB-REVIEW-001
    statement: Every formal review SHALL execute all mandatory review passes.
    verification: review-report-audit
  - id: AKB-REVIEW-002
    statement: Every finding SHALL contain id, severity, section, category, finding, evidence, impact, recommendation, verification_test, and confidence.
    verification: schema-validation
  - id: AKB-REVIEW-003
    statement: Evidence SHALL reference supplied AKB identifiers and sections or explicitly identified external primary sources.
    verification: evidence-audit
  - id: AKB-REVIEW-004
    statement: AI reviewers SHALL distinguish source-derived facts, inference, and NEEDS_VERIFICATION assumptions.
    verification: review-output-audit
  - id: AKB-REVIEW-005
    statement: AI reviewers SHALL NOT silently correct missing contracts or assume undocumented KA9Q behavior.
    verification: review-output-audit
  - id: AKB-REVIEW-006
    statement: A review decision SHALL follow the decision rules in AKB-STATUS.
    verification: decision-audit
  - id: AKB-REVIEW-007
    statement: Review output SHALL include a machine-readable JSON findings object.
    verification: schema-validation
  - id: AKB-REVIEW-008
    statement: Every formal foundation review SHALL evaluate entry-point dependency consistency according to AKB-SCHEMA-009.
    verification: entry-point-dependency-audit
```

# Interfaces

```yaml
mandatory_review_passes:
  - architecture-consistency
  - requirement-traceability
  - dependency-graph-validation
  - runtime-determinism
  - data-model-integrity
  - module-interface-completeness
  - failure-and-recovery
  - capacity-and-performance
  - testability-and-acceptance

finding_schema:
  id: string
  severity: [CRITICAL, HIGH, MEDIUM, LOW, QUESTION]
  section: string
  category: string
  finding: string
  evidence: string
  impact: string
  recommendation: string
  verification_test: string
  confidence: number_0_to_1
```

# Constraints

- Reviewers SHALL use the complete package declared by `MANIFEST.yaml`.
- External technical verification SHALL use primary sources when possible.
- A reviewer MAY recommend alternatives but SHALL separate them from confirmed findings.
- Confidence SHALL reflect evidence quality, not rhetorical certainty.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Review omits mandatory pass | Review SHALL be considered incomplete. |
| Finding lacks evidence | Finding SHALL be downgraded to QUESTION or removed. |
| Review uses missing normative source | Package-completeness finding SHALL be raised. |
| AI invents requirement | Review output SHALL be rejected. |

# Traceability

```yaml
traceability:
  closes_prior_findings:
    - AI-011
  verified_by:
    - TEST-REVIEW-SCHEMA
    - TEST-REVIEW-DECISION-RULES
    - TEST-AKB-ENTRY-ORDER
```

# Review Questions

1. Does the process prevent unsupported AI invention?
2. Can review output be parsed and compared across versions?
3. Are package-completeness gaps reported explicitly?
4. Are design defects separated from process questions?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial human and AI review contract. |
| 1.0.1 | 2026-08-06 | Normalized definition table and added AKB-SCHEMA dependency. |
| 1.0.2 | 2026-08-06 | Added mandatory dependency-graph validation pass and entry-order audit. |
| 1.0.3 | 2026-08-06 | Delegated entry-point dependency consistency definition to AKB-SCHEMA-009. |
