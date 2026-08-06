---
id: MOD-MEASUREMENT-BUILDER
title: Measurement Window Builder
version: 1.0.1
status: DRAFT
owner: Runtime
normative: true
depends_on:
  - ARCH-RUNTIME
  - ARCH-EVENTS
  - DM-STATUS-SAMPLE
  - DM-MEASUREMENT-WINDOW
  - MOD-STATUS-RECEIVER
provides:
  - measurement-window-grouping
  - event-time-window-closing
consumes:
  - normalized-status-sample
verified_by:
  - TEST-MOD-MEASUREMENT-BUILDER
---

# Purpose

Define the runtime component that groups normalized `StatusSample` objects into
UTC-aligned, ten-second `MeasurementWindow` objects without classification,
persistence, or verification DSP.

# Scope

The module owns event-time window alignment, per-channel buffering, deterministic
window closure, explicit clock advancement, late-sample rejection, counters,
and downstream handler isolation. It does not synthesize empty windows.

# Responsibilities

- Assign each sample to the UTC-aligned ten-second window containing its source timestamp.
- Maintain at most one open window per channel.
- Close an earlier window when a sample for a later window arrives.
- Close due windows when `advance_time` is called.
- Preserve all accepted samples and delegate ordering/metrics to `MeasurementWindow`.
- Reject samples for a window already closed.
- Isolate downstream handler and error-handler failures.

# Definitions

| Term | Definition |
|---|---|
| Event time | The `StatusSample.timestamp_utc` used for window assignment. |
| Clock advancement | Explicit call that closes windows whose exclusive end is not later than the supplied UTC time. |
| Late sample | A sample belonging to a window that the builder has already closed for that channel. |
| Flush | Controlled shutdown operation that emits all currently open non-empty windows. |

# Normative Requirements

- **MOD-MEASUREMENT-BUILDER-001:** Window starts SHALL be aligned to UTC seconds divisible by ten, with zero microseconds.
- **MOD-MEASUREMENT-BUILDER-002:** The builder SHALL maintain independent window state for each `channel_id`.
- **MOD-MEASUREMENT-BUILDER-003:** Each accepted sample SHALL appear exactly once in one emitted `MeasurementWindow`.
- **MOD-MEASUREMENT-BUILDER-004:** A sample for a later window SHALL close the currently open earlier window for that channel before the new sample is buffered.
- **MOD-MEASUREMENT-BUILDER-005:** `advance_time(now_utc)` SHALL close every open window whose exclusive end is less than or equal to `now_utc`.
- **MOD-MEASUREMENT-BUILDER-006:** The builder SHALL NOT synthesize empty windows.
- **MOD-MEASUREMENT-BUILDER-007:** A sample belonging to a previously closed window SHALL be rejected as late and SHALL NOT reopen or modify that window.
- **MOD-MEASUREMENT-BUILDER-008:** Downstream handler failure SHALL be isolated, counted, reported when possible, and SHALL NOT prevent later windows from being processed.
- **MOD-MEASUREMENT-BUILDER-009:** `flush()` SHALL emit every currently open non-empty window in deterministic `(start_utc, channel_id)` order.
- **MOD-MEASUREMENT-BUILDER-010:** This module SHALL NOT perform beacon classification, SNR policy selection, persistence, or verification DSP.
- **MOD-MEASUREMENT-BUILDER-011:** Calls that mutate state for the same `channel_id` SHALL be serialized internally across asynchronous handler waits so that concurrent delivery cannot overwrite or lose an accepted sample.

# Interfaces

```yaml
module: MOD-MEASUREMENT-BUILDER
input:
  type: DM-STATUS-SAMPLE
  method: add_sample
clock:
  method: advance_time
shutdown:
  method: flush
output:
  type: DM-MEASUREMENT-WINDOW
  delivery: callback
future_event_ownership:
  MeasurementWindowClosed: MOD-EVENT-BUS integration adapter
counters:
  - samples_received
  - samples_accepted
  - samples_late
  - windows_emitted
  - handler_failures
```

# Constraints

- Source timestamps must be timezone-aware UTC as required by `DM-STATUS-SAMPLE`.
- Window duration is owned by `DM-MEASUREMENT-WINDOW` and is ten seconds.
- UDP loss is not repaired by this module.
- Empty intervals are represented by absence of an emitted window, not by a synthetic object.
- Event-envelope creation according to `ARCH-EVENTS-002` belongs to the Event Bus integration layer.
- Per-channel state mutation is protected by an internal asynchronous lock; different channels remain independently processable.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Non-UTC clock advancement | Reject the call without changing buffered state. |
| Late sample | Increment `samples_late`; do not alter closed data. |
| Downstream handler raises | Increment `handler_failures`; report when possible; continue. |
| Error handler raises | Suppress and continue. |
| Invalid expected status rate | Construction fails. |
| Flush after prior closure | Do not emit an already closed window again. |
| Concurrent calls for the same channel | Serialize the complete state transition, including downstream handler waits; do not lose or overwrite samples. |

# Traceability

```yaml
governs:
  - src/ka9q_beacon_monitor/processing/measurement_builder.py
verified_by:
  - tests/processing/test_measurement_builder.py
produces_contract:
  - DM-MEASUREMENT-WINDOW
```

# Review Questions

- Is event-time grouping deterministic at exact ten-second boundaries?
- Can a late sample reopen or mutate a closed window?
- Are channels isolated from one another?
- Can a downstream failure stop future window processing?
- Is empty-window behavior explicit and testable?
- Is Event-envelope ownership separated from this domain-processing component?
- Can concurrent same-channel calls cross an `await` point without losing buffered state?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial M4.2 measurement-builder contract. |
| 1.0.1 | 2026-08-06 | Added internal per-channel serialization requirement and concurrency failure mode (M4.2-F-001). |
