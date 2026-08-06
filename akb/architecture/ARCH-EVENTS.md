---
id: ARCH-EVENTS
title: Event and Command Architecture
version: 1.0.1
status: DRAFT_FOR_RE_REVIEW
owner: Software Architecture
type: architecture
normative: true
depends_on:
  - CTX-GLOSSARY
  - ARCH-PRINCIPLES
  - ARCH-RUNTIME
provides:
  - event-model
  - command-model
  - event-catalog
consumes:
  - runtime-component-model
review:
  required: true
  passes:
    - runtime-determinism
    - module-interface-completeness
    - failure-and-recovery
---

# Purpose

Define the distinction between Events and Commands, mandatory event metadata, ownership rules, and the architecture-level event catalog used by runtime components.

# Scope

This contract defines event semantics and catalog names. Detailed payload field schemas belong to M3 data-model contracts and detailed producer/consumer signatures belong to M4 module contracts.

# Responsibilities

- Ensure Events represent facts that already occurred.
- Ensure Commands represent requests to attempt work.
- Provide stable event names and ownership.
- Prevent cyclic command/event semantics and hidden synchronous coupling.

# Definitions

Terms are governed by `CTX-GLOSSARY`.

# Normative Requirements

## ARCH-EVENTS-001 — Event Immutability

An Event SHALL be immutable after publication.

## ARCH-EVENTS-002 — Event Identity

Each Event SHALL have a stable event type, unique event identifier, source component, source timestamp, publication timestamp, and schema version.

## ARCH-EVENTS-003 — Command Semantics

A Command SHALL request an action and SHALL NOT assert that the action succeeded.

## ARCH-EVENTS-004 — Completion Facts

Successful, failed, timed-out, rejected, or cancelled command outcomes SHALL be represented by Events.

## ARCH-EVENTS-005 — Delivery Expectations

The in-process Event Bus SHALL provide at-least-once delivery semantics unless a later module contract explicitly defines a stronger local guarantee.

## ARCH-EVENTS-006 — Idempotent Consumers

Consumers of persistence-relevant Events SHALL be idempotent using the event's natural or explicit idempotency key.

## ARCH-EVENTS-007 — Ordering

Ordering SHALL be guaranteed only within an explicitly documented partition, such as one beacon or one verification request. Global ordering SHALL NOT be assumed.

## ARCH-EVENTS-008 — Failure Isolation

A failing subscriber SHALL NOT prevent unrelated subscribers from receiving Events.

## ARCH-EVENTS-009 — No Raw Array Payloads

Events SHALL NOT carry unbounded PCM or IQ arrays. Verification streams SHALL be referenced or consumed through dedicated stream interfaces.

## ARCH-EVENTS-010 — Event Versioning

Breaking event-payload changes SHALL require a new schema version and compatibility handling.

## ARCH-EVENTS-011 — Catalog Ownership

This document SHALL be the single normative definition owner for architecture-level Event and Command names. Other architecture documents SHALL reference these catalogs and SHALL NOT define alternative names.

## ARCH-EVENTS-012 — Runtime Coverage

Every Event produced by a component listed in `ARCH-RUNTIME` SHALL appear in the Event Catalog or be explicitly excluded with rationale. Every Command named by `ARCH-RUNTIME` SHALL appear in the Command Catalog.

# Event Catalog

| Event | Producer | Meaning |
|---|---|---|
| `StatusSampleReceived` | Status Receiver | A valid normalized KA9Q Status Sample was accepted. |
| `StatusDatagramRejected` | Status Receiver | A status datagram was rejected as malformed or unusable. |
| `ChannelBecameStale` | Status Cache | A logical channel exceeded its freshness limit. |
| `ChannelRecovered` | Status Cache | A stale channel received fresh valid status again. |
| `MeasurementWindowOpened` | Window Manager | A beacon window began. |
| `MeasurementWindowClosed` | Window Manager | A beacon window reached its normative end. |
| `ObservationCreated` | Observation Builder | Exactly one Observation was created for a beacon window. |
| `ClassificationChanged` | Classifier | The current operational state changed. |
| `VerificationQueued` | Verification Scheduler | A verification request entered the bounded queue. |
| `VerificationStarted` | Verification Worker | Verification processing began. |
| `VerificationCompleted` | Verifier | Approved verification evidence was produced. |
| `VerificationUnavailable` | Verifier | Verification could not be completed. |
| `ObservationPersisted` | Repository Writer | An Observation was committed idempotently. |
| `PersistenceBackpressureChanged` | Repository Writer | Persistence pressure state changed. |
| `IntervalSummaryCompleted` | Aggregator | One beacon summary was completed for one interval. |
| `HealthChanged` | Health Registry | Component or system Health State changed. |
| `RetentionCompleted` | Retention Job | One retention run completed. |

# Command Catalog

| Command | Issuer | Intended handler |
|---|---|---|
| `RequestVerification` | Classifier, scheduler, operator tooling | Verification Scheduler |
| `CancelVerification` | Shutdown or scheduler | Verification Scheduler |
| `PersistObservation` | Observation pipeline | Repository Writer |
| `RecomputeInterval` | Aggregator recovery or operator tooling | Aggregator |
| `RunRetention` | Retention scheduler or operator tooling | Retention Job |
| `RefreshConfiguration` | Operator tooling | Configuration Manager, if later approved |

# Event Relationships

```text
StatusSampleReceived
  -> MeasurementWindowClosed
  -> ObservationCreated
  -> PersistObservation command
  -> ObservationPersisted
  -> IntervalSummaryCompleted

ObservationCreated
  -> optional RequestVerification command
  -> VerificationQueued
  -> VerificationStarted
  -> VerificationCompleted | VerificationUnavailable
```

# Interfaces

```yaml
transport: in-process-event-bus
persistence: events-are-not-primary-system-of-record
payload_owner: later-data-model-contracts
```

# Constraints

- Event names SHALL be stable identifiers in later schemas.
- Event payloads SHALL reference beacon, window, interval, channel, or request identifiers explicitly.
- Events SHALL avoid embedding mutable service objects.
- Commands SHALL include deadline or timeout metadata when work is time-sensitive.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Subscriber exception | Isolate, report health, continue other delivery. |
| Duplicate event delivery | Idempotent consumer prevents duplicate persisted result. |
| Out-of-order event across beacons | Consumers SHALL NOT assume global order. |
| Unknown event version | Reject or route to compatibility handler; never silently reinterpret. |
| Event queue pressure | Apply bounded policy and expose health degradation. |

# Traceability

```yaml
governed_by:
  - ARCH-PRINCIPLES-014
  - ARCH-RUNTIME
verified_by:
  - TEST-M2-EVENT-CATALOG
```

# Review Questions

- Is every catalog item a fact or a command, not both?
- Are ordering assumptions explicit?
- Can duplicate delivery corrupt persistence?
- Are large stream payloads excluded?
- Are outcome events defined for all commands?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial event and command architecture. |
| 1.0.1 | 2026-08-06 | Established canonical catalog ownership and runtime coverage rule. |
