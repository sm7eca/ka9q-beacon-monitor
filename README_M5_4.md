# M5.4 — KA9Q Production Adapters and Phase 0

M5.4 adds production-facing adapter boundaries for the selected `ka9q-radio` release and an auditable Phase 0 evidence workflow.

The Python code deliberately does not hard-code a guessed KA9Q metadata grammar. A deployment bridge validated against the selected radiod release performs version-specific decoding and emits the narrow JSON contract consumed by the approved M4 adapter boundary.

M5.4.1 hardens Phase 0 evidence integrity. `VERIFIED_CAPTURE` now requires structured radiod/hardware/network/UTC/checksum provenance plus actual capture bytes whose computed SHA-256 matches the provenance. Synthetic fixtures without this evidence cannot be labeled verified.

The repository still includes only an `UNVERIFIED` Phase 0 template. Actual P0-A-001..003 conclusions require a real captured field session and evidence review.

Focused tests:

```bash
python3 -m pytest tests/ka9q/test_production_adapters.py tests/ka9q/test_phase0.py -q
```
