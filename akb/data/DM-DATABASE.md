---
id: DM-DATABASE
title: Database Model
version: 1.0.0
status: DRAFT
owner: Data Architecture
type: entity
normative: true
depends_on:
  - DM-OBSERVATION
  - DM-INTERVAL-SUMMARY
provides:
  - database-schema
  - persistence-identity
  - retention-policy
consumes:
  - observation
  - interval-summary
review:
  required: true
  passes:
    - data-model-integrity
    - requirement-traceability
    - testability-and-acceptance
---

# Purpose

Define the normative logical persistence model for beacon metadata, observations, interval summaries, health events, and schema versioning.

# Scope

This contract owns table identity, keys, constraints, schema versioning, and retention semantics. It does not own repository method signatures or database deployment topology.

# Responsibilities

- Preserve exactly one Observation per beacon and MeasurementWindow.
- Preserve exactly one IntervalSummary per beacon and 30-minute interval.
- Enforce beacon referential integrity.
- Support idempotent schema application and summary upsert.
- Define retention ownership without deleting records during model construction.

# Definitions

| Term | Definition |
|---|---|
| Observation identity | The tuple `(beacon_id, window_start_utc)`. |
| Summary identity | The tuple `(beacon_id, interval_start_utc)`. |
| Schema version | A monotonically increasing integer identifying the applied logical schema. |
| Retention policy | Configured maximum age for a record class; `null` means indefinite retention. |

# Normative Requirements

- **DM-DATABASE-001:** The initial implementation SHALL use SQLite with foreign keys enabled.
- **DM-DATABASE-002:** Schema application SHALL be idempotent.
- **DM-DATABASE-003:** `observations` SHALL reject duplicate `(beacon_id, window_start_utc)` rows.
- **DM-DATABASE-004:** `interval_summaries` SHALL use `(beacon_id, interval_start_utc)` as its primary key and SHALL support deterministic upsert.
- **DM-DATABASE-005:** Every persisted observation and summary SHALL reference an existing beacon.
- **DM-DATABASE-006:** Raw `StatusSample` and `MeasurementWindow` objects SHALL NOT be persisted in normal operation.
- **DM-DATABASE-007:** Observation retention SHALL default to 90 days.
- **DM-DATABASE-008:** Interval summaries SHALL be retained indefinitely by default.
- **DM-DATABASE-009:** Health events SHALL default to 30 days retention.
- **DM-DATABASE-010:** Retention execution SHALL be owned by the future `OPS-RETENTION` contract and SHALL not be hidden inside read or write operations.
- **DM-DATABASE-011:** Timestamps SHALL be stored as normalized UTC ISO-8601 text.
- **DM-DATABASE-012:** Schema version 1 SHALL contain `schema_version`, `beacons`, `observations`, `interval_summaries`, and `health_events`.

# Interfaces

```yaml
produces:
  - database-schema
  - schema-version
  - persistence-identity
consumes:
  - observation
  - interval-summary
future_consumers:
  - MOD-REPOSITORY
  - OPS-RETENTION
```

# Constraints

- Database CHECK constraints SHALL reject impossible percentages and negative counts.
- Domain enum values SHALL be persisted as their stable string values.
- Database-generated surrogate keys MAY be used, but SHALL NOT replace normative domain identities.
- Migration logic beyond schema version 1 is outside this contract.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Duplicate observation | Reject or explicitly update through a repository policy; silent duplication is forbidden. |
| Unknown beacon reference | Reject through foreign-key enforcement. |
| Partial schema | Validation SHALL return an error and startup SHALL be blocked. |
| Unsupported schema version | Repository startup SHALL fail safely. |
| Retention job failure | Existing data SHALL remain intact and health SHALL become degraded. |

# Traceability

```yaml
governs:
  - MOD-REPOSITORY
  - OPS-RETENTION
verified_by:
  - TEST-DATABASE-MODEL
  - TEST-DATABASE-SCHEMA
  - TEST-DATABASE-IDEMPOTENCY
```

# Review Questions

- Are domain identities sufficient to prevent duplicate rows after reconnects or replay?
- Can every database constraint be traced to a domain invariant?
- Is any low-level KA9Q sample data persisted contrary to DM-DATABASE-006?
- Are retention defaults explicit and owned by the correct future component?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial database model contract. |
