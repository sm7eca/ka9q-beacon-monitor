# M5.7 Change Log

- Added concrete production deployment factory.
- Changed CLI factory invocation so the selected runtime config path reaches the factory.
- Added strict deployment-specific configuration separate from M5.1 runtime configuration.
- Added explicit no-SDR deployment/smoke-test mode.
- Added Raspberry Pi 5 no-SDR runtime/deployment examples.
- Updated systemd service to invoke the real factory.
- Added no-SDR smoke script and focused integration tests.
- Added M5.7 AKB contract and AI review request.

## M5.7.1

- Removed stale `KA9Q_ASGI_FACTORY` from the deployment environment example.
- Added AKB `Purpose` and `depends_on`.
- Added M5.7 to the top-level M5 delivery plan and ensured review configuration is included in the M5.7 review package.
- No production code changed.

## M5.7.2

- Aligned `deploy/runtime.env.example` with the M5.1 `KA9Q_*` environment whitelist after a real Raspberry Pi 5 systemd startup exposed stale unsupported variables.
- Added a regression test preventing unsupported environment keys from returning to the template.
- Added field-discovered finding disposition.
- No application production code changed.

## M5.7.3

- Added a shared registry for observability build-identity environment names.
- M5.1 now accepts registered cross-module metadata while continuing to reject unknown `KA9Q_*` variables.
- Restored supported build identity values to `runtime.env.example`.
- Added regression tests and AKB traceability updates.
## M5.7.4

- Added executable proof that BuildIdentity consumes the shared environment registry aliases.
- Added observability/core.py explicitly to the M5.7 review package.
- Closed M5.7.3-F-001.

