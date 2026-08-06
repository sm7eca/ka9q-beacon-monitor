---
id: AKB-META
title: AKB Meta-Model and Governance
version: 1.0.3
status: DRAFT_FOR_RE_REVIEW
owner: Architecture Board
type: knowledge
normative: true
depends_on: [AKB-SCHEMA]
provides:
  - normative-language-policy
  - document-governance
consumes:
  - schema-contract
review:
  required: true
  passes: [consistency, completeness, governance, traceability]
change_control:
  approval: Architecture Board
  mechanism: ADR
---

# Purpose

Define governance and interpretation rules for the KA9Q VHF Beacon Monitor Architecture Knowledge Base (AKB).

# Scope

This contract governs every file listed in `MANIFEST.yaml` and every future file admitted to the AKB baseline. Structural syntax and identifier classes are owned by `AKB-SCHEMA`.

# Responsibilities

- Define document-type semantics.
- Define normative language.
- Define change-control and precedence rules.
- Ensure that every normative concept has one authoritative definition.

# Definitions

| Term | Definition |
|---|---|
| AKB | The authoritative Architecture Knowledge Base for the system. |
| Baseline | A reviewed and approved version of the AKB used for implementation. |
| Normative statement | A statement containing SHALL, SHALL NOT, SHOULD, SHOULD NOT, or MAY. |
| Contract | A document that defines required behavior, interfaces, or governance. |
| Knowledge document | A document that defines context or interpretation without defining executable behavior. |
| Entity document | A document that defines a normative data object and its invariants. |
| Decision document | An ADR that authorizes a change to architecture or design policy. |

# Normative Requirements

```yaml
requirements:
  - id: AKB-META-001
    statement: Every AKB document SHALL have a stable identifier declared in YAML front matter.
    verification: schema-validation
  - id: AKB-META-002
    statement: Every normative AKB document SHALL declare version, status, owner, type, dependencies, concept tags, and review passes.
    verification: schema-validation
  - id: AKB-META-003
    statement: Requirement keywords SHALL be interpreted according to RFC 2119 and RFC 8174 when written in uppercase.
    verification: document-review
  - id: AKB-META-004
    statement: Architecture changes SHALL be authorized by an approved ADR before affected contracts are baselined.
    verification: governance-review
  - id: AKB-META-005
    statement: A normative concept SHALL have exactly one normative definition location.
    verification: cross-reference-audit
  - id: AKB-META-006
    statement: Derived Word, PDF, HTML, API, and code artifacts SHALL NOT override AKB source files.
    verification: release-audit
  - id: AKB-META-007
    statement: Unverified KA9Q behavior SHALL be marked NEEDS_VERIFICATION and SHALL NOT be represented as guaranteed behavior.
    verification: technical-review
  - id: AKB-META-008
    statement: Formal stable identifiers SHALL conform to the identifier grammar defined by AKB-SCHEMA.
    verification: schema-validation
```

# Interfaces

```yaml
interfaces:
  inputs:
    - manifest
    - schema-contract
    - akb-documents
  outputs:
    - validated-knowledge-graph
    - traceability-graph
    - review-input-set
  external_standards:
    - RFC2119
    - RFC8174
```

# Constraints

- Markdown SHALL be UTF-8.
- YAML front matter SHALL be valid YAML 1.2.
- References SHALL use stable identifiers, not filenames alone.
- Duplicate normative definitions are prohibited.
- Narrative rationale MAY be included but SHALL be clearly separated from normative requirements.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Duplicate stable ID | Baseline validation SHALL fail. |
| Missing dependency | Baseline validation SHALL fail. |
| Unresolved normative reference | Baseline validation SHALL fail. |
| Conflicting normative statements | Review status SHALL become RE_REVIEW_REQUIRED. |
| Unverified external behavior stated as fact | Finding severity SHALL be at least HIGH. |

# Traceability

```yaml
traceability:
  governs:
    - AKB-README
    - AKB-STATUS
    - AKB-REVIEW
    - AKB-TRACE
  governed_by:
    - AKB-SCHEMA
  verified_by:
    - TEST-AKB-SCHEMA
    - TEST-AKB-XREF
```

# Review Questions

1. Are governance responsibilities separated from syntax owned by AKB-SCHEMA?
2. Can a validator detect duplicate IDs and missing dependencies?
3. Is precedence between AKB source and generated artifacts explicit?
4. Are assumptions about KA9Q clearly separated from verified facts?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial M1 foundation contract. |
| 1.0.1 | 2026-08-06 | Moved identifier and structural schema rules to AKB-SCHEMA; addressed AKB-F-004 and AKB-F-005. |
| 1.0.2 | 2026-08-06 | Aligned Foundation metadata with M1.2 entry-order validation. |
