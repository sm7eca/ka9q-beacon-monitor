from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from ka9q_beacon_monitor.model import (
    DetectionState,
    MeasurementSource,
    Observation,
    QualityLevel,
    SummaryState,
)
from ka9q_beacon_monitor.processing.interval_aggregator import (
    AggregatorPolicy,
    IntervalAggregator,
    align_interval_start,
)

UTC = timezone.utc


def observation(
    second: int,
    *,
    minute: int = 0,
    beacon_id: str = "SK6VHF",
    snr: float = 8.0,
) -> Observation:
    start = datetime(2026, 8, 6, 12, minute, second, tzinfo=UTC)
    return Observation(
        beacon_id=beacon_id,
        window_start_utc=start,
        window_end_utc=start + timedelta(seconds=10),
        detection_state=DetectionState.PROBABLE_BEACON,
        measurement_source=MeasurementSource.STATUS_ONLY,
        derived_local_snr_db=snr,
        verification_snr_db=None,
        ka9q_reported_snr_db=None,
        measurement_quality=QualityLevel.NOMINAL,
        verification_quality=QualityLevel.INVALID,
        identification_quality=QualityLevel.INVALID,
        verification_accepted=False,
        reason_code="probable_beacon",
    )


def test_aligns_to_half_hour_boundary() -> None:
    value = datetime(2026, 8, 6, 12, 44, 59, 999999, tzinfo=UTC)
    assert align_interval_start(value) == datetime(2026, 8, 6, 12, 30, tzinfo=UTC)


def test_policy_validates_divisibility_and_thresholds() -> None:
    with pytest.raises(ValueError):
        AggregatorPolicy(interval_seconds=31, observation_period_seconds=10)
    with pytest.raises(ValueError):
        AggregatorPolicy(weak_threshold_db=8, audible_threshold_db=6)


@pytest.mark.asyncio
async def test_emits_summary_when_next_interval_arrives() -> None:
    emitted = []
    aggregator = IntervalAggregator(on_summary=emitted.append)
    assert await aggregator.add_observation(observation(0))
    next_obs = Observation(
        beacon_id="SK6VHF",
        window_start_utc=datetime(2026,8,6,12,30,tzinfo=UTC),
        window_end_utc=datetime(2026,8,6,12,30,10,tzinfo=UTC),
        detection_state=DetectionState.PROBABLE_BEACON,
        measurement_source=MeasurementSource.STATUS_ONLY,
        derived_local_snr_db=8.0,
        verification_snr_db=None,
        ka9q_reported_snr_db=None,
        measurement_quality=QualityLevel.NOMINAL,
        verification_quality=QualityLevel.INVALID,
        identification_quality=QualityLevel.INVALID,
        verification_accepted=False,
        reason_code="probable_beacon",
    )
    assert await aggregator.add_observation(next_obs)
    assert len(emitted) == 1
    assert emitted[0].interval_start_utc == datetime(2026,8,6,12,0,tzinfo=UTC)


@pytest.mark.asyncio
async def test_duplicate_window_is_rejected() -> None:
    aggregator = IntervalAggregator(on_summary=lambda _: None)
    item = observation(0)
    assert await aggregator.add_observation(item)
    assert not await aggregator.add_observation(item)
    assert aggregator.counters.observations_rejected == 1


@pytest.mark.asyncio
async def test_late_observation_after_close_is_rejected() -> None:
    emitted = []
    aggregator = IntervalAggregator(on_summary=emitted.append)
    await aggregator.add_observation(observation(0))
    await aggregator.advance_time(datetime(2026,8,6,12,30,tzinfo=UTC))
    assert not await aggregator.add_observation(observation(10))
    assert len(emitted) == 1


@pytest.mark.asyncio
async def test_advance_time_requires_utc_before_mutation() -> None:
    aggregator = IntervalAggregator(on_summary=lambda _: None)
    await aggregator.add_observation(observation(0))
    with pytest.raises(ValueError):
        await aggregator.advance_time(datetime(2026,8,6,12,30))
    assert aggregator.counters.summaries_published == 0


@pytest.mark.asyncio
async def test_flush_is_deterministic_by_start_then_beacon() -> None:
    order = []
    aggregator = IntervalAggregator(on_summary=lambda summary: order.append(summary.beacon_id))
    await aggregator.add_observation(observation(0, beacon_id="B"))
    await aggregator.add_observation(observation(0, beacon_id="A"))
    await aggregator.flush()
    assert order == ["A", "B"]


@pytest.mark.asyncio
async def test_handler_failure_is_isolated_and_counted() -> None:
    errors = []
    def fail(_):
        raise RuntimeError("boom")
    aggregator = IntervalAggregator(on_summary=fail, on_error=errors.append)
    await aggregator.add_observation(observation(0))
    await aggregator.flush()
    assert aggregator.counters.summary_handler_failures == 1
    assert len(errors) == 1


@pytest.mark.asyncio
async def test_no_empty_intervals_are_synthesized() -> None:
    emitted = []
    aggregator = IntervalAggregator(on_summary=emitted.append)
    await aggregator.advance_time(datetime(2026,8,6,13,0,tzinfo=UTC))
    assert emitted == []


@pytest.mark.asyncio
async def test_concurrent_same_beacon_observations_are_not_lost() -> None:
    emitted = []
    handler_entered = asyncio.Event()
    release_handler = asyncio.Event()
    handler_calls = 0

    async def blocking_handler(summary) -> None:
        nonlocal handler_calls
        handler_calls += 1
        emitted.append(summary)
        if handler_calls == 1:
            handler_entered.set()
            await release_handler.wait()

    aggregator = IntervalAggregator(on_summary=blocking_handler)
    await aggregator.add_observation(observation(0))

    transition = asyncio.create_task(
        aggregator.add_observation(observation(0, minute=30))
    )
    await handler_entered.wait()

    concurrent = asyncio.create_task(
        aggregator.add_observation(observation(10, minute=30))
    )
    await asyncio.sleep(0)
    assert not concurrent.done()

    release_handler.set()
    assert await transition
    assert await concurrent
    await aggregator.flush()

    total_observations = sum(summary.observation_count for summary in emitted)
    assert total_observations == 3
    assert emitted[-1].observation_count == 2


@pytest.mark.asyncio
async def test_summary_uses_domain_factory_and_expected_count() -> None:
    emitted = []
    aggregator = IntervalAggregator(on_summary=emitted.append)
    await aggregator.add_observation(observation(0, snr=10.0))
    await aggregator.flush()
    summary = emitted[0]
    assert summary.expected_observation_count == 180
    assert summary.observation_count == 1
    assert summary.final_state is SummaryState.NO_DATA
