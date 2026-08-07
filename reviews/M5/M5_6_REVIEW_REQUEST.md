# M5.6 AI Re-review Request

Re-review M5.6 Operations and Release Candidate against `MOD-OPERATIONS-RELEASE-CANDIDATE.md` and `reviews/M5/M5_6_FINDING_DISPOSITION.md`.

Run `python3 -m pytest tests/operations -q` and the full suite. Verify M5.6-F-001 through M5.6-F-003 are closed: dedicated Shutdown/Restart runbook sections exist, AKB `provides`/`consumes` tags are present, and a simulated restore copy failure cleans `.restore-next` while preserving the active SQLite database. Confirm Phase-0 remains UNVERIFIED and separate from software release readiness.
