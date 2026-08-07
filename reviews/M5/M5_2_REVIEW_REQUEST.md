# AI Peer Review Request — M5.2 Observability and Diagnostics

Review M5.2 against `akb/modules/MOD-OBSERVABILITY-DIAGNOSTICS.md` and the governing M5 milestone.

Please verify:

1. all eleven normative requirements and all documented failure modes;
2. liveness/readiness separation and fail-closed readiness behavior;
3. Prometheus metrics faithfully reflect existing runtime counters;
4. build identity contains no secret source and has safe fallbacks;
5. JSON logs are parseable and arbitrary extras are not serialized;
6. `/ops/*` integration does not alter approved M4 API/Web UI semantics or lifecycle;
7. focused and full repository tests pass.

Do not invent requirements belonging to M5.3–M5.6.

Report findings with severity, evidence, impact, recommendation, and a verification test where applicable.
