# M5.1 — Configuration & Secrets

M5.1 adds a validated startup configuration boundary without changing approved M4 behavior.

Key properties:
- JSON for non-secret deployment configuration.
- Explicit `KA9Q_*` environment overrides.
- Secrets accepted only through dedicated environment variables.
- Strict unknown-key and secret-like-key rejection.
- Fail-closed validation before external resources start.
- Redacted secret rendering.

Run focused tests:

```bash
python3 -m pytest tests/config -q
```

Create review package:

```bash
python3 tools/create_review_package.py M5.1
```
