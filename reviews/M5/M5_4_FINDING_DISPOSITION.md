# M5.4 Finding Disposition

## M5.4-F-001 — CLOSED

`real_capture: bool` has been removed from the Phase 0 analyzer. `VERIFIED_CAPTURE` now requires a structured `CaptureProvenance`, non-empty samples, supplied capture bytes, a computed SHA-256 matching the provenance, and sample timestamps inside the recorded UTC interval. Synthetic data without provenance therefore remains `UNVERIFIED` structurally rather than by caller discipline.

Permanent regression tests cover missing provenance, checksum mismatch, out-of-interval samples, empty captures, and the original fabricated-data scenario.

The remaining boundary is explicit: software can verify provenance completeness and artifact integrity, but cannot prove that an operator actually captured the bytes from physical hardware. That field-session custody assumption remains subject to evidence review.

## M5.4-F-002 — CLOSED

`MOD-KA9Q-PRODUCTION-ADAPTERS-004` now states the intended fail-closed semantics explicitly: an absent timestamp uses receiver arrival UTC, while a present-but-invalid timestamp rejects the datagram. Dedicated tests cover both branches. Production adapter behavior was not changed.
