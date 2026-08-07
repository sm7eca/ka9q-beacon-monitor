# M5.5 End-to-End and Failure Validation

M5.5 validates the approved system as one composition rather than as isolated modules.

The focused suite covers deterministic replay, persistence, aggregation, REST API visibility, Web UI mounting, the production status-adapter boundary, explicit receiver/radiod interruption and restart recovery, malformed-input isolation, storage failure/recovery, process restart, and readiness behavior during partial dependency outage.

The receiver-restart regression test persists data through the real runtime, disposes the active receiver, verifies stored data remains available through the REST API, recreates the receiver, and proves that later samples continue through the same runtime and repository without losing earlier data.

During development this validation exposed a real integration issue: `SQLiteRepository` connections created in the runtime thread could not be used by FastAPI synchronous endpoints running in worker threads. The repository uses SQLite `check_same_thread=False` together with an internal re-entrant lock to serialize connection access while preserving existing transaction and persistence semantics.

Phase-0 field evidence remains `UNVERIFIED`; M5.5 synthetic adapter execution does not alter that status.
