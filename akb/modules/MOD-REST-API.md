---
id: MOD-REST-API
title: REST API
version: 1.0.1
status: DRAFT_FOR_RE_REVIEW
type: contract
owner: Runtime Team
normative: true
depends_on: [MOD-REPOSITORY, DM-OBSERVATION, DM-INTERVAL-SUMMARY]
verified_by: [TEST-MOD-REST-API]
provides: [rest-api, openapi-contract]
consumes: [observation, interval-summary]
review:
  required: true
  passes: [contract-code, test-coverage, error-handling, security-boundary, openapi]
---

# Purpose

Define the read-only HTTP interface for beacon metadata, observations, interval summaries, and operational health.

# Scope

This contract governs the public HTTP routes, request validation, response status semantics, and the read-only repository boundary. It does not govern persistence implementation, domain classification, DSP, aggregation, or presentation styling.

# Responsibilities

- Expose health and beacon catalog endpoints.
- Expose read-only observation and interval-summary history.
- Validate limits and UTC timestamps before repository access.
- Distinguish unknown beacons from known beacons with no persisted records.
- Translate repository health failures into stable HTTP responses.
- Publish an OpenAPI description of all public routes.

# Definitions

| Term | Definition |
|---|---|
| Known beacon | A beacon identifier present in the immutable catalog supplied when the application is created. |
| Unknown beacon | A beacon identifier absent from that catalog. |
| Missing record | A requested observation or interval summary that does not exist for a known beacon. |
| Read-only API | An API that performs no persistence writes or domain-state mutation. |

# Interfaces

The module consumes a `ReadRepository` protocol and an immutable beacon catalog. Repository payloads are returned without redefining the domain contracts that own them.

Public routes:

- `GET /health`
- `GET /beacons`
- `GET /beacons/{beacon_id}`
- `GET /beacons/{beacon_id}/observations`
- `GET /beacons/{beacon_id}/observations/{window_start_utc}`
- `GET /beacons/{beacon_id}/summaries`
- `GET /beacons/{beacon_id}/summaries/{interval_start_utc}`

# Constraints

- Beacon identifiers SHALL be resolved against the configured catalog before repository history queries.
- Timestamp path parameters SHALL be timezone-aware UTC values.
- List limits SHALL remain within 1 through 1000.
- Repository payloads SHALL be exposed read-only.
- Error responses SHALL not reveal internal exception details.

# Normative Requirements

- **MOD-REST-API-001:** The module SHALL expose `GET /health` with repository schema version and record counts.
- **MOD-REST-API-002:** The module SHALL expose deterministic beacon metadata through `GET /beacons` and `GET /beacons/{beacon_id}`.
- **MOD-REST-API-003:** The module SHALL expose paged observation lists per beacon with a validated limit from 1 through 1000.
- **MOD-REST-API-004:** The module SHALL expose exact observation lookup by beacon ID and UTC window-start timestamp.
- **MOD-REST-API-005:** The module SHALL expose paged interval-summary lists and exact summary lookup using the same validation policy.
- **MOD-REST-API-006:** Timestamp path parameters SHALL be valid ISO-8601, timezone-aware, and expressed in UTC.
- **MOD-REST-API-007:** Unknown beacons and missing persisted records SHALL return HTTP 404 without leaking implementation details. Unknown-beacon validation SHALL occur before repository history access.
- **MOD-REST-API-008:** Repository failure in the health path SHALL return HTTP 503.
- **MOD-REST-API-009:** The module SHALL publish an OpenAPI schema containing all public routes.
- **MOD-REST-API-010:** The API SHALL be read-only and SHALL NOT perform classification, DSP, verification, aggregation, retention, or persistence writes.

# Failure Modes

| Condition | Required behavior |
|---|---|
| Invalid limit | HTTP 422 |
| Invalid or non-UTC timestamp | HTTP 422 |
| Unknown beacon | HTTP 404 before repository history lookup |
| Missing observation or summary for known beacon | HTTP 404 |
| Repository health failure | HTTP 503 |
| Duplicate catalog ID at startup | Fail fast with `ValueError` |

# Traceability

```yaml
verified_by:
  - TEST-MOD-REST-API
related_architecture:
  - ARCH-RUNTIME
  - ARCH-EVENTS
depends_on:
  - MOD-REPOSITORY
  - DM-OBSERVATION
  - DM-INTERVAL-SUMMARY
```

# Acceptance Criteria

- All normative requirements SHALL have executable tests.
- Unknown beacons SHALL return 404 on beacon metadata, list, and exact-record routes.
- Known beacons without data MAY return an empty list page.
- The complete inherited test suite SHALL remain green.
- The generated OpenAPI schema SHALL contain every public route.

# Review Questions

1. Are unknown-beacon and missing-record semantics distinguishable and consistent across all routes?
2. Does every route remain read-only and free from domain-processing logic?
3. Are UTC and limit validations performed before repository access?
4. Does the OpenAPI schema reflect the complete public route set?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial M4.7 REST API contract. |
| 1.0.1 | 2026-08-06 | Added complete AKB section set and required catalog-first 404 behavior for all history routes. |
