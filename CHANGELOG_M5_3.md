# M5.3 Change Log

## 1.0.1 — 2026-08-07

- Added dedicated regression tests for archive path traversal rejection.
- Added extraction-failure recovery test proving the active release remains unchanged and staging is cleaned.
- Added rollback-without-previous regression test.
- Closed M5.3-F-001 without production-code changes.

## 1.0.0 — 2026-08-07

- Added deterministic deployment archive builder and verifier.
- Added versioned install, atomic upgrade and rollback mechanics.
- Added hardened systemd service definition and non-secret deployment example.
- Added deployment packaging contract, tests and AI review request.
