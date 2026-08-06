# M3.1 Finding Disposition

| Finding | Decision | Resolution |
|---|---|---|
| DM3-F-001 | Accepted | Re-exported the complete public model API from `model/__init__.py`. |
| DM3-F-002 | Accepted | Removed nonexistent `MeasurementQuality`; `IntervalSummary.quality` now uses `QualityLevel`. |
| DM3-F-003 | Accepted | `StatusSample` uses `pll_locked` and includes validated `sequence_number`. |
| DM3-F-004 | Accepted | Added AM/IQ/UNKNOWN and standardized `SampleQuality.PARTIAL`. |
| DM3-F-005 | Accepted | Implemented finite-number, frequency, sequence and quality-consistency validation. |
| DM3-F-006 | Accepted | Included direct Observation tests covering its invariants. |
| DM3-F-007 | Accepted | Documented first-match-wins evaluation order. |
| DM3-F-008 | Accepted | Standardized sibling enum values to lowercase strings. |
| DM3-F-009 | Accepted | Full suite is executed in this patch release. |
