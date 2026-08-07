---
id: MOD-DEPLOYMENT-PACKAGING
version: 1.0.0
status: DRAFT_FOR_REVIEW
title: Deployment Packaging
owner: Runtime Operations
normative: true
type: contract
depends_on:
  - MILESTONE-M5-PRODUCTION-READINESS
  - MOD-CONFIGURATION-SECRETS
  - MOD-OBSERVABILITY-DIAGNOSTICS
verified_by:
  - TEST-M5-DEPLOYMENT-PACKAGING
provides:
  - deterministic-deployment-package
  - atomic-release-switching
  - rollback-mechanism
  - service-definition
consumes:
  - repository-controlled-build-inputs
review:
  required: true
  passes:
    - reproducibility
    - package-integrity
    - install-upgrade-rollback
    - secret-boundary
    - m4-m5-regression
---

# Purpose

Define M5.3 deployment packaging so approved application code can be built, verified, installed, upgraded, and rolled back by repeatable automation.

# Scope

This module covers deterministic deployment archives, release manifests, checksum verification, versioned installation directories, atomic current/previous release pointers, rollback mechanics, and a hardened Linux service definition. It does not implement KA9Q production adapters, Phase 0 hardware behavior, or deployment-specific secrets.

# Responsibilities

- Build a deterministic deployment archive from repository-controlled inputs.
- Record every packaged file with size and SHA-256 checksum.
- Reject malformed, tampered, or path-unsafe deployment archives.
- Install releases into immutable version directories.
- Switch active versions atomically while retaining the previous version.
- Provide a deterministic rollback operation.
- Supply a service definition and non-secret environment example.

# Definitions

| Term | Definition |
|---|---|
| Deployment archive | Deterministic ZIP containing application/build inputs, deployment templates, and release manifest. |
| Release manifest | Machine-readable list of packaged file paths, sizes, hashes, package identity, and version. |
| Current release | Version selected by the atomic `current` symbolic link. |
| Previous release | Prior active version retained as rollback target. |

# Interfaces

Inputs: repository root, explicit release version, deployment archive, install root.

Outputs: deterministic deployment ZIP, verified version directory, `current` and `previous` release pointers, systemd service template.

# Constraints

- Package construction SHALL NOT include secrets or runtime-generated state.
- Package verification SHALL occur before an active release pointer is changed.
- Paths originating in archives SHALL be validated against traversal/absolute-path injection.
- Installation SHALL preserve an already active release if verification or extraction fails.
- M5.4 production adapter implementation SHALL NOT be invented by M5.3.
- M4 semantics remain governed by `MILESTONE-M5-001`.

# Normative Requirements

- **MOD-DEPLOYMENT-PACKAGING-001:** Identical repository-controlled inputs and release version SHALL produce byte-for-byte identical deployment archives.
- **MOD-DEPLOYMENT-PACKAGING-002:** Every packaged repository file SHALL be represented in `RELEASE_MANIFEST.json` with SHA-256 and byte size.
- **MOD-DEPLOYMENT-PACKAGING-003:** Archive verification SHALL reject missing, extra, checksum-mismatched, size-mismatched, or path-unsafe members.
- **MOD-DEPLOYMENT-PACKAGING-004:** A release SHALL be fully verified before installation changes the active release pointer.
- **MOD-DEPLOYMENT-PACKAGING-005:** Installed releases SHALL use immutable version-specific directories under a release root.
- **MOD-DEPLOYMENT-PACKAGING-006:** Upgrade SHALL atomically activate the new release and retain the formerly active release as `previous`.
- **MOD-DEPLOYMENT-PACKAGING-007:** Rollback SHALL atomically reactivate `previous` and retain the displaced version for subsequent recovery.
- **MOD-DEPLOYMENT-PACKAGING-008:** Reinstalling an already installed version SHALL fail closed rather than overwrite it in place.
- **MOD-DEPLOYMENT-PACKAGING-009:** Deployment templates SHALL contain no credential or secret value and SHALL rely on external secret injection.
- **MOD-DEPLOYMENT-PACKAGING-010:** The Linux service definition SHALL use a non-root service identity and explicit writable data path.
- **MOD-DEPLOYMENT-PACKAGING-011:** M5.3 SHALL preserve the approved M4/M5.1/M5.2 code semantics and SHALL NOT implement M5.4 hardware adapters.
- **MOD-DEPLOYMENT-PACKAGING-012:** The package/install design SHALL require no manual post-install file mutation to switch, upgrade, or roll back releases.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Archive checksum mismatch | Reject package before release activation. |
| Archive contains extra/missing file relative to manifest | Reject package. |
| Archive path attempts traversal | Reject package. |
| Target version already exists | Reject in-place overwrite. |
| Extraction fails | Keep existing active release unchanged. |
| No previous release exists | Reject rollback without changing current. |

# Traceability

This contract implements `MILESTONE-M5-005` and `MILESTONE-M5-013`, preserves `MILESTONE-M5-001`, and is verified by `tests/deployment/test_packaging.py` plus full-suite regression.

# Acceptance Criteria

- Repeated builds of identical inputs have identical SHA-256 archive digests.
- Manifest and archive contents agree exactly.
- Tampering and unsafe paths fail closed.
- Install, upgrade, rollback, and duplicate-version behavior are executable tests.
- Deployment templates contain no secrets.
- Full repository test suite remains green.

# Review Questions

1. Is archive reproducibility byte-for-byte rather than only logically equivalent?
2. Can a tampered archive become active before verification?
3. Can archive path traversal escape the release directory?
4. Does upgrade preserve a known rollback target atomically?
5. Has M5.3 avoided implementing or assuming M5.4 production adapters?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-07 | Initial M5.3 deployment packaging contract. |
