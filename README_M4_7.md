# M4.7 REST API

Adds a read-only FastAPI layer for health, beacon catalog, observations and interval summaries.

Run tests:

```bash
python3 -m pytest -q
```

Create review package:

```bash
python3 tools/create_review_package.py M4.7
```


## M4.7.1

- Unknown beacon IDs now return HTTP 404 consistently on all observation and summary routes.
- Added regression coverage for all four history routes.
- Completed `MOD-REST-API.md` according to the normative AKB section schema.
