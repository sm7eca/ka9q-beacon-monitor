---
id: ARCH-RUNTIME
title: Runtime Architecture
version: 1.0.2
status: DRAFT_FOR_RE_REVIEW
owner: Software Architecture
type: architecture
normative: true
depends_on:
  - CTX-SYSTEM
  - CTX-GLOSSARY
  - ARCH-PRINCIPLES
  - ARCH-KA9Q
provides:
  - runtime-component-model
  - processing-pipeline
  - concurrency-model
  - degradation-model
consumes:
  - status-path-contract
  - verification-path-contract
review:
  required: true
  passes:
    - runtime-determinism
    - failure-and-recovery
    - capacity-and-performance
---

# Purpose

Define the runtime components, normal processing pipeline, concurrency boundaries, time-window behavior, selective verification scheduling, backpressure, and shutdown/recovery model.

# Scope

This contract defines architecture-level component responsibilities and interactions. Exact class signatures and implementation libraries belong to later module contracts.

# Responsibilities

The runtime architecture SHALL provide:

- one status-ingestion path;
- immutable event publication;
- latest-status caching;
- per-beacon Measurement Window construction;
- one Observation per fixed ten-second window;
- deterministic classification;
- bounded persistence and verification work;
- fixed thirty-minute aggregation;
- API and health publication;
- isolated recovery for channel and downstream failures.

# Definitions

Terms are governed by `CTX-GLOSSARY`.

# Runtime Components

| Component | Primary responsibility |
|---|---|
| Status Receiver | Join KA9Q multicast, parse datagrams, normalize channel status. |
| Event Bus | Publish immutable runtime facts to subscribed components. |
| Status Cache | Retain latest normalized status per logical channel with freshness metadata. |
| Measurement Window Manager | Build fixed ten-second windows per beacon from Signal and Reference Channel Status Samples. |
| Observation Builder | Produce exactly one Observation, including NO_DATA, per beacon per window. |
| Classifier | Map evidence to detection and presentation states using deterministic rules. |
| Verification Scheduler | Prioritize and bound verification work. |
| Verifiers | Produce tone, CW, frequency, interference, or identity evidence. |
| Repository Writer | Persist Observations and summaries idempotently. |
| Aggregator | Produce one thirty-minute Interval Summary per beacon. |
| Health Registry | Maintain component and system health facts. |
| API Service | Publish current, historical, and health views. |
| Retention Job | Remove or archive records according to policy. |

# Normative Requirements

## ARCH-RUNTIME-001 — Processing Order

The normal runtime flow SHALL be:

```text
Status Receiver -> Event Bus -> Status Cache -> Measurement Window Manager
-> Observation Builder -> Classifier -> Repository -> Aggregator -> API
```

## ARCH-RUNTIME-002 — Fixed Window Alignment

Measurement Windows SHALL be aligned to UTC ten-second boundaries and SHALL use half-open intervals.

## ARCH-RUNTIME-003 — Exactly One Observation

Exactly one Observation SHALL be created per enabled beacon per Measurement Window, including windows that result in `NO_DATA`.

## ARCH-RUNTIME-004 — Window Minimum Evidence

A non-`NO_DATA` Observation SHALL require at least one fresh Signal Channel Status Sample and at least one fresh Reference Channel Status Sample during the window.

## ARCH-RUNTIME-005 — Window Quality

A window with incomplete expected coverage but satisfying the minimum evidence rule MAY produce an Observation with reduced Measurement Quality.

## ARCH-RUNTIME-006 — Complete Reference Evidence

A window with fresh evidence from both Reference Channels MAY qualify for full reference-availability quality, subject to gain, overload, timestamp, and coverage checks.

## ARCH-RUNTIME-007 — No Carry-Forward as Fresh

Status from a prior Measurement Window SHALL NOT be counted as fresh evidence in the current window.

## ARCH-RUNTIME-008 — Verification Triggering

Verification SHALL be triggered by explicit policy, including new signal appearance, ambiguous classification, interference suspicion, scheduled identity checks, or operator diagnostics.

## ARCH-RUNTIME-009 — Verification Budget

Verification work SHALL use a bounded priority queue, a configurable maximum concurrency, and a configurable rate limit.

## ARCH-RUNTIME-010 — Classification Update

A fresh approved verification result MAY enrich or replace the Classification SNR and identity state for the applicable observation or subsequent observations according to later data contracts.

## ARCH-RUNTIME-011 — Bounded Persistence Queue

The persistence queue SHALL be bounded. Overflow behavior SHALL be explicit, observable, and tested.

## ARCH-RUNTIME-012 — Per-Beacon Isolation

Each beacon's window and classification processing SHALL be independently recoverable.

## ARCH-RUNTIME-013 — Idempotent Time Keys

Observations SHALL use `(beacon_id, window_start_utc)` as their natural idempotency key. Interval Summaries SHALL use `(beacon_id, interval_start_utc)`.

## ARCH-RUNTIME-014 — Aggregation Timing

Aggregation SHALL execute after each fixed thirty-minute interval with a bounded completion delay.

## ARCH-RUNTIME-015 — Graceful Shutdown

Shutdown SHALL stop new work, stop status ingestion, finish or cancel verification according to policy, drain persistence within a bounded timeout, close storage, and terminate cleanly.

## ARCH-RUNTIME-016 — Recovery

Restart SHALL reconstruct current state from configuration and persisted data without creating duplicate Observations or Interval Summaries.

## ARCH-RUNTIME-017 — Health Propagation

Component failures and degraded evidence SHALL be reflected in Health State without requiring the complete process to fail.

## ARCH-RUNTIME-018 — Canonical Event Catalog

`ARCH-EVENTS` SHALL be the single normative owner of runtime Event and Command names. This document SHALL reference that catalog and SHALL NOT introduce an unregistered Event or Command name.

# Concurrency Model

```text
Task: status receive loop
Task: event dispatch
Task group: per-beacon measurement windows
Task: bounded repository writer
Task: aggregator scheduler
Task group: bounded verification workers
Task: API server
Task: retention scheduler
```

CPU-intensive verification MAY run in worker threads or processes. It SHALL NOT block status ingestion or measurement-window closure.

# Backpressure Model

| Resource | Required control |
|---|---|
| Status events | Bounded queue or latest-value coalescing. |
| Persistence | Bounded queue and explicit overflow policy. |
| Verification requests | Priority queue, concurrency cap, rate limit. |
| API history requests | Query range and response-size limits. |

# Interfaces

```yaml
event_catalog_owner: ARCH-EVENTS
publishes:
  - StatusSampleReceived
  - StatusDatagramRejected
  - ChannelBecameStale
  - ChannelRecovered
  - MeasurementWindowOpened
  - MeasurementWindowClosed
  - ObservationCreated
  - ClassificationChanged
  - VerificationQueued
  - VerificationStarted
  - VerificationCompleted
  - VerificationUnavailable
  - ObservationPersisted
  - PersistenceBackpressureChanged
  - IntervalSummaryCompleted
  - HealthChanged
  - RetentionCompleted
issues_commands:
  - RequestVerification
  - CancelVerification
  - PersistObservation
  - RecomputeInterval
  - RunRetention
consumes:
  - KA9Q-status-multicast
  - KA9Q-verification-streams
```

# Constraints

- Correctness SHALL be independent of exact status packet rate.
- Wall-clock jumps SHALL NOT silently create duplicate or overlapping windows.
- All retries SHALL have limits and observability.
- API work SHALL NOT directly mutate radio configuration in the first baseline.

# Failure Modes

| Failure | Required runtime behavior |
|---|---|
| Status receiver stops | Restart with backoff; windows produce NO_DATA as necessary. |
| Event subscriber fails | Isolate subscriber; preserve ingestion. |
| One beacon processor fails | Restart only affected beacon processor. |
| Persistence slow | Buffer within bounds; expose pressure. |
| Persistence unavailable | Retry within policy; preserve bounded memory. |
| Verification timeout | Complete request as unavailable; preserve status result. |
| Window timer delayed | Close by normative UTC boundaries; report lateness. |
| Aggregator delayed | Re-run idempotently for missing interval. |

# Traceability

```yaml
governed_by:
  - ARCH-PRINCIPLES
  - ARCH-KA9Q
supports:
  - CTX-SYSTEM-008
  - CTX-SYSTEM-009
  - CTX-SYSTEM-010
verified_by:
  - TEST-M2-DEPENDENCY-GRAPH
```

# Review Questions

- Is exactly-one-observation behavior unambiguous?
- Are minimum evidence and degraded windows distinct?
- Are all queues and worker pools bounded?
- Can one beacon fail independently?
- Is shutdown and restart idempotent?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial runtime architecture. |
| 1.0.1 | 2026-08-06 | Reconciled published Events and Commands with the canonical ARCH-EVENTS catalogs. |
| 1.0.2 | 2026-08-06 | Added CancelVerification to the runtime command interface and prepared the M2.1.1 package release. |
