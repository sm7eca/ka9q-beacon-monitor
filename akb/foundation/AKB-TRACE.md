---
id: AKB-TRACE
title: Requirements and Design Traceability Contract
version: 1.0.3
status: DRAFT_FOR_RE_REVIEW
owner: Architecture Board
type: contract
normative: true
depends_on: [AKB-META, AKB-SCHEMA, AKB-README, AKB-STATUS, AKB-REVIEW]
provides:
  - traceability-model
  - trace-link-types
  - completeness-rules
consumes:
  - requirements
  - adrs
  - modules
  - tests
review:
  required: true
  passes: [traceability, consistency, completeness]
change_control:
  approval: Architecture Board
  mechanism: ADR
---

# Purpose

Define the machine-readable links connecting requirements, architecture decisions, entities, modules, interfaces, tests, acceptance criteria, and operational controls.

# Scope

This contract applies to all normative AKB objects and closes the process gap in which an AI review package could not verify numbered FR/NFR requirements.

# Responsibilities

- Define permitted trace-link types.
- Define traceability completeness criteria.
- Define orphan and conflict detection.
- Ensure every requirement can be followed to implementation ownership and verification.

# Definitions

```yaml
link_types:
  refines: higher-level contract to lower-level contract
  satisfies: implementation contract to requirement
  implements: module to interface or behavior
  verifies: test to requirement or invariant
  governed_by: contract to ADR or policy
  consumes: module to entity or interface
  produces: module to entity or event
  mitigates: control to risk or failure mode
  supersedes: newer object to older object
```

# Normative Requirements

```yaml
requirements:
  - id: AKB-TRACE-001
    statement: Every FR and NFR SHALL have exactly one normative definition.
    verification: traceability-audit
  - id: AKB-TRACE-002
    statement: Every FR and NFR SHALL link to at least one architecture or module contract and at least one verification artifact.
    verification: traceability-audit
  - id: AKB-TRACE-003
    statement: Every module SHALL link to the requirements it satisfies and the entities or interfaces it consumes and produces.
    verification: traceability-audit
  - id: AKB-TRACE-004
    statement: Every acceptance criterion SHALL link to at least one requirement and one executable or manual verification procedure.
    verification: traceability-audit
  - id: AKB-TRACE-005
    statement: Every ADR SHALL list the contracts and requirements it governs.
    verification: adr-audit
  - id: AKB-TRACE-006
    statement: Orphan requirements, orphan tests, unresolved IDs, and circular supersession chains SHALL fail baseline validation.
    verification: graph-validation
  - id: AKB-TRACE-007
    statement: The AI review package SHALL include a generated or source-level traceability table covering every FR and NFR.
    verification: package-completeness-check
```

# Interfaces

```yaml
trace_record:
  source_id: stable_identifier
  relation: link_type
  target_id: stable_identifier
  rationale: optional_string
  status: [ACTIVE, DEPRECATED, SUPERSEDED]

minimum_requirement_trace:
  - requirement_id
  - normative_source
  - governed_by_adr
  - satisfied_by_contract
  - verified_by_test
  - accepted_by_criterion
```

# Constraints

- Trace links SHALL use stable identifiers.
- Filenames MAY be included for navigation but SHALL NOT be authoritative.
- A requirement SHALL NOT be considered implemented solely because code exists.
- Generated traceability reports SHALL identify source version and manifest hash.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Requirement has no test | Baseline validation SHALL fail. |
| Test has no requirement or invariant | Test SHALL be marked exploratory or baseline validation SHALL fail. |
| Unknown target ID | Baseline validation SHALL fail. |
| Two normative sources define same requirement ID | Baseline validation SHALL fail. |
| Word and AKB numbering differ | AKB identifiers SHALL prevail; generated artifact SHALL be regenerated. |

# Traceability

```yaml
foundation_traceability:
  - source_id: AKB-META-001
    relation: verifies
    target_id: TEST-AKB-SCHEMA
  - source_id: AKB-TRACE-007
    relation: verifies
    target_id: TEST-AKB-PACKAGE-COMPLETE
  - source_id: AKB-STATUS-004
    relation: verifies
    target_id: TEST-AKB-ASSUMPTION-REGISTER
  - source_id: AKB-REVIEW-002
    relation: verifies
    target_id: TEST-REVIEW-SCHEMA
  - source_id: AKB-TRACE-007
    relation: mitigates
    target_id: AI-011
  - source_id: AKB-SCHEMA-009
    relation: verifies
    target_id: TEST-AKB-ENTRY-ORDER
```

# Review Questions

1. Can every future FR/NFR be followed to a module and a test?
2. Does the contract prevent the missing-normative-source problem from AI-011?
3. Are orphan requirements and tests detectable automatically?
4. Can changes be impact-analyzed through stable links?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial traceability contract. |
| 1.0.1 | 2026-08-06 | Registered planned verification artifacts and consolidated package-completeness ownership. |
| 1.0.2 | 2026-08-06 | Added entry-point dependency rule references and planned verification artifact. |
| 1.0.3 | 2026-08-06 | Added missing central traceability entry for TEST-AKB-ENTRY-ORDER. |
