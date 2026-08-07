# M5.2 — Observability and Diagnostics

Adds read-only operational visibility to the approved M4 composition root:

- `/ops/live` process liveness
- `/ops/ready` runtime/dependency readiness
- `/ops/build` build identity
- `/ops/diagnostics` runtime state and counters
- `/ops/metrics` Prometheus text metrics
- structured one-line JSON operational logging

Focused verification: `python3 -m pytest tests/observability -q`.
Full verification: `python3 -m pytest -q`.
