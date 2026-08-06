---
id: AKB-README
title: AKB Entry Point and Navigation Contract
version: 1.0.3
status: DRAFT_FOR_RE_REVIEW
owner: Architecture Board
type: knowledge
normative: true
depends_on: [AKB-META, AKB-SCHEMA]
provides:
  - repository-entry-point
  - reading-order
  - consumer-rules
consumes:
  - manifest
review:
  required: true
  passes: [consistency, navigation, completeness]
change_control:
  approval: Architecture Board
  mechanism: ADR
---

# Purpose

Provide the deterministic entry point for human reviewers, AI reviewers, implementers, and generators consuming the AKB.

# Scope

This document defines repository purpose, reading order, consumer behavior, and package-level precedence.

# Responsibilities

- Direct all consumers to authoritative files.
- Prevent interpretation of isolated files without required dependencies.
- Define how humans and AI SHALL consume the AKB.
- Define package outputs and non-authoritative derived artifacts.

# Definitions

| Term | Definition |
|---|---|
| Consumer | A human or software system reading the AKB. |
| Generator | A tool producing code, tests, diagrams, or documents from AKB contracts. |
| Review package | The complete set of normative AKB files and the manifest used for one review. |

# Normative Requirements

```yaml
requirements:
  - id: AKB-README-001
    statement: Every consumer SHALL read MANIFEST.yaml, AKB-SCHEMA, and AKB-META before interpreting any other AKB document.
    verification: review-procedure
  - id: AKB-README-002
    statement: Consumers SHALL resolve dependencies by stable identifier.
    verification: cross-reference-audit
  - id: AKB-README-003
    statement: AI reviewers SHALL review only behavior present in the supplied review package and SHALL identify missing normative sources.
    verification: review-output-audit
  - id: AKB-README-004
    statement: AI reviewers SHALL NOT invent missing requirements, KA9Q fields, interface behavior, thresholds, or failure recovery rules.
    verification: review-output-audit
  - id: AKB-README-005
    statement: Generators SHALL preserve requirement IDs, ADR IDs, entity names, field names, and module identifiers exactly.
    verification: generated-artifact-audit
  - id: AKB-README-006
    statement: Word, PDF, HTML, diagrams, and generated code SHALL be treated as derived artifacts.
    verification: release-audit
  - id: AKB-README-007
    statement: AI review-package completeness SHALL be governed by AKB-TRACE-007.
    verification: cross-reference-audit
```

# Interfaces

```yaml
entry_points:
  human:
    - MANIFEST.yaml
    - AKB-SCHEMA
    - AKB-META
    - AKB-README
    - AKB-STATUS
    - AKB-REVIEW
    - AKB-TRACE
  ai:
    - MANIFEST.yaml
    - AKB-SCHEMA
    - AKB-META
    - AKB-README
    - AKB-STATUS
    - AKB-REVIEW
    - AKB-TRACE
```

# Constraints

- A partial review package SHALL declare itself partial.
- A review decision SHALL identify omitted normative documents.
- No file path SHALL be treated as a stable reference.
- The AKB language is English for normative content; localized derived documents MAY be generated.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Normative file missing from review package | Reviewer SHALL issue a package-completeness finding. |
| Dependency cycle | Baseline validation SHALL fail. |
| Generator changes stable IDs | Generated artifact SHALL be rejected. |
| Derived artifact conflicts with AKB | AKB SHALL prevail and conflict SHALL be reported. |

# Traceability

```yaml
traceability:
  requirements:
    - AKB-META-005
    - AKB-META-006
  governed_by:
    - AKB-TRACE
  verified_by:
    - TEST-AKB-PACKAGE-COMPLETE
    - TEST-AKB-DEPENDENCY-GRAPH
    - TEST-AKB-ENTRY-ORDER
```

# Review Questions

1. Can an AI determine the correct reading order without outside instructions?
2. Is the authoritative source of each concept discoverable?
3. Does the package prevent the process gap identified in AI-011?
4. Can generated artifacts be distinguished from normative source?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial deterministic entry-point contract. |
| 1.0.1 | 2026-08-06 | Replaced duplicated package-completeness definition with governance link to AKB-TRACE-007. |
| 1.0.2 | 2026-08-06 | Added AKB-SCHEMA to deterministic reading order before AKB-META and added entry-order verification. |
