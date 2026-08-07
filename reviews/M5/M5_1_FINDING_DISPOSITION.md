# M5.1.1 Finding Disposition

## M5.1-F-001 — CLOSED

`load_runtime_configuration` now scans every environment key with the `KA9Q_` prefix before applying overrides or secrets. Any prefixed key that is not declared in `_ENV_KEYS` or `_SECRET_ENV_KEYS` raises `ConfigError`.

Verification: `test_unknown_ka9q_environment_key_is_rejected` reproduces the prior typo case (`KA9Q_API_PROT`) and requires fail-closed behavior.

## M5.1-F-002 — CLOSED

`_SECRET_ENV_KEYS` is now the authoritative environment-to-secret-field mapping. Secret loading iterates that mapping rather than hardcoding `KA9Q_VERIFICATION_TOKEN` in a separate read path.

## Regression result

Focused configuration suite: 14 passed.
