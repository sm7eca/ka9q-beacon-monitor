# M4.9.2 Finding Disposition

## M4.9-F-001 — Closed

The complete M4.9 composition root is restored unchanged except for the narrow
hysteresis feedback correction in `BeaconRuntime._join_and_process`.

The runtime now stores the classifier's raw pre-verification
`detection_state` before invoking `VerificationAnalyzer.verify()`. Therefore a
persisted `VERIFIED_BEACON` state is never fed into `BeaconClassifier`, whose
hysteresis state machine intentionally owns only `NO_SIGNAL`,
`SIGNAL_PRESENT`, and `PROBABLE_BEACON`.

Verification is provided by
`test_verified_observation_preserves_classifier_hysteresis_feedback`, which
first persists a `VERIFIED_BEACON`, then submits an 8 dB observation in the
probable-beacon hysteresis band and requires the next classifier result to
remain `PROBABLE_BEACON`.

## M4.9.1-F-001 — Closed

The accidental replacement of the full composition root has been reverted.
`BeaconRuntime`, `BeaconPipelineConfig`, `RuntimeCounters`, and
`create_main_app` are present again.

## M4.9.1-F-002 — Closed

The unused standalone helper containing `verifier.analyze()` is not retained.
The restored composition root uses the approved `VerificationAnalyzer.verify()`
interface.

## M4.9.1-F-003 — Closed

The GitHub update package does not contain the stray
`tests/test_create_review_package.py` or the stale `TEST_RESULTS_M4_1.txt`.
