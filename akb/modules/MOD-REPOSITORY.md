---
id: MOD-REPOSITORY
title: Repository Module Contract
version: 1.0.1
status: DRAFT_FOR_RE_REVIEW
owner: Architecture
type: contract
normative: true
review:
  required: true
  passes:
    - metadata-and-schema-consistency
    - contract-code-consistency
    - failure-mode-analysis
    - requirements-traceability
    - executable-test-coverage
depends_on: [DM-OBSERVATION, DM-INTERVAL-SUMMARY, DM-DATABASE, ARCH-PRINCIPLES]
verified_by: [TEST-MOD-REPOSITORY]
provides: [observation-persistence, interval-summary-persistence, retention-execution]
consumes: [observation, interval-summary]
---

# Purpose

Define the persistence boundary for observations and 30-minute interval summaries.

# Scope

This contract covers SQLite schema creation, transactional writes, idempotent upserts, queries, retention deletion, and schema-version metadata. It excludes classification, aggregation, DSP, networking, and web presentation.

# Responsibilities

The repository SHALL persist domain records without changing their domain meaning. It SHALL isolate SQL and storage mechanics from processing modules.

# Definitions

| Term | Definition |
|---|---|
| Idempotent upsert | Repeating a write with the same natural key produces one current row. |
| Natural key | Observation: `(beacon_id, window_start_utc)`; summary: `(beacon_id, interval_start_utc)`. |
| Payload JSON | Canonical JSON representation of the supplied dataclass or mapping. |

# Normative Requirements

- **MOD-REPOSITORY-001:** The implementation SHALL create and migrate its schema automatically before normal operations.
- **MOD-REPOSITORY-002:** Every write SHALL execute inside an explicit transaction and SHALL roll back on failure.
- **MOD-REPOSITORY-003:** Observation writes SHALL be idempotent on `(beacon_id, window_start_utc)`.
- **MOD-REPOSITORY-004:** Interval-summary writes SHALL be idempotent on `(beacon_id, interval_start_utc)`.
- **MOD-REPOSITORY-005:** Persisted payloads SHALL preserve enum values and timezone-aware timestamps in deterministic JSON.
- **MOD-REPOSITORY-006:** Naive datetimes and missing natural-key fields SHALL be rejected before persistence.
- **MOD-REPOSITORY-007:** Query results SHALL be ordered deterministically, newest first where a list is returned.
- **MOD-REPOSITORY-008:** Retention deletion SHALL delete only rows whose end timestamp is strictly older than the UTC cutoff.
- **MOD-REPOSITORY-009:** The module SHALL expose the active schema version.
- **MOD-REPOSITORY-010:** The module SHALL contain no classification, aggregation, DSP, multicast, or web logic.

# Interfaces

```yaml
inputs:
  - Observation-compatible dataclass or mapping
  - IntervalSummary-compatible dataclass or mapping
outputs:
  - persisted JSON records
  - deterministic query results
  - purge counts
storage_backend:
  - SQLite
```

# Failure Modes

| Failure | Required behavior |
|---|---|
| Missing natural-key field | Reject without writing. |
| Naive datetime | Reject without writing. |
| SQL error during transaction | Roll back the transaction and propagate. |
| Duplicate natural key | Update the existing row, do not create a duplicate. |
| Invalid query limit | Reject before SQL execution. |
| Missing schema metadata | Raise `RepositoryError`. |

# Traceability

```yaml
verified_by:
  - TEST-MOD-REPOSITORY
implements:
  - DM-DATABASE
consumes:
  - DM-OBSERVATION
  - DM-INTERVAL-SUMMARY
```

# Review Questions

1. Are the natural keys sufficient for reconnect and replay idempotency?
2. Is JSON payload persistence acceptable until a PostgreSQL adapter is introduced?
3. Are retention cutoffs correctly based on end timestamps rather than creation timestamps?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.1 | 2026-08-06 | Fixed-width UTC serialization and completed AKB metadata after M4.5 review. |
| 1.0.0 | 2026-08-06 | Initial M4.5 repository contract. |
