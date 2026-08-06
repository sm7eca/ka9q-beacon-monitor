---
id: CTX-GLOSSARY
title: Normative Glossary
version: 1.0.1
status: DRAFT_FOR_RE_REVIEW
owner: Architecture Board
type: knowledge
normative: true
depends_on:
  - CTX-SYSTEM
provides:
  - normative-terminology
consumes:
  - system-purpose
review:
  required: true
  passes:
    - architecture-consistency
    - data-model-integrity
---

# Purpose

Provide the single normative definition location for cross-cutting terms used by M2 and later AKB contracts.

# Scope

Terms in this file govern architecture and later data, module, interface, operations, requirements, and test contracts. Detailed entity fields remain outside M2.

# Responsibilities

- Define each term once.
- Distinguish radio evidence, application classifications, and persistence units.
- Prevent use of ambiguous terms such as "sample", "signal", "heard", and "verified" without qualification.

# Definitions

| Term | Definition |
|---|---|
| Status Sample | One normalized set of KA9Q status values for one logical channel at one source timestamp. It is transient and not the primary persistence unit. |
| Signal Channel | Narrow KA9Q channel centered on a configured beacon frequency. |
| Reference Channel | Narrow KA9Q channel offset from the signal channel and used to estimate local noise or interference conditions. |
| Beacon Channel Set | One signal channel plus its configured lower and upper reference channels. |
| Measurement Window | Fixed ten-second interval that collects Status Samples for one Beacon Channel Set. |
| Observation | Exactly one persisted result for one beacon and one Measurement Window. |
| Interval Summary | Exactly one persisted aggregate for one beacon and one fixed thirty-minute interval. |
| Derived SNR | Status-path SNR calculated from signal-channel and reference-channel measurements. |
| Verification SNR | SNR produced by an approved PCM or IQ verification analysis. |
| Classification SNR | Verification SNR when a fresh approved verification exists; otherwise Derived SNR. |
| Signal Present | Evidence of energy in the expected channel without sufficient identity evidence. |
| Probable Beacon | Signal evidence compatible with the configured beacon but without completed identity verification. |
| Verified Beacon | Beacon identity supported by an approved verification level. |
| Degraded Mode | Explicit operating state in which processing continues with reduced evidence, quality, or availability. |
| Stale | Data older than the maximum age permitted by its contract. |
| Measurement Quality | Objective score or category based on coverage, reference availability, gain compatibility, overload state, and timestamp integrity. |
| Verification Quality | Objective measure of verification evidence sufficiency and freshness. |
| Identification Quality | Objective measure of how strongly evidence supports the configured beacon identity. |
| Verification Level 0 | Status-only evidence. |
| Verification Level 1 | Tone and narrowband verification from PCM or IQ. |
| Verification Level 2 | Keyed-CW timing or pattern verification. |
| Verification Level 3 | Morse identification verification. |
| Event | Immutable runtime message describing a fact that occurred. |
| Command | Request for a runtime component to attempt an action. |
| Health State | `HEALTHY`, `DEGRADED`, or `UNHEALTHY` operational state. |
| Fresh Evidence | Evidence whose age is within the maximum freshness interval defined by later contracts. |
| Complete Window | Measurement Window meeting the minimum evidence contract required to create a non-`NO_DATA` Observation. |
| `NO_DATA` | Observation classification indicating that the minimum evidence contract for the Measurement Window was not satisfied. It SHALL NOT be interpreted as proof that no RF energy was present. |
| Partial Reference Loss | Runtime condition where exactly one of the two normal reference channels is unavailable or stale. |

# Normative Requirements

## CTX-GLOSSARY-001

Later documents SHALL use the terms in this glossary without redefining their normative meaning.

## CTX-GLOSSARY-002

The unqualified word `sample` SHOULD NOT be used where `Status Sample`, PCM sample, or IQ sample is intended.

## CTX-GLOSSARY-003

The unqualified word `verified` SHALL NOT be used unless the applicable Verification Level and evidence source are known.

## CTX-GLOSSARY-004

`Heard` MAY be used only as a user-interface label mapped to a defined classification state; it SHALL NOT be the normative internal state name.

# Interfaces

```yaml
consumed_by:
  - ARCH-PRINCIPLES
  - ARCH-KA9Q
  - ARCH-RUNTIME
  - ARCH-EVENTS
```

# Constraints

- Terms SHALL remain implementation-independent.
- Field-level schemas SHALL be defined in M3 data-model contracts.
- Thresholds and timing parameters SHALL be owned by requirements or later design contracts.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Undefined term introduced | Review SHALL raise at least a Medium finding. |
| Existing term redefined | Baseline validation SHALL fail. |
| UI term used as internal state | Review SHALL require explicit mapping. |

# Traceability

```yaml
governs:
  - ARCH-PRINCIPLES
  - ARCH-KA9Q
  - ARCH-RUNTIME
  - ARCH-EVENTS
verified_by:
  - TEST-M2-BOUNDARY-CONSISTENCY
```

# Review Questions

- Does every cross-cutting term have one definition?
- Are radio evidence and application classifications distinct?
- Are temporary runtime objects distinguished from persisted objects?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial normative glossary. |
| 1.0.1 | 2026-08-06 | Added normative `NO_DATA` definition for M2-F-003. |
