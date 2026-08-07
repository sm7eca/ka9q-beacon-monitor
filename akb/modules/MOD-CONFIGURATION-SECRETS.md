---
id: MOD-CONFIGURATION-SECRETS
version: 1.0.0
status: DRAFT_FOR_REVIEW
title: Runtime Configuration and Secrets
owner: Runtime Operations
normative: true
type: contract
depends_on:
  - MILESTONE-M5-PRODUCTION-READINESS
  - MOD-MAIN-APPLICATION
verified_by:
  - TEST-M5-CONFIGURATION-SECRETS
provides:
  - validated-runtime-configuration
  - secret-boundary
consumes:
  - deployment-configuration
  - deployment-secrets
review:
  required: true
  passes:
    - contract-code-consistency
    - validation-completeness
    - secret-boundary
    - failure-mode-coverage
    - dependency-boundary
---

# Purpose

Define the M5.1 boundary for loading and validating runtime configuration and deployment secrets before any external service is started.

# Scope

This module covers repository-controlled JSON configuration, environment overrides, validation, secret injection, redaction, and startup-failure behavior. It does not open sockets, databases, HTTP clients, KA9Q services, or verification backends.

# Responsibilities

- Load non-secret runtime configuration from an optional JSON file and explicit environment overrides.
- Validate every production-impacting value before returning a runtime configuration object.
- Keep secret material outside repository-controlled configuration files.
- Require configured secrets before external services can start.
- Prevent accidental secret disclosure through string and representation methods.

# Definitions

| Term | Definition |
|---|---|
| Non-secret configuration | Runtime values safe to store in repository-controlled deployment configuration. |
| Secret | Credential or token that must be injected by an explicit deployment mechanism and never committed to source control. |
| Fail closed | Reject startup configuration before external resources are opened. |
| Environment override | Explicit `KA9Q_*` environment value that takes precedence over the same non-secret JSON field. |

# Interfaces

Inputs: optional JSON configuration path and environment mapping.

Outputs: immutable `RuntimeConfiguration` containing validated `AppConfig` plus redacted `RuntimeSecrets`.

# Constraints

- Secret values SHALL NOT be accepted from JSON configuration files.
- Configuration loading SHALL perform no network, database, filesystem-write, or external-service startup actions.
- Unknown configuration keys SHALL be rejected rather than silently ignored.
- Environment variable names are part of the deployment interface and SHALL remain explicit.
- Namespace validation SHALL recognize explicitly registered cross-module `KA9Q_*` metadata keys without treating them as runtime-configuration overrides.

# Normative Requirements

- **MOD-CONFIGURATION-SECRETS-001:** `load_runtime_configuration` SHALL fully validate configuration before returning.
- **MOD-CONFIGURATION-SECRETS-002:** Missing required configuration SHALL raise `ConfigError` before external services are started.
- **MOD-CONFIGURATION-SECRETS-003:** Environment values SHALL override matching non-secret JSON values deterministically.
- **MOD-CONFIGURATION-SECRETS-004:** JSON configuration SHALL reject unknown keys and secret-like keys.
- **MOD-CONFIGURATION-SECRETS-005:** Secret material SHALL be accepted only through explicitly named secret environment variables.
- **MOD-CONFIGURATION-SECRETS-006:** Verification enabled without `KA9Q_VERIFICATION_TOKEN` SHALL fail closed.
- **MOD-CONFIGURATION-SECRETS-007:** Secret string/repr rendering SHALL redact the underlying value.
- **MOD-CONFIGURATION-SECRETS-008:** Status multicast configuration SHALL require a valid IPv4 multicast address.
- **MOD-CONFIGURATION-SECRETS-009:** Network ports SHALL be integers in the inclusive range 1..65535 and Web refresh SHALL remain in 5..3600 seconds.
- **MOD-CONFIGURATION-SECRETS-010:** Configuration loading SHALL not open or mutate external runtime resources.
- **MOD-CONFIGURATION-SECRETS-011:** The configuration model SHALL preserve approved M4 behavior and SHALL not redefine M4 domain policies.
- **MOD-CONFIGURATION-SECRETS-012:** Unknown `KA9Q_*` environment names SHALL fail closed, except explicitly registered cross-module environment names owned by approved modules; recognized cross-module names SHALL not be consumed as M5.1 runtime overrides.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Missing configuration file | Raise `ConfigError`; do not start external resources. |
| Malformed JSON | Raise `ConfigError`; do not start external resources. |
| Unknown configuration key | Raise `ConfigError`; do not ignore silently. |
| Secret-like key in JSON | Raise `ConfigError`; do not retain or log the secret value. |
| Invalid multicast/port/range | Raise `ConfigError`. |
| Verification enabled without token | Raise `ConfigError` naming only the required environment variable, not a secret value. |

# Traceability

`MOD-CONFIGURATION-SECRETS-001` through `-012` implement `MILESTONE-M5-002` and `MILESTONE-M5-003`. Executable evidence is provided by `tests/config/test_settings.py` (`TEST-M5-CONFIGURATION-SECRETS`).

# Acceptance Criteria

- All M5.1 configuration tests pass with no external resources required.
- Invalid startup configuration is rejected deterministically.
- Secret-like JSON content is rejected.
- Injected secret values do not appear in `repr()` or `str()`.
- M4 production modules remain unmodified by this sub-milestone.

# Review Questions

1. Are all production-impacting values validated before service startup?
2. Can any secret enter repository-controlled configuration or rendered diagnostics?
3. Are precedence rules deterministic and explicit?
4. Does the module remain free of external-resource startup side effects?
5. Does M5.1 preserve M4 contracts without redefining them?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-07 | Initial M5.1 configuration and secrets contract. |
| 1.0.1 | 2026-08-07 | Register approved cross-module KA9Q environment metadata while preserving fail-closed unknown-key handling. |
