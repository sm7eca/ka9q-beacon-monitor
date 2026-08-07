# M5.5 Change Log

## 1.0.1 — 2026-08-07

- Closed M5.5-F-001 with a dedicated receiver/radiod interruption and restart end-to-end regression test.
- The new test verifies persisted-data integrity during transport absence and normal processing after a replacement receiver is created.
- No production code changed in this patch.

## 1.0.0 — 2026-08-07

- Added deterministic replay validation through the approved runtime composition root.
- Added end-to-end persistence, aggregation, REST API and Web UI integration tests.
- Added production status-adapter boundary integration validation.
- Added fault-injection/recovery tests for interruption, malformed input, storage failure, process restart and partial dependency outage.
- Added software validation evidence metadata while preserving Phase-0 field status as `UNVERIFIED`.
- Fixed a cross-module SQLite/FastAPI threading defect discovered by M5.5 by allowing cross-thread SQLite connection use under a repository-owned `RLock`.
