---
id: AKB-SCHEMA
title: AKB Document and Identifier Schema
version: 1.0.3
status: DRAFT_FOR_RE_REVIEW
owner: Architecture Board
type: contract
normative: true
depends_on: []
provides:
  - schema-contract
  - stable-identifier-grammar
  - concept-tag-grammar
  - reference-resolution-policy
consumes:
  - manifest
review:
  required: true
  passes: [schema, consistency, traceability]
change_control:
  approval: Architecture Board
  mechanism: ADR
---

# Purpose

Define the machine-readable structure, identifier classes, reference semantics, and validation rules for all AKB documents and artifacts.

# Scope

Applies to `MANIFEST.yaml`, Markdown front matter, embedded normative YAML blocks, stable identifiers, concept tags, and cross-document references.

# Responsibilities

- Define formal stable identifiers.
- Define concept tags used by `provides` and `consumes`.
- Define required front-matter fields.
- Define existing, planned, external, and unknown reference states.
- Define baseline validation outcomes.

# Definitions

| Term | Definition |
|---|---|
| Stable identifier | A formal reference key that SHALL remain unchanged when a file is moved or renamed. |
| Concept tag | A lowercase descriptive label used for discovery and semantic indexing; it is not a reference target. |
| Existing artifact | An object registered in `documents` or as the manifest schema document. |
| Planned artifact | An object registered in `planned_documents` or `planned_artifacts`; references to it resolve but are not yet executable. |
| External reference | A registered reference to a review finding, external standard, or external source. |
| Unknown reference | A reference not registered in any allowed manifest registry. |

# Normative Requirements

```yaml
requirements:
  - id: AKB-SCHEMA-001
    statement: Stable identifiers SHALL be ASCII and SHALL match ^[A-Z][A-Z0-9-]*$.
    verification: schema-validation
  - id: AKB-SCHEMA-002
    statement: Concept tags SHALL be ASCII lowercase and SHALL match ^[a-z][a-z0-9-]*$.
    verification: schema-validation
  - id: AKB-SCHEMA-003
    statement: The provides and consumes front-matter fields SHALL contain concept tags only.
    verification: schema-validation
  - id: AKB-SCHEMA-004
    statement: depends_on, governs, governed_by, verified_by, source_id, and target_id SHALL contain stable identifiers only.
    verification: cross-reference-audit
  - id: AKB-SCHEMA-005
    statement: Every normative reference SHALL resolve to an existing artifact, planned artifact, or registered external reference.
    verification: cross-reference-audit
  - id: AKB-SCHEMA-006
    statement: An unknown normative reference SHALL fail baseline validation.
    verification: cross-reference-audit
  - id: AKB-SCHEMA-007
    statement: A planned verification artifact MAY satisfy reference resolution during design authoring but SHALL NOT satisfy an executable acceptance gate until implemented.
    verification: release-audit
  - id: AKB-SCHEMA-008
    statement: Every normative Markdown document SHALL contain all required sections declared in MANIFEST.yaml.
    verification: document-structure-audit
  - id: AKB-SCHEMA-009
    statement: Every explicit entry-point sequence SHALL place each document after all documents listed in its depends_on field.
    verification: entry-point-dependency-audit
```

# Interfaces

```yaml
identifier_classes:
  stable_identifier:
    regex: "^[A-Z][A-Z0-9-]*$"
    examples: [AKB-META, MOD-CLASSIFIER, TEST-AKB-XREF]
  concept_tag:
    regex: "^[a-z][a-z0-9-]*$"
    examples: [document-governance, runtime-event, traceability-model]

entry_point_dependency_rule:
  id: RULE-013
  name: Entry Point Dependency Rule
  condition: Every dependency of an entry-point document appears earlier in the same sequence.
  failure: ENTRY_ORDER_ERROR

reference_states:
  EXISTING: registered and supplied
  PLANNED: registered but not yet supplied
  EXTERNAL: registered outside the AKB artifact graph
  UNKNOWN: not registered; validation failure
```

# Constraints

- Stable identifiers SHALL NOT contain periods, underscores, whitespace, or lowercase letters.
- Version numbers belong in the `version` property and SHALL NOT be encoded as dotted suffixes in stable IDs.
- Concept tags SHALL NOT be used as `target_id` values.
- File paths are navigational data, not identifiers.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Stable ID violates grammar | Schema validation SHALL fail. |
| Concept tag violates grammar | Schema validation SHALL fail. |
| Concept tag used as target ID | Cross-reference validation SHALL fail. |
| Unknown reference | Baseline validation SHALL fail. |
| Planned test used as proof of execution | Acceptance validation SHALL fail until test status is IMPLEMENTED. |
| Entry-point document precedes a declared dependency | Entry-order validation SHALL fail with `ENTRY_ORDER_ERROR`. |

# Traceability

```yaml
traceability:
  governs:
    - AKB-META
    - AKB-README
    - AKB-STATUS
    - AKB-REVIEW
    - AKB-TRACE
  verified_by:
    - TEST-AKB-SCHEMA
    - TEST-AKB-XREF
    - TEST-AKB-ENTRY-ORDER
```

# Review Questions

1. Are stable IDs and concept tags unambiguously distinguishable?
2. Can every normative reference be classified as EXISTING, PLANNED, EXTERNAL, or UNKNOWN?
3. Does the schema prevent planned tests from being mistaken for executed evidence?
4. Can the validator apply these rules without domain-specific interpretation?
5. Are all explicit entry-point sequences topologically consistent with document dependencies?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Added in M1.1 to centralize schema and identifier rules. |
| 1.0.2 | 2026-08-06 | Added RULE-013 and normative entry-point dependency validation. |
