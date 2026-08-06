---
id: MOD-MAIN-APPLICATION
version: 1.0.0
status: DRAFT_FOR_REVIEW
title: Main Application Composition Root
owner: Runtime Architecture
normative: true
type: contract
depends_on:
  - MOD-STATUS-RECEIVER
  - MOD-MEASUREMENT-BUILDER
  - MOD-CLASSIFIER
  - MOD-VERIFICATION-ANALYZER
  - MOD-REPOSITORY
  - MOD-INTERVAL-AGGREGATOR
  - MOD-REST-API
  - MOD-WEB-UI
verified_by:
  - TEST-MOD-MAIN-APPLICATION
provides:
  - application-lifecycle
  - pipeline-composition
consumes:
  - approved-runtime-modules
review:
  required: true
  passes:
    - contract-to-code
    - lifecycle-safety
    - pipeline-integration
    - graceful-shutdown
    - dependency-boundary
---

# Purpose

Define the composition root that connects the approved M4 modules without duplicating their domain rules.

# Scope

This contract covers dependency injection, window joining, runtime lifecycle, persistence handoff, API/UI mounting, and graceful shutdown. The concrete KA9Q wire decoder and low-level verification backend remain deployment adapters.

# Responsibilities

- Join configured signal and reference windows by beacon and window start.
- Preserve classifier previous-state feedback per beacon.
- Apply selective verification, persist observations, and forward them to interval aggregation.
- Persist emitted interval summaries.
- Start and stop the receiver exactly once.
- Flush measurement and interval state before closing the repository.
- Expose the REST API under `/api` and the Web UI under `/`.

# Definitions

| Term | Definition |
|---|---|
| Composition root | The only layer that constructs and connects approved modules. |
| Beacon pipeline | One beacon's signal channel, reference channels, and optional expected callsign. |
| Deployment adapter | Environment-specific implementation of a protocol such as the KA9Q decoder or verification backend. |

# Interfaces

Inputs: `StatusSample`, runtime configuration, injected receiver/decoder/backend/repository dependencies.

Outputs: persisted `Observation`, persisted `IntervalSummary`, REST API and Web UI services.

# Constraints

- No signal-classification thresholds, DSP, SQL schema, or presentation rules may be redefined here.
- Beacon IDs and reference-channel IDs must be unique within their configured scopes.
- A classification may run only after the signal window and every configured reference window for the same UTC window are present.
- Runtime mutation is serialized per beacon.

# Normative Requirements

- **MOD-MAIN-APPLICATION-001:** Start SHALL reject a second concurrent or repeated start.
- **MOD-MAIN-APPLICATION-002:** Shutdown SHALL be idempotent.
- **MOD-MAIN-APPLICATION-003:** Shutdown SHALL close the receiver, flush measurement windows, flush interval summaries, then close the repository.
- **MOD-MAIN-APPLICATION-004:** Window joining SHALL use `(beacon_id, window_start_utc)` and require all configured channels.
- **MOD-MAIN-APPLICATION-005:** Each complete joined window set SHALL be classified exactly once.
- **MOD-MAIN-APPLICATION-006:** The resulting observation SHALL pass through verification before persistence.
- **MOD-MAIN-APPLICATION-007:** Every persisted observation SHALL be forwarded to `IntervalAggregator`.
- **MOD-MAIN-APPLICATION-008:** Every emitted interval summary SHALL be persisted.
- **MOD-MAIN-APPLICATION-009:** Previous `DetectionState` SHALL be retained independently per beacon for classifier hysteresis.
- **MOD-MAIN-APPLICATION-010:** Pipeline errors SHALL be counted and isolated from the error handler itself.
- **MOD-MAIN-APPLICATION-011:** The ASGI application SHALL mount the approved REST API at `/api` and Web UI at `/` with one shared lifecycle.
- **MOD-MAIN-APPLICATION-012:** Hardware- and DSP-specific adapters SHALL remain injected and SHALL NOT be silently replaced by production mocks.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Duplicate beacon ID | Reject configuration. |
| Missing reference channel | Reject configuration. |
| Receiver startup failure | Reset runtime state and propagate the error. |
| Error handler failure | Suppress it and continue. |
| Repeated shutdown | Return without additional side effects. |
| Incomplete joined window set | Retain pending state; do not classify. |

# Traceability

`BeaconRuntime` and `create_main_app` implement this contract. `tests/runtime/test_application.py` and `tests/test_main.py` provide executable verification.

# Acceptance Criteria

- The complete repository test suite passes.
- A synchronized signal/reference pair produces one persisted observation.
- The receiver starts and closes exactly once.
- API and UI routes are reachable through the composed ASGI app.
- No deployment-specific decoder or DSP implementation is embedded in the composition root.

# Review Questions

1. Is shutdown ordering sufficient to prevent data loss?
2. Can concurrent windows for one beacon be joined without duplicate classification?
3. Are deployment adapters explicit at every external boundary?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial M4.9 composition-root contract. |
