# M5.5 AI Review Request — End-to-End and Failure Validation

Review M5.5 against `akb/modules/MOD-END-TO-END-FAILURE-VALIDATION.md` and the approved M5 milestone scope.

## Required review passes

1. Execute `python3 -m pytest tests/validation -q` and the full repository suite.
2. Confirm deterministic replay traverses the real `BeaconRuntime` path through persistence and aggregation.
3. Confirm persisted observations and summaries are visible through the approved REST API and the Web UI surface remains mounted.
4. Confirm the M5.4 production status-adapter boundary is executed without claiming synthetic fixtures are Phase-0 field evidence.
5. Exercise/inspect the six operational failure scenarios: network/radiod interruption, malformed input, storage failure, process restart, partial dependency outage, incomplete field evidence.
6. Review the SQLite cross-thread hardening introduced after M5.5 exposed a real FastAPI worker-thread failure. Confirm serialization via the repository `RLock` and no change to persistence semantics.
7. Confirm performance evidence reports workload/time/throughput but introduces no unsupported release threshold.
8. Diff previously approved modules for unintended semantic changes; only the SQLite thread-safety hardening is expected outside new M5.5 files.

## Known evidence boundary

Phase-0 physical field evidence remains `UNVERIFIED`. Synthetic M5.5 adapter tests are software integration evidence only.

## Expected decision rule

Any failure that permits data corruption, false persistence claims, inability to recover, or silent Phase-0 verification is mandatory. Pure test/document completeness gaps may be lower severity according to the AKB review rules.
