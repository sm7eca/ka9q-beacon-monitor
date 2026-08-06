# M4.9.1 Finding Disposition

## M4.9-F-001 — Closed

The composition root now retains the classifier's raw pre-verification
`DetectionState` independently per beacon. The post-verification persisted state
is no longer fed back into the classifier hysteresis machine.

A defensive mapping treats any legacy `VERIFIED_BEACON` feedback as
`PROBABLE_BEACON`.

## Verification

- A verified observation cannot replace the classifier feedback state.
- Feedback remains independent per beacon.
- `VERIFIED_BEACON` is never passed directly to classifier hysteresis.
