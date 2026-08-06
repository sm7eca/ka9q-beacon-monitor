# M3.1 Re-review Request

Review the complete domain-model patch against the five AKB data contracts.

Required checks:
1. Run `python3 -m pytest -q`.
2. Verify all public model symbols import from `ka9q_beacon_monitor.model`.
3. Compare fields, enum values and invariants against each `DM-*.md` contract.
4. Confirm `QualityLevel` is the sole quality enum used by Observation and IntervalSummary.
5. Confirm StatusSample validation and enum completeness.
6. Confirm IntervalSummary rules are first-match-wins in documented order.
7. Report Critical/High/Medium/Low findings and a JSON summary.
