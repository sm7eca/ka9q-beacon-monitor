# M4.4 Verification Analyzer

Adds selective verification orchestration for `PROBABLE_BEACON` observations.

## Included

- Verification policy, request, evidence, backend protocol, and analyzer.
- Deterministic upgrade/rejection behavior.
- Backend failure isolation.
- CW/SNR/frequency/quality/callsign gates.
- Formal AKB contract and review request.

## Test

```bash
python3 -m pytest -q
```

## Review package

```bash
python3 tools/create_review_package.py M4.4
```
