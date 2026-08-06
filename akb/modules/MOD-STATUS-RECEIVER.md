---
id: MOD-STATUS-RECEIVER
title: KA9Q Status Receiver
version: 1.0.1
status: DRAFT
owner: Runtime
normative: true
depends_on:
  - ARCH-KA9Q
  - ARCH-RUNTIME
  - ARCH-EVENTS
  - DM-STATUS-SAMPLE
provides:
  - ka9q-status-transport
  - normalized-status-sample-publication
consumes:
  - udp-multicast-datagram
verified_by:
  - TEST-MOD-STATUS-RECEIVER
---

# Purpose

Define the transport boundary that receives KA9Q radiod status multicast,
dispatches each complete datagram to a version-specific decoder, and publishes a
validated `StatusSample` without beacon classification or derived DSP.

# Scope

The module owns IPv4 UDP multicast membership, datagram size validation,
receipt timestamping, decoder dispatch, consumer dispatch, counters, and fault
isolation. The exact binary KA9Q status/TLV mapping is owned by a separate
decoder contract and SHALL be verified against the selected radiod release in
Phase 0.

# Responsibilities

- Receive complete UDP multicast datagrams.
- Timestamp receipt in UTC.
- Reject empty and oversized datagrams.
- Invoke exactly one configured `StatusDatagramDecoder` per datagram.
- Deliver at most one validated `StatusSample` per accepted datagram to the configured next-layer consumer.
- Isolate malformed datagrams and consumer failures.
- Maintain monotonic operational counters.
- Support direct datagram replay for tests and hardware-in-the-loop fixtures.

# Definitions

| Term | Definition |
|---|---|
| Datagram decoder | Version-specific adapter that maps one KA9Q status datagram to one normalized `StatusSample`. |
| Transport error | Socket-level error reported independently of a received datagram. |
| Rejected datagram | Datagram that fails size validation or decoder normalization. |
| Published sample | Sample successfully delivered to the configured consumer. |

# Normative Requirements

- **MOD-STATUS-RECEIVER-001:** The receiver SHALL accept only a validated IPv4 multicast group and UDP port.
- **MOD-STATUS-RECEIVER-002:** Each non-empty datagram within the configured maximum size SHALL be passed once to the decoder.
- **MOD-STATUS-RECEIVER-003:** Receipt timestamps SHALL be timezone-aware UTC values.
- **MOD-STATUS-RECEIVER-004:** A decoder failure SHALL reject only the affected datagram and SHALL NOT stop subsequent processing.
- **MOD-STATUS-RECEIVER-005:** A consumer failure SHALL NOT count the sample as published and SHALL NOT stop subsequent processing.
- **MOD-STATUS-RECEIVER-006:** The receiver SHALL deliver no more than one `StatusSample` to its next-layer consumer for one input datagram.
- **MOD-STATUS-RECEIVER-007:** The receiver SHALL expose counters for received, published, rejected, and consumer-failure outcomes.
- **MOD-STATUS-RECEIVER-008:** The transport layer SHALL NOT implement beacon classification, local SNR derivation, persistence, or verification DSP.
- **MOD-STATUS-RECEIVER-009:** The binary KA9Q decoder SHALL be replaceable without modifying multicast transport behavior.
- **MOD-STATUS-RECEIVER-010:** Direct `process_datagram` replay SHALL use the same validation and dispatch path as live multicast input.

# Interfaces

```yaml
module: MOD-STATUS-RECEIVER
configuration:
  group: IPv4 multicast address
  port: UDP port
  interface: local IPv4 interface or 0.0.0.0
  receive_buffer_bytes: positive integer
  max_datagram_bytes: 1..65535
input:
  type: udp-multicast-datagram
decoder:
  interface: StatusDatagramDecoder.decode
  output: DM-STATUS-SAMPLE
delivers:
  - DM-STATUS-SAMPLE
event_ownership:
  StatusSampleReceived: MOD-EVENT-BUS integration adapter
  StatusDatagramRejected: MOD-EVENT-BUS integration adapter
counters:
  - datagrams_received
  - samples_published
  - datagrams_rejected
  - handler_failures
```

# Constraints

- The initial implementation supports IPv4 multicast only.
- UDP ordering and delivery are not guaranteed.
- The receiver does not synthesize missing sequence numbers.
- Decoder output must already satisfy `DM-STATUS-SAMPLE` validation.
- Actual KA9Q wire field identifiers and endianness remain a Phase 0 verification item.

# Failure Modes

| Failure | Required behavior |
|---|---|
| Invalid multicast endpoint | Construction fails before socket creation. |
| Empty or oversized datagram | Reject and increment `datagrams_rejected`. |
| Malformed or unsupported wire data | Decoder raises; reject only that datagram. |
| Consumer raises | Increment `handler_failures`; do not increment `samples_published`. |
| Error callback raises | Suppress callback failure and continue. |
| Socket startup failure | Close the temporary socket and propagate startup failure. |

# Traceability

```yaml
governs:
  - src/ka9q_beacon_monitor/ka9q/status_receiver.py
verified_by:
  - tests/ka9q/test_status_receiver.py
future_decoder_contract:
  - IF-KA9Q-STATUS
```

# Review Questions

- Is transport cleanly separated from the version-specific wire decoder?
- Can one malformed datagram or consumer failure stop future reception?
- Does every counter have one unambiguous increment condition?
- Is live input behavior reproducible through direct datagram replay?
- Are all assumptions about the KA9Q binary format explicitly deferred rather than invented?

# Change History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-08-06 | Initial M4.1 receiver contract. |
| 1.0.1 | 2026-08-06 | Clarified that this module delivers domain objects; ARCH-EVENTS-002 event envelopes are owned by the Event Bus integration layer. |
