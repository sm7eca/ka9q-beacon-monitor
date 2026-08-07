# M5.7 Production Deployment Integration

M5.7 closes the deployment gap discovered during the first Raspberry Pi 5 / Debian 13 Trixie installation: the service template referenced a production ASGI factory that was not implemented.

The milestone adds a concrete `ka9q_beacon_monitor.deployment_factory:create_app`, a strict sibling `deployment.json`, an explicit `no_sdr` software-smoke mode, the executable Pi/systemd entrypoint, and deployment integration tests.

`no_sdr` is intentionally software-only. It starts the application without radiod/SDR input and does not alter the Phase-0 `UNVERIFIED` status.

## M5.7.1

Re-review patch closing the deployment-template, AKB schema and top-level milestone traceability findings. No production code changed.
