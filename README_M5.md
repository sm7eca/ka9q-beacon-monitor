# M5 — Production Readiness and Field Validation

M4 is approved and committed. M5 prepares the application for repeatable deployment and verified operation with real KA9Q/radiod infrastructure.

This start package contains governance files only. It intentionally adds no production code before the M5 scope has been reviewed.

## Planned sequence

1. M5.1 Configuration and Secrets
2. M5.2 Observability and Diagnostics
3. M5.3 Deployment Packaging
4. M5.4 KA9Q Production Adapters and Phase 0
5. M5.5 End-to-End and Failure Validation
6. M5.6 Operations and Release Candidate

## Review package

Run from the repository root:

```bash
python3 tools/create_review_package.py M5
```

The generated package shall contain the M5 milestone contract, this README, the changelog, and the M5 review request.

## M5.0.1 scope corrections

- M5.3 now has a dedicated reproducibility requirement (`MILESTONE-M5-013`).
- M4-preservation is governed only by `MILESTONE-M5-001`; the Constraints section delegates to it.
