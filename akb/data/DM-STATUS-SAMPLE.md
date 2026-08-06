---
id: DM-STATUS-SAMPLE
title: Status Sample Data Contract
version: 1.0.1
status: DRAFT_FOR_RE_REVIEW
owner: Data Architecture
type: entity
normative: true
depends_on:
  - AKB-META
  - AKB-SCHEMA
  - CTX-GLOSSARY
  - ARCH-KA9Q
provides:
  - status-sample-contract
consumes:
  - ka9q-channel-status
traceability:
  requirements:
    - DM-STATUS-SAMPLE-001
    - DM-STATUS-SAMPLE-002
    - DM-STATUS-SAMPLE-003
    - DM-STATUS-SAMPLE-004
  modules:
    - MOD-STATUS-RECEIVER
  tests:
    - TEST-DM-STATUS-SAMPLE
review:
  required: true
  passes:
    - data-model-integrity
    - schema-consistency
    - testability-and-acceptance
---

# Purpose

Define the immutable normalized representation of one KA9Q `radiod` channel-status sample.

# Scope

This contract owns receiver-status measurements received for one configured KA9Q channel at one UTC timestamp.

It SHALL NOT contain beacon classification, derived local SNR, verification results, interval aggregation, persistence state, or web presentation fields.

# Responsibilities

- Define the normalized fields emitted by the status receiver.
- Define nullability and validation rules.
- Distinguish valid, partial, and invalid samples.
- Provide the input contract for `DM-MEASUREMENT-WINDOW`.

# Definitions

| Term | Definition |
|---|---|
| StatusSample | One immutable normalized channel-status record derived from a received KA9Q status update. |
| Valid sample | A sample containing the measurements required for normal status-based processing. |
| Partial sample | A structurally valid sample with one or more unavailable optional or measurement fields. |
| Invalid sample | A sample representing rejected or unusable status input and containing no measurement values. |
| UTC timestamp | A timezone-aware timestamp expressed in UTC. |

# Normative Requirements

## DM-STATUS-SAMPLE-001 — Immutability

A `StatusSample` SHALL be immutable after construction.

## DM-STATUS-SAMPLE-002 — UTC time

`timestamp_utc` SHALL be timezone-aware and expressed in UTC.

## DM-STATUS-SAMPLE-003 — Separation of concerns

A `StatusSample` SHALL contain only normalized receiver and channel status. It SHALL NOT contain `derived_snr_db`, `classification_snr_db`, beacon state, confidence, or verification identity.

## DM-STATUS-SAMPLE-004 — Quality consistency

A sample marked `VALID` SHALL contain both `baseband_power_db` and `noise_density_db_hz`. A sample marked `INVALID` SHALL contain no measurement values.

# Interfaces

```yaml
entity: StatusSample
producer: MOD-STATUS-RECEIVER
consumer: MOD-MEASUREMENT-WINDOW
python_contract: src/ka9q_beacon_monitor/model/status_sample.py
verification_contract: tests/model/test_status_sample.py
```

# Field Definitions

| Field | Type | Required | Constraint | Meaning |
|---|---|---:|---|---|
| `timestamp_utc` | datetime | yes | timezone-aware UTC | Time assigned to the normalized sample. |
| `channel_id` | string | yes | non-empty stable channel identifier | Identifies the KA9Q signal or reference channel. |
| `frequency_hz` | float | yes | finite and greater than zero | Nominal or reported channel frequency. |
| `baseband_power_db` | float/null | conditional | finite when present | KA9Q baseband power measurement. |
| `noise_density_db_hz` | float/null | conditional | finite when present | KA9Q noise-density measurement normalized per hertz. |
| `gain_db` | float/null | no | finite when present | Reported channel gain. |
| `output_level_db` | float/null | no | finite when present | Reported demodulator output level. |
| `headroom_db` | float/null | no | finite when present | Reported available headroom. |
| `demod_mode` | enum | yes | `linear`, `fm`, `am`, `iq`, `unknown` | Normalized channel demodulator mode. |
| `pll_locked` | bool/null | no | null when not applicable or unavailable | Optional PLL lock status. |
| `sequence_number` | integer/null | no | non-negative when present | Source or receiver sequence number when exposed. |
| `sample_quality` | enum | yes | `valid`, `partial`, `invalid` | Normalization result quality. |

# Constraints

- Numeric values SHALL reject NaN and infinity.
- `channel_id` SHALL be stable across process restarts for the same configured channel.
- `DEMOD_SNR` is not a required field of this contract.
- Missing optional KA9Q fields SHALL be represented as null, not invented values.
- `StatusSample` SHALL not be persisted as an authoritative observation record.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Timestamp is naive | Construction SHALL fail. |
| Timestamp is not UTC | Construction SHALL fail. |
| Channel identifier is empty | Construction SHALL fail. |
| Frequency is zero, negative, NaN, or infinite | Construction SHALL fail. |
| Required valid-sample measurement is missing | Construction SHALL fail. |
| Invalid sample contains measurements | Construction SHALL fail. |
| Optional source field is absent | Field SHALL be null and sample MAY be `PARTIAL`. |

# Traceability

```yaml
governed_by:
  - ARCH-KA9Q
  - AKB-SCHEMA
implemented_by:
  - MOD-STATUS-RECEIVER
consumed_by:
  - DM-MEASUREMENT-WINDOW
verified_by:
  - TEST-DM-STATUS-SAMPLE
```

# Acceptance Criteria

- All model tests pass.
- The Python model is immutable.
- Every required field and enum value matches this contract.
- Invalid numeric values are rejected.
- No beacon-classification or derived-SNR field exists in the model.

# Review Questions

- Are all fields direct normalized receiver-status values rather than derived beacon-domain values?
- Are nullability rules deterministic?
- Can a consumer distinguish missing optional data from invalid source data?
- Is the UTC requirement unambiguous?
- Does the Python contract match this document exactly?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial M3 `StatusSample` contract. |

| 1.0.1 | 2026-08-06 | M3.1 consistency and executable-test patch. |
