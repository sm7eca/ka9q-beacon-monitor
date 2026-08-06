from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest

from ka9q_beacon_monitor.ka9q import (
    Ka9qStatusReceiver,
    MulticastEndpoint,
    StatusDecodeError,
)
from ka9q_beacon_monitor.model import DemodMode, SampleQuality, StatusSample


class FakeDecoder:
    def decode(self, datagram, *, received_at_utc, source):
        if datagram == b"bad":
            raise StatusDecodeError("malformed")
        return StatusSample(
            timestamp_utc=received_at_utc,
            channel_id="beacon-1-signal",
            frequency_hz=144_412_000.0,
            baseband_power_db=-95.0,
            noise_density_db_hz=-121.0,
            gain_db=0.0,
            output_level_db=-18.0,
            headroom_db=12.0,
            demod_mode=DemodMode.LINEAR,
            pll_locked=None,
            sequence_number=7,
            sample_quality=SampleQuality.VALID,
        )


def endpoint(**changes):
    values = {"group": "239.1.2.3", "port": 5006}
    values.update(changes)
    return MulticastEndpoint(**values)


def run(coro):
    return asyncio.run(coro)


def test_endpoint_requires_multicast_group():
    with pytest.raises(ValueError, match="multicast"):
        endpoint(group="192.0.2.1")


def test_endpoint_validates_port_and_sizes():
    with pytest.raises(ValueError, match="port"):
        endpoint(port=0)
    with pytest.raises(ValueError, match="receive_buffer"):
        endpoint(receive_buffer_bytes=0)
    with pytest.raises(ValueError, match="max_datagram"):
        endpoint(max_datagram_bytes=0)


def test_valid_datagram_is_decoded_and_published():
    received = []
    receiver = Ka9qStatusReceiver(endpoint(), FakeDecoder(), received.append)
    timestamp = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)

    sample = run(receiver.process_datagram(b"ok", ("192.0.2.20", 5006), received_at_utc=timestamp))

    assert sample is received[0]
    assert sample.timestamp_utc == timestamp
    assert receiver.counters.datagrams_received == 1
    assert receiver.counters.samples_published == 1
    assert receiver.counters.datagrams_rejected == 0


def test_async_sample_handler_is_supported():
    received = []

    async def handler(sample):
        await asyncio.sleep(0)
        received.append(sample)

    receiver = Ka9qStatusReceiver(endpoint(), FakeDecoder(), handler)
    run(receiver.process_datagram(b"ok"))

    assert len(received) == 1
    assert receiver.counters.samples_published == 1


def test_decode_error_is_isolated_and_reported():
    errors = []
    receiver = Ka9qStatusReceiver(
        endpoint(), FakeDecoder(), lambda sample: None,
        on_error=lambda exc, data, source: errors.append((exc, data, source)),
    )

    result = run(receiver.process_datagram(b"bad", ("192.0.2.20", 5006)))

    assert result is None
    assert receiver.counters.datagrams_received == 1
    assert receiver.counters.datagrams_rejected == 1
    assert receiver.counters.samples_published == 0
    assert isinstance(errors[0][0], StatusDecodeError)
    assert errors[0][1] == b"bad"


def test_empty_and_oversized_datagrams_are_rejected_before_decode():
    receiver = Ka9qStatusReceiver(endpoint(max_datagram_bytes=3), FakeDecoder(), lambda sample: None)

    assert run(receiver.process_datagram(b"")) is None
    assert run(receiver.process_datagram(b"1234")) is None
    assert receiver.counters.datagrams_rejected == 2


def test_consumer_failure_does_not_count_as_published():
    errors = []

    def failing_handler(sample):
        raise RuntimeError("consumer failed")

    receiver = Ka9qStatusReceiver(
        endpoint(), FakeDecoder(), failing_handler,
        on_error=lambda exc, data, source: errors.append(exc),
    )

    result = run(receiver.process_datagram(b"ok"))

    assert result is None
    assert receiver.counters.handler_failures == 1
    assert receiver.counters.samples_published == 0
    assert isinstance(errors[0], RuntimeError)


def test_error_handler_failure_is_isolated():
    def failing_error_handler(exc, data, source):
        raise RuntimeError("error reporter failed")

    receiver = Ka9qStatusReceiver(
        endpoint(), FakeDecoder(), lambda sample: None,
        on_error=failing_error_handler,
    )

    assert run(receiver.process_datagram(b"bad")) is None
    assert receiver.counters.datagrams_rejected == 1


def test_close_without_start_is_safe():
    receiver = Ka9qStatusReceiver(endpoint(), FakeDecoder(), lambda sample: None)
    run(receiver.close())
    assert receiver.is_running is False


def test_default_timestamp_is_utc_aware():
    received = []

    class Decoder:
        def decode(self, datagram, *, received_at_utc, source):
            assert received_at_utc.tzinfo is not None
            assert received_at_utc.utcoffset().total_seconds() == 0
            received.append(received_at_utc)
            return FakeDecoder().decode(
                datagram, received_at_utc=received_at_utc, source=source
            )

    receiver = Ka9qStatusReceiver(endpoint(), Decoder(), lambda sample: None)
    run(receiver.process_datagram(b"ok"))
    assert len(received) == 1
