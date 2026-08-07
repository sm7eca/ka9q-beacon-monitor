# M5.3 — Deployment Packaging

M5.3 provides deterministic deployment archives, SHA-256 release manifests, versioned releases, atomic upgrade/rollback pointers, and Linux service templates without implementing M5.4 hardware adapters.

M5.3.1 adds permanent regression coverage for all Failure Modes identified in AI review M5.3-F-001. Production code is unchanged.

Focused verification:

```bash
python3 -m pytest tests/deployment -q
```

Full verification:

```bash
python3 -m pytest -q
```
