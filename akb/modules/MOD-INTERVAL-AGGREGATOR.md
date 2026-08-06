---
id: MOD-INTERVAL-AGGREGATOR
title: Interval Aggregator
version: 1.0.0
status: DRAFT_FOR_REVIEW
type: contract
owner: Architecture
normative: true
depends_on:
  - DM-OBSERVATION
  - DM-INTERVAL-SUMMARY
  - ARCH-RUNTIME
verified_by:
  - TEST-MOD-INTERVAL-AGGREGATOR
provides:
  - interval-summary-aggregation
consumes:
  - observation
review:
  required: true
  passes:
    - contract-to-code
    - deterministic-aggregation
    - concurrency-safety
    - failure-mode-analysis
    - test-traceability
---

# Purpose

Define the runtime contract for converting accepted `Observation` objects into aligned `IntervalSummary` objects.

# Scope

The module owns buffering, half-hour alignment, deterministic closure, late-observation rejection, duplicate-window rejection, and invocation of the normative `IntervalSummary.from_observations` factory. It does not persist, classify, verify, receive network traffic, or render web content.

# Interfaces

Consumes `Observation`. Delivers `IntervalSummary` to an injected handler. Event envelopes are owned by the future event-bus integration layer.

# Requirements

- **MOD-INTERVAL-AGGREGATOR-001:** Intervals SHALL be UTC-aligned, non-overlapping, and default to 1800 seconds.
- **MOD-INTERVAL-AGGREGATOR-002:** State SHALL be independent per `beacon_id`.
- **MOD-INTERVAL-AGGREGATOR-003:** Every accepted observation SHALL belong to exactly one emitted interval.
- **MOD-INTERVAL-AGGREGATOR-004:** Duplicate observations with the same beacon and `window_start_utc` SHALL be rejected.
- **MOD-INTERVAL-AGGREGATOR-005:** Observations for an already closed interval SHALL be rejected without mutating open state.
- **MOD-INTERVAL-AGGREGATOR-006:** `advance_time` SHALL close every open interval whose end is less than or equal to the supplied UTC time.
- **MOD-INTERVAL-AGGREGATOR-007:** Empty intervals SHALL NOT be synthesized.
- **MOD-INTERVAL-AGGREGATOR-008:** `flush` SHALL emit in deterministic `(interval_start_utc, beacon_id)` order.
- **MOD-INTERVAL-AGGREGATOR-009:** Calls SHALL be serialized per beacon so concurrent observations cannot be lost.
- **MOD-INTERVAL-AGGREGATOR-010:** Summary-handler failures SHALL be isolated, counted, and SHALL NOT prevent later intervals from closing.
- **MOD-INTERVAL-AGGREGATOR-011:** Summary calculations SHALL delegate to `DM-INTERVAL-SUMMARY`; this module SHALL NOT redefine classification thresholds or statistics.
- **MOD-INTERVAL-AGGREGATOR-012:** The module SHALL contain no persistence, network, DSP, verification, or presentation logic.

# Failure Modes

| Condition | Required behavior |
|---|---|
| Naive or non-UTC `advance_time` | Reject before state mutation |
| Duplicate observation window | Reject and increment rejection counter |
| Late observation for closed interval | Reject and preserve closed state |
| Summary handler raises | Count, report if possible, mark interval closed |
| Error handler raises | Suppress and continue |
| Concurrent same-beacon calls | Serialize without data loss |

# Traceability

`TEST-MOD-INTERVAL-AGGREGATOR` SHALL exercise every normative requirement and failure mode.

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial M4.6 contract. |
