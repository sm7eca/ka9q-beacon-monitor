---
id: ARCH-KA9Q
title: KA9Q Integration Architecture
version: 1.0.2
status: DRAFT_FOR_RE_REVIEW
owner: Radio Architecture
type: architecture
normative: true
depends_on:
  - CTX-SYSTEM
  - CTX-GLOSSARY
  - ARCH-PRINCIPLES
provides:
  - ka9q-responsibility-model
  - channel-set-model
  - status-path-contract
  - verification-path-contract
consumes:
  - architecture-principles
review:
  required: true
  passes:
    - architecture-consistency
    - failure-and-recovery
    - capacity-and-performance
---

# Purpose

Define how the Beacon Monitor uses KA9Q `radiod`, which responsibilities remain inside KA9Q, which status values are consumed, how Beacon Channel Sets are constructed, and how selective verification streams are used.

# Scope

This contract defines architecture-level behavior. Exact TLV numbers, parser field layouts, radio configuration syntax, and DSP algorithms belong to later interface and module contracts.

# Responsibilities

KA9Q SHALL perform:

- SDR ownership and sample acquisition;
- frequency translation;
- channel filtering;
- decimation and output-rate selection;
- demodulation where configured;
- channel-level baseband-power measurement;
- noise-density measurement where available;
- gain, output, headroom, overload, and channel-status reporting;
- production of optional PCM or IQ verification streams.

The Beacon Monitor SHALL perform:

- channel-to-beacon mapping;
- Status Sample normalization;
- ten-second Measurement Window construction;
- Derived SNR calculation;
- evidence quality evaluation;
- classification, selective verification, aggregation, storage, and publication.

# Definitions

Terms are governed by `CTX-GLOSSARY`.

# Normative Requirements

## ARCH-KA9Q-001 — Beacon Channel Set

The normal architecture SHALL configure one Signal Channel and two Reference Channels per beacon.

## ARCH-KA9Q-002 — Reference Placement

Reference channels SHALL be sufficiently offset from the expected beacon signal to avoid intended signal energy while remaining close enough to represent local noise and interference conditions.

## ARCH-KA9Q-003 — Equivalent Measurement Configuration

Signal and Reference Channels within one Beacon Channel Set SHALL use compatible bandwidth, sampling, gain, and measurement configuration unless a documented correction exists.

## ARCH-KA9Q-004 — Fixed Gain for Measurement

Per-channel AGC SHOULD be disabled for quantitative comparison. Any active gain control SHALL be reported and incorporated into measurement quality.

## ARCH-KA9Q-005 — Primary Status Values

The normal path SHALL consume `BASEBAND_POWER`, `NOISE_DENSITY`, gain-related values, output/headroom values, channel identity, source timestamp, and overload-related status when available.

## ARCH-KA9Q-006 — Optional DEMOD_SNR

`DEMOD_SNR` MAY be consumed as optional diagnostic evidence. It SHALL NOT be required for normal classification and SHALL NOT replace the primary Derived SNR contract unless an approved degraded-mode rule explicitly permits it.

## ARCH-KA9Q-007 — Derived SNR

Derived SNR SHALL be calculated from the Signal Channel and valid Reference Channel evidence according to a later single-owner data or processing contract.

## ARCH-KA9Q-008 — Partial Reference Loss

When exactly one reference channel is stale or unavailable, processing MAY continue using the remaining reference with degraded Measurement Quality and degraded health.

## ARCH-KA9Q-009 — Complete Reference Loss

When both reference channels are stale or unavailable, the system SHALL produce `NO_DATA` unless an explicitly configured degraded fallback is active.

## ARCH-KA9Q-010 — Verification Streams

PCM or IQ streams SHALL be used selectively for tone, frequency, keyed-CW, interference, or Morse identity verification.

## ARCH-KA9Q-011 — Verification Independence

Failure of a verification stream SHALL NOT invalidate an otherwise valid status-path Observation; it SHALL reduce verification or identification evidence and SHALL be visible operationally.

## ARCH-KA9Q-012 — Status Freshness

Status evidence older than its configured freshness limit SHALL be treated as stale and SHALL NOT be silently reused as fresh evidence.

## ARCH-KA9Q-013 — Status Rate Independence

Correctness SHALL NOT depend on receiving status at exactly the nominal rate. Measurement windows SHALL evaluate actual coverage and freshness.

## ARCH-KA9Q-014 — Phase 0 Verification

Phase 0 SHALL determine:

- actual status multicast cadence;
- status fields emitted in the selected demodulation modes;
- `BASEBAND_POWER` smoothing behavior under keyed CW;
- gain and overload behavior on target hardware;
- practical PCM and IQ stream acquisition behavior.

## ARCH-KA9Q-015 — No Implicit KA9Q Control

The first baseline SHALL NOT require autonomous retuning or creation of KA9Q channels during normal monitoring. Static or externally managed channel configuration is the default.

# Channel Architecture

```text
For each beacon:

Lower Reference Channel ----+
                            |
Signal Channel --------------+--> Beacon Channel Set --> Measurement Window
                            |
Upper Reference Channel ----+
```

Design target for ten beacons:

```text
10 Signal Channels
20 Reference Channels
---------------------
30 KA9Q status-producing channels
```

# Interfaces

## Status Path

```yaml
producer: KA9Q-radiod
transport: UDP-multicast
consumer: MOD-STATUS-RECEIVER
output_concept: Status-Sample
normal_path: true
```

## Verification Path

```yaml
producer: KA9Q-radiod
transport:
  - RTP-PCM
  - RTP-IQ
consumer:
  - MOD-TONE-VERIFIER
  - MOD-CW-VERIFIER
  - MOD-MORSE-VERIFIER
normal_path: false
```

# Constraints

- KA9Q version-specific details SHALL be isolated in interface adapters.
- Status parser failure for one datagram SHALL NOT terminate the receiver.
- Channel identity mapping SHALL be explicit and testable.
- The design SHALL support multicast restart and rejoin.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Unknown TLV | Ignore or retain diagnostically; do not crash. |
| Malformed datagram | Reject datagram; count error; continue. |
| Signal channel stale | Observation becomes NO_DATA; channel health degraded. |
| One reference stale | Continue with degraded Measurement Quality. |
| Both references stale | NO_DATA unless explicit fallback applies. |
| Gain mismatch | Reduce Measurement Quality or reject comparison per later contract. |
| Overload/headroom alarm | Mark measurements unreliable and trigger health degradation. |
| Verification RTP unavailable | Preserve status-path state and report unavailable verification. |

# Traceability

```yaml
governed_by:
  - ARCH-PRINCIPLES
supports:
  - CTX-SYSTEM-004
  - CTX-SYSTEM-005
  - CTX-SYSTEM-006
verified_by:
  - TEST-M2-KA9Q-ASSUMPTIONS
```

# Review Questions

- Does the design maximize KA9Q processing without hiding application semantics?
- Are status and verification paths clearly separated?
- Is DEMOD_SNR correctly optional?
- Are reference-loss behaviors explicit?
- Are Phase 0 assumptions complete and non-normative?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial KA9Q integration architecture. |
| 1.0.2 | 2026-08-06 | Package release: synchronized metadata and documented unchanged KA9Q architecture content. |
