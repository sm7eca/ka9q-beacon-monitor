# AI Peer Review Request — M5.7 Production Deployment Integration

## Background

The first real Raspberry Pi 5 / Debian 13 Trixie deployment after M5.6 approval exposed a concrete deployment gap: `main.py` required `--factory`, and the systemd template referenced `deployment_factory:create_app`, but no such production factory existed in the repository.

## Review scope

Review `MOD-PRODUCTION-DEPLOYMENT-INTEGRATION.md`, `deployment_factory.py`, the CLI change in `main.py`, Pi no-SDR configuration/templates, systemd unit, smoke script and tests.

## Required review passes

1. Verify that no approved M4/M5 domain semantics are reimplemented or changed.
2. Verify `no_sdr` starts the composed software stack without multicast/SDR/bridge dependencies.
3. Verify no-SDR operation cannot be confused with Phase-0 field evidence.
4. Verify `ka9q` and verification-enabled configurations fail closed when required bridge commands are absent.
5. Verify beacon runtime/API configuration comes from one deployment source.
6. Verify CLI -> concrete factory -> Uvicorn wiring is executable rather than documentary.
7. Verify the systemd factory path exists and is importable.
8. Run focused tests and the full suite.

## Expected decision rule

Any missing concrete startup path, silent fallback to fake hardware data, or weakening of configuration/Phase-0 boundaries is HIGH or CRITICAL.
