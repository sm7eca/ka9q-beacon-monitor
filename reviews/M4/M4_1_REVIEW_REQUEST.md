# AI Review Request — M4.1 KA9Q Status Receiver

Review:

- `src/ka9q_beacon_monitor/ka9q/status_receiver.py`
- `src/ka9q_beacon_monitor/ka9q/__init__.py`
- `tests/ka9q/test_status_receiver.py`
- `akb/modules/MOD-STATUS-RECEIVER.md`
- M3 domain models imported by the receiver

Run the complete test suite. Verify transport/decoder separation, asynchronous
fault isolation, counter semantics, endpoint validation, direct replay parity,
and absence of invented KA9Q wire-format assumptions.

Return findings with severity, evidence, impact, recommendation, verification
test, confidence, and a JSON summary. Decision rules follow AKB-REVIEW.
