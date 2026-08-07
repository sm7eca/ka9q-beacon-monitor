---
id: MOD-OBSERVABILITY-DIAGNOSTICS
version: 1.0.0
status: DRAFT_FOR_REVIEW
title: Observability and Diagnostics
owner: Runtime Operations
normative: true
type: contract
depends_on:
  - MILESTONE-M5-PRODUCTION-READINESS
  - MOD-MAIN-APPLICATION
  - MOD-CONFIGURATION-SECRETS
verified_by:
  - TEST-M5-OBSERVABILITY-DIAGNOSTICS
provides:
  - structured-operational-logs
  - runtime-metrics
  - liveness-readiness
  - build-identity
  - runtime-diagnostics
consumes:
  - runtime-state
  - runtime-counters
review:
  required: true
  passes:
    - contract-code-consistency
    - diagnostics-completeness
    - secret-boundary
    - failure-mode-coverage
    - m4-regression
---

# Purpose

Define M5.2 observability surfaces that make the approved application operationally inspectable without moving domain logic into diagnostics.

# Scope

This module covers structured JSON logging, process liveness, service readiness, Prometheus-text metrics, build identity, and read-only runtime diagnostics. It does not change classifier, verification, persistence, aggregation, REST resource, or Web UI semantics.

# Responsibilities

- Emit deterministic structured operational log records.
- Expose distinct liveness and readiness semantics.
- Export existing runtime counters without taking ownership of them.
- Expose version and build revision identity.
- Provide read-only diagnostics suitable for operational fault isolation.
- Avoid accidental serialization of arbitrary secret-bearing log extras.

# Definitions

| Term | Definition |
|---|---|
| Liveness | Evidence that the process and HTTP application can answer an operations request. |
| Readiness | Evidence that the composed runtime is started and optional deployment readiness checks pass. |
| Metric | Numeric operational state exported in Prometheus text exposition format. |
| Build identity | Version, revision, and optional build timestamp identifying the running artifact. |
| Diagnostic status | Read-only snapshot of runtime state and counters. |

# Interfaces

Inputs: `BeaconRuntime.is_started`, existing `RuntimeCounters`, optional readiness callback, and named `KA9Q_BUILD_*` environment metadata.

Outputs: `/ops/live`, `/ops/ready`, `/ops/build`, `/ops/diagnostics`, `/ops/metrics`, plus the structured logging formatter/configurator.

# Constraints

- Observability SHALL remain read-only with respect to domain and repository state.
- Liveness SHALL NOT depend on repository, radio, or verification-backend availability.
- Readiness SHALL fail closed when the runtime is not started or an explicit readiness check fails.
- Metrics SHALL be derived from existing runtime state rather than duplicate business counters.
- Secret values SHALL NOT be intentionally exported through metrics, build identity, diagnostics, or arbitrary logging extras.
- M4 domain behavior remains governed by MILESTONE-M5-001.

# Normative Requirements

- **MOD-OBSERVABILITY-DIAGNOSTICS-001:** The composed application SHALL expose a process-level liveness endpoint.
- **MOD-OBSERVABILITY-DIAGNOSTICS-002:** The composed application SHALL expose a readiness endpoint distinct from liveness.
- **MOD-OBSERVABILITY-DIAGNOSTICS-003:** Readiness SHALL return unavailable while the runtime is stopped and when an injected readiness check fails.
- **MOD-OBSERVABILITY-DIAGNOSTICS-004:** Runtime counters SHALL be exposed as machine-readable operational metrics without modifying their ownership or increment semantics.
- **MOD-OBSERVABILITY-DIAGNOSTICS-005:** Metrics SHALL include runtime-started state and build identity.
- **MOD-OBSERVABILITY-DIAGNOSTICS-006:** Build identity SHALL expose version and revision, with optional build timestamp, from explicit build metadata or package metadata.
- **MOD-OBSERVABILITY-DIAGNOSTICS-007:** Diagnostic status SHALL expose runtime-started state, runtime counters, and build identity without mutating the runtime.
- **MOD-OBSERVABILITY-DIAGNOSTICS-008:** Operational logs SHALL be emitted as one parseable JSON object per record with UTC timestamp, severity, logger, and rendered message.
- **MOD-OBSERVABILITY-DIAGNOSTICS-009:** Arbitrary `LogRecord` extras SHALL NOT be serialized automatically, limiting accidental secret disclosure.
- **MOD-OBSERVABILITY-DIAGNOSTICS-010:** Observability endpoints SHALL be mounted in the M4.9 composition root without changing the approved `/api` or Web UI behavior.
- **MOD-OBSERVABILITY-DIAGNOSTICS-011:** The module SHALL introduce no new network, storage, or hardware dependency during construction.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Runtime not started | Liveness remains available; readiness returns HTTP 503. |
| Deployment readiness dependency unavailable | Readiness returns HTTP 503 without changing runtime state. |
| Missing build metadata | Use safe `unknown`/package fallback values rather than fail startup. |
| Runtime counter absent in a test/deployment double | Export zero for the known counter name. |
| Arbitrary logging extra contains sensitive material | Do not serialize arbitrary extras. |

# Traceability

This contract implements `MILESTONE-M5-004` and preserves `MILESTONE-M5-001`. Executable evidence is in `tests/observability/`, including composition-root integration coverage.

# Acceptance Criteria

- All M5.2 focused tests pass.
- The full repository test suite passes without M4 regression.
- Liveness and readiness are behaviorally distinct.
- Metrics and diagnostics reflect existing runtime counters.
- Build identity is explicit and deterministic when deployment metadata is supplied.
- Structured log output is parseable and does not serialize arbitrary extras.

# Review Questions

1. Are liveness and readiness semantics operationally correct and distinct?
2. Do metrics reuse rather than redefine runtime counters?
3. Can any secret-bearing arbitrary log extra leak through the formatter?
4. Does composition-root integration preserve all approved M4 routes and lifecycle behavior?
5. Is build identity sufficient to identify a deployed artifact?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-07 | Initial M5.2 observability and diagnostics contract. |
