from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ka9q_beacon_monitor.model import DemodMode, SampleQuality, StatusSample
from ka9q_beacon_monitor.processing import MeasurementBuilder, align_window_start

UTC = timezone.utc


def sample(channel: str, second: int, *, minute: int = 0) -> StatusSample:
    return StatusSample(
        timestamp_utc=datetime(2026, 8, 6, 12, minute, second, tzinfo=UTC),
        channel_id=channel,
        frequency_hz=144_300_000.0,
        baseband_power_db=-90.0,
        noise_density_db_hz=-120.0,
        gain_db=12.0,
        output_level_db=-18.0,
        headroom_db=6.0,
        pll_locked=None,
        demod_mode=DemodMode.LINEAR,
        sample_quality=SampleQuality.VALID,
        sequence_number=second,
    )


def test_align_window_start_uses_utc_ten_second_boundary() -> None:
    value = datetime(2026, 8, 6, 12, 0, 19, 999999, tzinfo=UTC)
    assert align_window_start(value) == datetime(2026, 8, 6, 12, 0, 10, tzinfo=UTC)


def test_exact_boundary_belongs_to_new_window() -> None:
    assert align_window_start(sample("a", 20).timestamp_utc).second == 20


@pytest.mark.asyncio
async def test_later_sample_closes_previous_window() -> None:
    emitted = []
    builder = MeasurementBuilder(on_window=emitted.append)
    await builder.add_sample(sample("a", 1))
    await builder.add_sample(sample("a", 9))
    await builder.add_sample(sample("a", 10))
    assert len(emitted) == 1
    assert emitted[0].start_utc.second == 0
    assert [item.timestamp_utc.second for item in emitted[0].samples] == [1, 9]
    assert builder.counters.windows_emitted == 1


@pytest.mark.asyncio
async def test_channels_are_independent() -> None:
    emitted = []
    builder = MeasurementBuilder(on_window=emitted.append)
    await builder.add_sample(sample("a", 1))
    await builder.add_sample(sample("b", 2))
    await builder.add_sample(sample("a", 10))
    assert [window.channel_id for window in emitted] == ["a"]
    assert builder.open_channel_count == 2


@pytest.mark.asyncio
async def test_advance_time_closes_due_window_without_synthesizing_empty_window() -> None:
    emitted = []
    builder = MeasurementBuilder(on_window=emitted.append)
    await builder.add_sample(sample("a", 3))
    await builder.advance_time(datetime(2026, 8, 6, 12, 0, 10, tzinfo=UTC))
    await builder.advance_time(datetime(2026, 8, 6, 12, 0, 30, tzinfo=UTC))
    assert len(emitted) == 1
    assert emitted[0].sample_count == 1


@pytest.mark.asyncio
async def test_late_sample_is_rejected() -> None:
    emitted = []
    builder = MeasurementBuilder(on_window=emitted.append)
    await builder.add_sample(sample("a", 1))
    await builder.add_sample(sample("a", 10))
    await builder.add_sample(sample("a", 8))
    assert builder.counters.samples_received == 3
    assert builder.counters.samples_accepted == 2
    assert builder.counters.samples_late == 1
    assert emitted[0].sample_count == 1


@pytest.mark.asyncio
async def test_flush_order_is_deterministic_and_not_repeated() -> None:
    emitted = []
    builder = MeasurementBuilder(on_window=emitted.append)
    await builder.add_sample(sample("b", 11))
    await builder.add_sample(sample("a", 1))
    await builder.add_sample(sample("c", 1))
    await builder.flush()
    await builder.flush()
    assert [(w.start_utc.second, w.channel_id) for w in emitted] == [
        (1 - 1, "a"),
        (0, "c"),
        (10, "b"),
    ]


@pytest.mark.asyncio
async def test_handler_failure_is_isolated_and_reported() -> None:
    errors = []
    calls = 0

    def handler(window):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("downstream")

    builder = MeasurementBuilder(on_window=handler, on_error=errors.append)
    await builder.add_sample(sample("a", 1))
    await builder.add_sample(sample("a", 10))
    await builder.add_sample(sample("a", 20))
    assert builder.counters.handler_failures == 1
    assert builder.counters.windows_emitted == 1
    assert len(errors) == 1


@pytest.mark.asyncio
async def test_error_handler_failure_is_suppressed() -> None:
    def handler(window):
        raise RuntimeError("downstream")

    def error_handler(exc):
        raise RuntimeError("error handler")

    builder = MeasurementBuilder(on_window=handler, on_error=error_handler)
    await builder.add_sample(sample("a", 1))
    await builder.add_sample(sample("a", 10))
    assert builder.counters.handler_failures == 1


@pytest.mark.asyncio
async def test_advance_time_requires_utc() -> None:
    builder = MeasurementBuilder(on_window=lambda window: None)
    await builder.add_sample(sample("a", 1))
    with pytest.raises(ValueError):
        await builder.advance_time(datetime(2026, 8, 6, 12, 0, 10))
    assert builder.open_channel_count == 1


def test_expected_status_rate_must_be_positive() -> None:
    with pytest.raises(ValueError):
        MeasurementBuilder(on_window=lambda window: None, expected_status_rate_hz=0)

@pytest.mark.asyncio
async def test_concurrent_same_channel_samples_are_serialized_without_loss() -> None:
    import asyncio

    emitted = []
    handler_entered = asyncio.Event()
    release_handler = asyncio.Event()

    async def handler(window):
        emitted.append(window)
        if len(emitted) == 1:
            handler_entered.set()
            await release_handler.wait()

    builder = MeasurementBuilder(on_window=handler)
    await builder.add_sample(sample("a", 1))

    first = asyncio.create_task(builder.add_sample(sample("a", 10)))
    await handler_entered.wait()
    second = asyncio.create_task(builder.add_sample(sample("a", 11)))
    await asyncio.sleep(0)
    release_handler.set()
    await asyncio.gather(first, second)
    await builder.flush()

    all_samples = [item for window in emitted for item in window.samples]
    assert [item.timestamp_utc.second for item in all_samples] == [1, 10, 11]
    assert builder.counters.samples_accepted == 3
