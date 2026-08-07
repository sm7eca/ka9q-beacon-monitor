# M5.7.2 Deployment Template Finding Disposition

## Field-discovered issue

The first real Raspberry Pi 5 systemd start failed closed because the installed
`runtime.env` contained `KA9Q_API_HOST`, `KA9Q_BUILD_VERSION`, and
`KA9Q_BUILD_REVISION`. M5.1 correctly rejects unknown `KA9Q_*` environment
variables, so the service exited before the ASGI application started.

## Resolution

- `deploy/runtime.env.example` now contains only environment variable names
  accepted by the M5.1 configuration whitelist.
- The default no-SDR EnvironmentFile is intentionally minimal and sets only
  `KA9Q_API_PORT=8000`; other supported overrides are documented as comments.
- A permanent deployment-integration regression test verifies that every
  uncommented `KA9Q_*` key in the template belongs to the configuration
  whitelist.
- No application production code is changed by M5.7.2.
