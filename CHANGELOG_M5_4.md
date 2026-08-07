# M5.4 Change Log

## 1.0.1 — 2026-08-07

- Replaced caller-supplied `real_capture` boolean with structured `CaptureProvenance`.
- Bound `VERIFIED_CAPTURE` to complete provenance, matching capture SHA-256, non-empty samples and the recorded UTC interval.
- Added regression coverage for fabricated samples, checksum mismatch, interval mismatch and empty captures.
- Clarified fail-closed handling for present-but-invalid bridge timestamps; absent timestamps still use receiver arrival UTC.
- Closed M5.4-F-001 and M5.4-F-002 without changing the already reviewed bridge implementation.

## 1.0.0 — 2026-08-07

- Added selected-release status bridge adapter behind `StatusDatagramDecoder`.
- Added selected-release verification bridge behind `VerificationBackend`.
- Added fail-closed normalization and bridge error handling.
- Added Phase 0 evidence analyzer and deliberately unverified real-capture template.
- Added M5.4 AKB contract, tests and review request.
