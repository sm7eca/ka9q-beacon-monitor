# AI Peer Review Request — M4.3 Classifier

Review the classifier implementation, tests and AKB contract against the approved M3 domain model and M4.1/M4.2 pipeline.

## Scope

- `src/ka9q_beacon_monitor/processing/classifier.py`
- `tests/processing/test_classifier.py`
- `akb/modules/MOD-CLASSIFIER.md`
- Relevant M3 model and AKB dependency files.

## Mandatory passes

1. Contract/code consistency.
2. Threshold and hysteresis correctness.
3. `NO_DATA` evidence handling.
4. Reference-channel aggregation and disagreement handling.
5. Observation invariant compliance.
6. Determinism and test completeness.
7. Confirmation that KA9Q-reported SNR is not a classification dependency.
8. Confirmation that the module contains no DSP, persistence or network I/O.

Run the complete test suite and report exact counts.
