---
id: CTX-SYSTEM
title: System Context
version: 1.0.1
status: DRAFT_FOR_RE_REVIEW
owner: Architecture Board
type: knowledge
normative: true
depends_on:
  - AKB-META
  - AKB-SCHEMA
  - AKB-README
provides:
  - system-purpose
  - system-boundary
  - actor-model
  - external-system-model
consumes:
  - foundation-governance
review:
  required: true
  passes:
    - architecture-consistency
    - requirement-traceability
    - failure-and-recovery
---

# Purpose

Define the operational purpose, system boundary, actors, external systems, primary use cases, goals, non-goals, assumptions, and high-level information flow for the KA9Q VHF Beacon Monitor.

# Scope

This contract covers the complete monitoring system from KA9Q status reception to published beacon reception summaries. It excludes detailed module design, persistent schema design, API field definitions, user-interface layout, and implementation code.

# Responsibilities

The system SHALL:

- observe ten configured VHF beacons continuously;
- use KA9Q `radiod` as the primary radio and low-level measurement engine;
- derive one observation per beacon per fixed ten-second measurement window;
- verify likely beacon detections selectively using PCM or IQ when required;
- aggregate observations into fixed thirty-minute summaries;
- publish current and historical results through a web-accessible API;
- expose health, stale-data, overload, and degraded-mode states;
- retain enough evidence to explain each published classification.

# Definitions

| Term | Definition |
|---|---|
| Beacon Monitor | The complete application described by this AKB. |
| Receiver Site | The physical site containing antenna, SDR, host, and KA9Q services. |
| KA9Q `radiod` | External radio-processing service that owns SDR access, tuning, filtering, demodulation, and status production. |
| Status Path | Normal measurement path using KA9Q status multicast. |
| Verification Path | Selective PCM or IQ path used to improve signal identity or quality evidence. |
| Operator | Person responsible for configuration, maintenance, and interpretation of results. |
| Consumer | Human or software client reading current or historical monitoring data. |

# Normative Requirements

## CTX-SYSTEM-001

The system SHALL monitor exactly the set of beacons enabled in configuration, up to a design target of at least ten simultaneous beacons.

## CTX-SYSTEM-002

The system boundary SHALL begin at receipt of KA9Q status or verification streams and SHALL end at storage, API publication, web presentation, and operational telemetry.

## CTX-SYSTEM-003

The SDR device, antenna system, RF filters, preamplifiers, operating system clock source, network infrastructure, and KA9Q installation SHALL be treated as external dependencies.

## CTX-SYSTEM-004

The system SHALL treat KA9Q status multicast as the normal source of signal-power, noise-density, gain, channel-status, and overload-related evidence.

## CTX-SYSTEM-005

The system SHALL NOT require KA9Q `DEMOD_SNR` for normal classification.

## CTX-SYSTEM-006

The system SHALL use a derived SNR based on status measurements as the primary status-path classification metric.

## CTX-SYSTEM-007

The system SHALL distinguish signal presence from probable beacon detection and verified beacon identity.

## CTX-SYSTEM-008

The system SHALL continue processing healthy beacons when one beacon, reference channel, verification stream, or downstream consumer fails.

## CTX-SYSTEM-009

The system SHALL create one Observation per configured beacon per fixed ten-second window, including a `NO_DATA` observation when the minimum evidence contract is not satisfied.

## CTX-SYSTEM-010

The system SHALL create one Interval Summary per configured beacon per fixed thirty-minute interval.

# Actors

| Actor | Interaction |
|---|---|
| Operator | Configures beacons, reviews health, investigates alarms, approves baseline changes. |
| Web User | Reads current and historical reception state. |
| External API Client | Reads machine-readable status and history. |
| Maintenance Process | Executes retention, backup, restart, and health checks. |
| AI Reviewer | Reviews AKB and implementation artifacts without inventing requirements. |

# External Systems

| External system | Direction | Contract role |
|---|---|---|
| KA9Q `radiod` | Input and optional control | Status and verification-stream provider. |
| SDR hardware | Indirect input | RF digitization, owned by KA9Q. |
| Time synchronization | Input | UTC timestamps and interval alignment. |
| Reverse proxy | Output boundary | Optional external publication and TLS termination. |
| File or database backup | Output | Operational recovery. |
| Monitoring platform | Output | Health and metrics consumption. |

# Primary Use Cases

## UC-001 Continuous Monitoring

The system receives status samples, groups them into measurement windows, creates observations, stores them, and updates thirty-minute summaries.

## UC-002 Selective Verification

The system requests or consumes PCM/IQ only when a configured trigger requires tone, keyed-CW, frequency, or identity evidence.

## UC-003 Current Status Publication

The system returns the latest completed summary and data freshness for each beacon.

## UC-004 Historical Analysis

The system returns time-series summaries for selected beacons and periods.

## UC-005 Fault Recovery

The system detects stale channels, failed streams, database errors, overload, and queue pressure; it degrades explicitly and recovers without corrupting completed intervals.

# Goals

- Maximize use of KA9Q low-level processing.
- Minimize duplicate continuous DSP in the application.
- Keep detection semantics deterministic and testable.
- Maintain explicit evidence quality and provenance.
- Support unattended operation for at least thirty days.
- Permit later extension to additional beacons and receiver sites.

# Non-Goals

The first baseline SHALL NOT require:

- transmitter control;
- antenna rotator control;
- automatic public beacon-directory synchronization;
- permanent raw IQ storage;
- calibrated absolute dBm reporting;
- autonomous retuning of KA9Q channels;
- multi-site propagation correlation;
- user account management;
- automatic scientific propagation forecasts.

# Interfaces

```yaml
produces:
  - system-purpose
  - system-boundary
  - actor-model
  - external-system-model
consumes:
  - KA9Q-status-multicast
  - KA9Q-verification-streams
  - UTC-time-source
external_outputs:
  - status-and-history-API
  - web-presentation
  - operational-telemetry
  - backup-artifacts
```

The interface list is architectural and SHALL NOT define transport fields, database columns, or implementation signatures.

# Constraints

- All normative timestamps SHALL be UTC.
- Reference channels are the normal architecture; missing references SHALL be explicit degraded operation.
- Continuous Python FFT processing for every beacon SHALL NOT be the normal path.
- Raw status samples SHALL NOT be the primary long-term persistence unit.
- One failing beacon SHALL NOT terminate the complete service.

# High-Level Information Flow

```text
RF -> SDR -> KA9Q radiod
                 |
                 +-> status multicast -> Status Receiver -> Event Bus
                                                -> Measurement Windows
                                                -> Observations
                                                -> Classifier
                                                -> Repository
                                                -> 30-minute Aggregator
                                                -> API / Web
                 |
                 +-> selective PCM or IQ -> Verification Pipeline
                                              -> enriched Observation evidence
```

# Failure Modes

| Failure | Required high-level behavior |
|---|---|
| No KA9Q status | Produce stale/NO_DATA state; preserve other channels. |
| One reference channel stale | Continue with reduced measurement quality and degraded health. |
| Both references stale | Produce NO_DATA unless an approved degraded fallback applies. |
| Verification stream unavailable | Retain status-path result; mark verification unavailable. |
| Database unavailable | Buffer within bounded policy; expose degraded health; never block indefinitely. |
| Clock unsynchronized | Mark interval integrity degraded and prevent silent timestamp acceptance. |

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

- Is the system boundary explicit and complete?
- Are normal and verification paths separated?
- Are all external dependencies identified?
- Are goals and non-goals compatible?
- Is any implementation detail incorrectly normative at context level?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial M2 system-context contract. |
| 1.0.1 | 2026-08-06 | Added mandatory Interfaces section for M2-F-002. |
