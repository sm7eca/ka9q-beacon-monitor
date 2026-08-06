---
id: ARCH-PRINCIPLES
title: Architecture Principles
version: 1.0.1
status: DRAFT_FOR_RE_REVIEW
owner: Architecture Board
type: decision-policy
normative: true
depends_on:
  - CTX-SYSTEM
  - CTX-GLOSSARY
provides:
  - architecture-principles
  - design-constraints
consumes:
  - system-boundary
  - normative-terminology
review:
  required: true
  passes:
    - architecture-consistency
    - failure-and-recovery
    - testability-and-acceptance
---

# Purpose

Define the mandatory principles governing all later architecture, data, module, interface, operational, requirement, test, and implementation choices.

# Scope

These principles govern design choices but do not define detailed interfaces or algorithms.

# Responsibilities

- Constrain architecture to exploit KA9Q appropriately.
- Preserve deterministic data and time semantics.
- Separate transient radio evidence from persistent application results.
- Ensure failure isolation, explicit degradation, and testability.

# Definitions

Terms are governed by `CTX-GLOSSARY`.

# Normative Requirements

## ARCH-PRINCIPLES-001 — KA9Q Owns Continuous Low-Level DSP

KA9Q `radiod` SHALL own SDR access, frequency translation, channel filtering, decimation, demodulation, and continuous low-level signal measurements available through its status interface.

## ARCH-PRINCIPLES-002 — No Normal-Path DSP Duplication

The application SHALL NOT continuously reproduce KA9Q filtering, FFT, signal-power, or noise-density calculations for every monitored beacon.

## ARCH-PRINCIPLES-003 — Status-Driven Normal Path

The Status Path SHALL be the normal measurement path.

## ARCH-PRINCIPLES-004 — Selective Verification

PCM or IQ analysis SHALL occur only under explicit verification triggers, scheduled validation, diagnostics, or hardware-in-the-loop testing.

## ARCH-PRINCIPLES-005 — Evidence Before Interpretation

Radio evidence SHALL remain distinguishable from application classification and beacon identity conclusions.

## ARCH-PRINCIPLES-006 — Fixed Time Windows

The runtime SHALL produce one Observation per beacon per fixed ten-second Measurement Window and one Interval Summary per beacon per fixed thirty-minute interval.

## ARCH-PRINCIPLES-007 — UTC and Half-Open Intervals

Normative intervals SHALL use UTC and half-open boundaries `[start, end)`.

## ARCH-PRINCIPLES-008 — Explicit Degradation

Missing, stale, overloaded, incompatible, or partial evidence SHALL produce explicit quality and health degradation; it SHALL NOT be silently treated as full-quality evidence.

## ARCH-PRINCIPLES-009 — Per-Beacon Failure Isolation

A failure affecting one beacon or Beacon Channel Set SHALL NOT terminate processing for other beacons.

## ARCH-PRINCIPLES-010 — Bounded Resources

All queues, caches, verification concurrency, retry loops, and persistence buffers SHALL be bounded.

## ARCH-PRINCIPLES-011 — Idempotent Persistence

Observation and Interval Summary persistence SHALL be idempotent for their natural time keys.

## ARCH-PRINCIPLES-012 — Single Definition Ownership

Each normative concept, entity, interface, threshold, and state transition SHALL have exactly one normative definition owner.

## ARCH-PRINCIPLES-013 — Objective Quality Measures

The architecture SHALL use objective measurement, verification, and identification quality attributes rather than an undocumented aggregate confidence score.

## ARCH-PRINCIPLES-014 — Events Describe Facts

Events SHALL be immutable facts; requests to perform work SHALL be represented as Commands.

## ARCH-PRINCIPLES-015 — Explainable Classification

Each persisted classification SHALL include enough provenance to identify its measurement source, evidence quality, and reason.

## ARCH-PRINCIPLES-016 — External Assumptions Are Test Gates

Unverified KA9Q behavior SHALL be registered as a Phase 0 assumption and SHALL NOT become a hidden implementation dependency.

# Interfaces

```yaml
governs:
  - ARCH-KA9Q
  - ARCH-RUNTIME
  - ARCH-EVENTS
  - DM-STATUS-SAMPLE
  - DM-MEASUREMENT-WINDOW
  - DM-OBSERVATION
  - DM-INTERVAL-SUMMARY
  - DM-DATABASE
  - MOD-STATUS-RECEIVER
  - MOD-MEASUREMENT-WINDOW
  - MOD-CLASSIFIER
  - MOD-VERIFICATION-SCHEDULER
```

# Constraints

- Later contracts MAY specialize these principles but SHALL NOT contradict them without an approved ADR.
- Implementation performance optimizations SHALL preserve deterministic semantics.

# Failure Modes

| Violation | Required response |
|---|---|
| Continuous duplicate DSP introduced | Architecture review SHALL fail. |
| Unbounded queue or retry | Architecture review SHALL fail. |
| Hidden degraded operation | Test and operations review SHALL fail. |
| Same definition in multiple owners | Cross-reference review SHALL fail. |

# Traceability

```yaml
governs:
  - ARCH-KA9Q
  - ARCH-RUNTIME
  - ARCH-EVENTS
verified_by:
  - TEST-M2-BOUNDARY-CONSISTENCY
```

# Review Questions

- Does any later design duplicate KA9Q processing?
- Are all resources bounded?
- Are time, failure, and quality semantics deterministic?
- Is each normative concept owned once?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial architecture principles. |
| 1.0.1 | 2026-08-06 | Replaced unresolved DM-MODEL reference with registered specific data contracts. |
