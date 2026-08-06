# M4.4 AI Review Request — Verification Analyzer

Review the M4.4 Verification Analyzer against:

- `akb/modules/MOD-VERIFICATION-ANALYZER.md`
- `akb/data/DM-OBSERVATION.md`
- `src/ka9q_beacon_monitor/processing/verification_analyzer.py`
- `tests/processing/test_verification_analyzer.py`

Also inspect prior M4 modules and tests for integration consistency.

Mandatory review passes:

1. Contract-to-code field and behavior matching.
2. Selective verification scope and backend separation.
3. Evidence identity correlation.
4. Acceptance/rejection policy determinism.
5. Observation invariant compliance.
6. Backend exception isolation.
7. Test coverage for every normative requirement and failure mode.
8. Full test-suite execution.

Return decision, findings with severity/evidence/impact/recommendation/test, and JSON summary.
