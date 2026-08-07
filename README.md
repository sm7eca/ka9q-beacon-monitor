# KA9Q VHF Beacon Monitor

**Software: APPROVED · 212 tests passing · Phase 0 field validation: UNVERIFIED**

A production-oriented monitoring system for detecting, classifying, verifying, storing and presenting VHF beacon observations using KA9Q-radio / radiod status and verification data.

The project is developed using an Architecture Knowledge Base (AKB), contract-driven implementation and independent AI peer review at each milestone.

## Project Status

**Software status: M5 COMPLETE / APPROVED**

The complete software stack from KA9Q status reception through operations and release management has passed independent AI peer review. The current approved automated baseline is **212 tests passed**.

### Field validation

Real KA9Q/radiod Phase-0 field evidence is still pending. The hardware-dependent assumptions `P0-A-001` through `P0-A-003` therefore remain **UNVERIFIED**.

This is intentional: synthetic tests and software validation are not allowed to mark real hardware assumptions as verified. The system is **software-ready**, while **field-ready status remains blocked until a documented Phase-0 session has been completed**.

## System Pipeline

```text
KA9Q / radiod
      |
      v
Status Receiver
      |
      v
Measurement Builder
      |
      v
Classifier
      |
      v
Verification Analyzer
      |
      v
Repository
      |
      +--------------------+
      |                    |
      v                    v
Interval Aggregator      REST API
                           |
                           v
                         Web UI
```

The Main Application composition root connects the independently reviewed modules and controls startup, shutdown and lifecycle management.

## Approved Software Modules

### M4 — Core Application

| Milestone | Module | Status |
|---|---|---|
| M4.1 | Status Receiver | APPROVED |
| M4.2 | Measurement Builder | APPROVED |
| M4.3 | Classifier | APPROVED |
| M4.4 | Verification Analyzer | APPROVED |
| M4.5 | Repository | APPROVED |
| M4.6 | Interval Aggregator | APPROVED |
| M4.7 | REST API | APPROVED |
| M4.8 | Web UI | APPROVED |
| M4.9 | Main Application / Composition Root | APPROVED |

### M5 — Production Readiness

| Milestone | Module | Status |
|---|---|---|
| M5.1 | Configuration & Secrets | APPROVED |
| M5.2 | Observability & Diagnostics | APPROVED |
| M5.3 | Deployment Packaging | APPROVED |
| M5.4 | KA9Q Production Adapters & Phase 0 Framework | SOFTWARE APPROVED |
| M5.5 | End-to-End & Failure Validation | APPROVED |
| M5.6 | Operations & Release Candidate | APPROVED |

## Major Capabilities

- KA9Q/radiod status ingestion
- deterministic measurement-window construction
- signal and beacon classification with hysteresis
- independent beacon verification
- SQLite persistence
- interval aggregation
- read-only REST API and Web UI
- validated configuration and secret handling
- liveness, readiness, diagnostics and metrics
- deterministic deployment packaging
- installation, upgrade and rollback support
- KA9Q production adapter boundaries
- end-to-end replay and failure validation
- network/radiod interruption recovery validation
- SQLite backup and restore
- operational runbook
- machine-readable release readiness decisions

## Architecture and AKB

Normative architecture and module contracts are stored under `akb/`. Each major module has an associated contract describing scope, responsibilities, interfaces, constraints, normative requirements, failure modes, traceability and review requirements.

Implementation changes are reviewed against these contracts rather than only against unit tests.

## Testing

Run the complete automated test suite:

```bash
python3 -m pytest -q
```

Current approved baseline:

```text
212 passed
```

Focused milestone tests are stored under `tests/` and cover processing, persistence, concurrency, API, Web UI, configuration, observability, deployment, KA9Q adapters, end-to-end validation, and operations/release handling.

## AI Peer Review

Generate a milestone review package with:

```bash
python3 tools/create_review_package.py <milestone>
```

For example:

```bash
python3 tools/create_review_package.py M5.6
```

Review configuration is maintained in `tools/review_milestones.json`. Review requests, finding dispositions and milestone review material are stored under `reviews/`.

A milestone is not treated as complete merely because its automated tests pass. Findings from independent review must also be resolved according to the AKB decision rules.

## Configuration and Secrets

Runtime configuration is validated before external resources are opened. Unknown `KA9Q_*` environment variables are rejected rather than silently ignored. Secrets are injected separately and are not intended to be stored in repository-controlled configuration files.

## Operations

Operational procedures are documented in `operations/RUNBOOK.md`, covering installation, startup, graceful shutdown, restart, health and diagnostics, upgrade, rollback, backup, restore, incident recovery and Phase-0 field validation.

## Deployment

M5.3 provides deterministic deployment packaging with reproducible release archives, manifests and checksums, archive integrity validation, immutable installed versions, controlled upgrade and rollback, and fail-closed rejection of malformed packages.

## Release Readiness

M5.6 deliberately separates two release decisions:

```text
software_release_ready
field_release_ready
```

Software readiness depends on successful software reviews and release checks. Field readiness additionally requires verified Phase-0 hardware evidence. This prevents synthetic or CI-generated evidence from being mistaken for actual KA9Q/radiod field validation.

## Remaining Work

The software implementation through M5 is complete. The principal remaining project activity is **Phase 0 — Real KA9Q/radiod Field Validation**.

A real field session must collect and document provenance including radiod version/revision, hardware identity, network endpoint, capture SHA-256, UTC capture interval, and relevant status and verification evidence.

Only reviewed field evidence may change `P0-A-001` through `P0-A-003` from `UNVERIFIED`.

**Software-ready: YES**  
**Field-ready: NO**

## Repository Structure

```text
akb/                  Architecture and normative contracts
operations/           Operations runbook
phase0/               Phase-0 evidence framework
reviews/              AI peer-review material
src/                  Application source code
tests/                Automated tests
tools/                Review and project tooling
validation_evidence/  End-to-end software validation evidence
```

## Development Principle

> Architecture defines the contract, tests verify the implementation, and independent review verifies that both agree.

No hardware-dependent claim is considered verified solely because a synthetic test passes.
