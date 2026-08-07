# Operations Runbook

## Install / upgrade / rollback
Use the verified M5.3 deployment archive and its `install_release` / `rollback_release` workflow. Never mutate files under an installed version directory.

## Startup validation
Load M5.1 configuration before opening external resources. A configuration or secret error blocks startup.


## Shutdown
Use `systemctl stop ka9q-beacon-monitor` for a routine graceful stop. The service shutdown path SHALL allow the approved `BeaconRuntime.close()` sequence to complete in order: stop receivers, flush measurement windows, flush interval summaries, then close the repository. After shutdown, `/ops/live` is expected to be unavailable because the process is no longer running; persistent data SHALL remain intact.

## Restart
Use `systemctl restart ka9q-beacon-monitor` for a routine restart after configuration or service-level maintenance. After restart, verify `/ops/live` first, then `/ops/ready`, then inspect `/ops/diagnostics` and `/ops/metrics`. Confirm previously persisted observations remain readable and that new observations resume before declaring the restart complete.

## Health and diagnostics
Use `/ops/live` for process liveness, `/ops/ready` for dependency-aware readiness, `/ops/metrics` for metrics and `/ops/diagnostics` for build/runtime diagnostics.

## Backup
Stop writes or use the supplied SQLite online-backup helper. Record the returned SHA-256 beside the backup and keep both outside the release directory.

## Restore
Verify the recorded SHA-256 and SQLite integrity before atomically replacing the database. Never restore an unverified backup.

## Incident recovery
For radiod/network loss, keep persisted data intact, restore connectivity/receiver, then verify new observations reach API/UI. For storage errors, resolve storage first and use readiness/diagnostics to confirm recovery.

## Phase 0
P0-A-001 through P0-A-003 remain UNVERIFIED until a real field capture with reviewed custody/provenance is recorded. Software-only evidence must not clear these blockers.
