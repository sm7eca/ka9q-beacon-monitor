# M4.2 Measurement Builder

Copy the package contents into the repository root, preserving paths.

This delivery adds:

- `MeasurementBuilder` with per-channel UTC-aligned ten-second windows
- late-sample rejection and explicit clock advancement
- deterministic shutdown flush
- downstream failure isolation and counters
- `MOD-MEASUREMENT-BUILDER` AKB contract
- M4.1.1 Event-envelope ownership clarification
- explicit receiver default-UTC test

Run:

```bash
python3 -m pytest -q
```

Expected result: `73 passed`.
