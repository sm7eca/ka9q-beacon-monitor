# M5.7.4 Finding Disposition

## M5.7.3-F-001 — CLOSED

The shared environment registry is now reviewable and executable as a true single source of truth.

- `observability/core.py` imports `KA9Q_BUILD_VERSION_ENV`, `KA9Q_BUILD_REVISION_ENV`, and `KA9Q_BUILD_TIME_UTC_ENV` from `ka9q_beacon_monitor.environment`.
- `BuildIdentity.from_environment()` consumes those imported names rather than duplicating string literals.
- A regression test monkeypatches the imported registry aliases and proves that `BuildIdentity` follows them for version, revision, and build time.
- The M5.7 review package now includes `observability/core.py` explicitly, closing the previous review-visibility gap.

No Phase-0 evidence status or M4 domain semantics are changed.
