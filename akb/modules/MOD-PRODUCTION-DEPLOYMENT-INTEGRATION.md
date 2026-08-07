---
id: MOD-PRODUCTION-DEPLOYMENT-INTEGRATION
version: 1.0.1
status: DRAFT_FOR_REVIEW
type: contract
title: Production Deployment Integration
owner: Runtime / Operations
normative: true
provides: [production-factory, no-sdr-smoke-mode, pi-systemd-entrypoint]
consumes: [approved-m4-composition-root, m5-configuration, m5-ka9q-adapters, m5-operations]
depends_on: [MOD-MAIN-APPLICATION, MOD-CONFIGURATION-SECRETS, MOD-KA9Q-PRODUCTION-ADAPTERS, MOD-OPERATIONS-RELEASE-CANDIDATE]
review:
  required: true
  passes: [contract, code, tests, deployment]
---

# Purpose

Provide the concrete, repository-controlled deployment integration required to start the approved application composition on a production host, including an explicit no-SDR smoke mode that cannot create radio or Phase-0 field evidence.

# Scope

Define the concrete deployment composition required to start the approved application on a production host. This contract was created after the first Raspberry Pi deployment exposed that the generic M4.9 CLI and M5.3 service template referenced a deployment factory that did not yet exist.

# Responsibilities

The module owns the concrete factory, deployment-only configuration, no-SDR smoke mode, and the executable systemd entrypoint. It does not redefine signal processing, verification policy, persistence semantics, API resources, Web UI behavior, or Phase-0 evidence rules.

# Definitions

**no_sdr mode** means the full application, repository, API, UI and operations endpoints are started without opening the KA9Q multicast receiver. It is software deployment evidence only and SHALL NOT be treated as Phase-0 field evidence.

**ka9q mode** means the approved production status adapter and multicast receiver are connected using repository-controlled deployment configuration.

# Interfaces

- `ka9q_beacon_monitor.deployment_factory:create_app(config_path=...)`
- sibling `deployment.json` beside the validated M5.1 `runtime.json`
- `ka9q-beacon-monitor --config ... --factory ...`
- `/ops/*`, `/api/*`, and `/`

# Constraints

Deployment wiring SHALL remain outside reviewed domain modules. Secrets SHALL continue to enter only through the M5.1 secret environment boundary. No-SDR operation SHALL not fabricate KA9Q samples or hardware evidence.

# Normative Requirements

- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-001:** The shipped systemd factory path SHALL resolve to a concrete repository implementation.
- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-002:** The CLI SHALL pass the selected runtime configuration path to the deployment factory before Uvicorn starts.
- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-003:** The factory SHALL use `load_runtime_configuration` for M5.1 runtime configuration and SHALL fail before service startup on invalid configuration.
- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-004:** Deployment-specific keys SHALL be loaded from a strict sibling `deployment.json`; unknown keys SHALL be rejected.
- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-005:** `no_sdr` mode SHALL construct the repository, classifier, verifier orchestration, composition root, API, Web UI and operations endpoints without opening a multicast receiver or requiring bridge executables.
- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-006:** `no_sdr` mode SHALL NOT mark or create Phase-0 field evidence.
- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-007:** `ka9q` mode SHALL require an explicit status bridge command and SHALL connect `Ka9qStatusReceiver` to `BeaconRuntime.ingest_sample`.
- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-008:** When verification is enabled, a verification bridge SHALL be explicitly configured; otherwise startup SHALL fail closed.
- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-009:** Beacon pipeline definitions used by the runtime and beacon definitions exposed by the API SHALL originate from the same deployment configuration records.
- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-010:** The shipped Raspberry Pi systemd unit SHALL invoke the concrete deployment factory and use repository-defined runtime locations.
- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-011:** A no-SDR smoke test SHALL verify liveness, readiness, diagnostics, metrics, repository health, API and Web UI without requiring radiod or an SDR.
- **MOD-PRODUCTION-DEPLOYMENT-INTEGRATION-012:** This module SHALL preserve all approved M4 and M5.1-M5.6 domain and field-evidence semantics.

# Failure Modes

| Failure | Required behavior |
|---|---|
| `deployment.json` missing/malformed | Fail before runtime start |
| unknown deployment key | Reject fail-closed |
| `ka9q` mode without status bridge | Reject fail-closed |
| verification enabled without verification bridge | Reject fail-closed |
| no SDR/radiod in `no_sdr` mode | Application remains startable for software smoke validation |

# Traceability

This contract closes the production-deployment gap discovered during the first Raspberry Pi 5 / Debian 13 Trixie installation after M5.6 software approval. It consumes the existing M4.9 composition root rather than replacing it.

# Review Questions

1. Does the concrete factory compose only already-approved modules?
2. Can no-SDR mode start without opening the multicast receiver?
3. Is `ka9q` mode fail-closed when its bridge is absent?
4. Does any no-SDR path fabricate Phase-0 evidence?
5. Does the systemd unit reference an importable factory?

# Change History

| Version | Change |
|---|---|
| 1.0.1 | Closed M5.7 review findings: deployment-template cleanup, complete AKB metadata/Purpose, and top-level M5 traceability registration. |
| 1.0.0 | Initial M5.7 deployment-integration contract after Raspberry Pi deployment discovery. |
