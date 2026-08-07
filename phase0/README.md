# M5.4 Phase 0 evidence

This directory is for **real** KA9Q radiod/hardware evidence. Repository tests may exercise the evidence analyzer with synthetic samples, but synthetic data SHALL remain `UNVERIFIED` and SHALL NOT close a Phase 0 assumption.

Required field session evidence before M5.4 can be marked field-complete:

1. Capture status datagrams from the selected radiod release and demodulation modes.
2. Record radiod version/revision, hardware, host, multicast group/interface, start/end UTC and capture checksum.
3. Run the selected-release status bridge and retain normalized capture output.
4. Measure status cadence and actual field availability, including whether DEMOD_SNR is present.
5. Measure BASEBAND_POWER for fixed peak RF level over several keyed-CW duty cycles.
6. Exercise PCM/IQ acquisition and verification bridge behavior.
7. Record pass/fail or `UNVERIFIED` for P0-A-001 through P0-A-003; never infer PASS from synthetic fixtures.

`PHASE0_EVIDENCE_TEMPLATE.json` is intentionally unverified until populated from a real session.

## M5.4.1 evidence integrity

`VERIFIED_CAPTURE` requires structured `CaptureProvenance` and capture bytes whose computed SHA-256 matches the recorded checksum. This establishes artifact integrity and provenance completeness, but does not by itself prove physical capture origin. P0-A-001..003 remain `UNVERIFIED` until a real field session is recorded and reviewed.
