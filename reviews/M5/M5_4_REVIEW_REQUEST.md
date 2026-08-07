# AI Review Request — M5.4.1 KA9Q Production Adapters and Phase 0

Re-review M5.4.1 against `akb/modules/MOD-KA9Q-PRODUCTION-ADAPTERS.md` and the governing M5 milestone. Focus on M5.4-F-001 and M5.4-F-002 while confirming no regression elsewhere.

Required review passes:

1. Reproduce the former fabricated-sample scenario and confirm it cannot yield `VERIFIED_CAPTURE` without structured provenance and matching capture bytes.
2. Verify `CaptureProvenance` requires radiod version/revision, hardware ID, network endpoint, capture SHA-256 and UTC interval.
3. Verify checksum mismatch, missing provenance, empty samples, or sample timestamps outside the provenance interval remain `UNVERIFIED`.
4. Confirm the remaining operational trust boundary is documented: checksum/provenance integrity does not alone prove physical capture origin.
5. Verify absent bridge `timestamp_utc` uses receiver arrival time, while a present-but-invalid timestamp is rejected fail-closed.
6. Confirm `production_adapters.py` and all prior approved M4/M5.1-M5.3 production code are otherwise unchanged.
7. Run focused and full tests.
8. Continue to report P0-A-001, P0-A-002 and P0-A-003 as `UNVERIFIED` unless actual field evidence is included.
