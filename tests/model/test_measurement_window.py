from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from ka9q_beacon_monitor.model import (
    DemodMode,
    MeasurementWindow,
    SampleQuality,
    StatusSample,
)


def sample(ts: datetime, channel_id: str = "beacon-1", power: float = -70.0) -> StatusSample:
    return StatusSample(
        timestamp_utc=ts,
        channel_id=channel_id,
        frequency_hz=144_412_000.0,
        baseband_power_db=power,
        noise_density_db_hz=-110.0,
        gain_db=10.0,
        output_level_db=-20.0,
        headroom_db=12.0,
        pll_lock=None,
        demod_mode=DemodMode.LINEAR,
        sample_quality=SampleQuality.VALID,
    )


def start() -> datetime:
    return datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc)


def test_window_is_exactly_ten_seconds() -> None:
    window = MeasurementWindow(channel_id="beacon-1", start_utc=start())
    assert window.end_utc - window.start_utc == timedelta(seconds=10)


def test_expected_count_and_coverage_at_two_hz() -> None:
    samples = [sample(start() + timedelta(milliseconds=500 * i)) for i in range(20)]
    window = MeasurementWindow.from_samples(channel_id="beacon-1", start_utc=start(), samples=samples)
    assert window.expected_sample_count == 20
    assert window.sample_count == 20
    assert window.coverage_ratio == 1.0
    assert window.coverage_percent == 100.0


def test_partial_coverage() -> None:
    samples = [sample(start() + timedelta(seconds=i)) for i in range(10)]
    window = MeasurementWindow.from_samples(channel_id="beacon-1", start_utc=start(), samples=samples)
    assert window.coverage_ratio == 0.5


def test_samples_are_sorted() -> None:
    later = sample(start() + timedelta(seconds=2))
    earlier = sample(start() + timedelta(seconds=1))
    window = MeasurementWindow.from_samples(
        channel_id="beacon-1", start_utc=start(), samples=[later, earlier]
    )
    assert window.samples == (earlier, later)


def test_rejects_other_channel() -> None:
    with pytest.raises(ValueError, match="channel_id"):
        MeasurementWindow.from_samples(
            channel_id="beacon-1",
            start_utc=start(),
            samples=[sample(start(), channel_id="beacon-2")],
        )


def test_rejects_sample_at_end_boundary() -> None:
    with pytest.raises(ValueError, match="inside"):
        MeasurementWindow.from_samples(
            channel_id="beacon-1",
            start_utc=start(),
            samples=[sample(start() + timedelta(seconds=10))],
        )


def test_rejects_non_utc_start() -> None:
    cet = timezone(timedelta(hours=1))
    with pytest.raises(ValueError, match="UTC"):
        MeasurementWindow(channel_id="beacon-1", start_utc=start().astimezone(cet))


def test_is_immutable() -> None:
    window = MeasurementWindow(channel_id="beacon-1", start_utc=start())
    with pytest.raises(FrozenInstanceError):
        window.channel_id = "other"  # type: ignore[misc]


def test_medians_ignore_missing_values() -> None:
    first = sample(start(), power=-70.0)
    second = sample(start() + timedelta(seconds=1), power=-60.0)
    window = MeasurementWindow.from_samples(
        channel_id="beacon-1", start_utc=start(), samples=[first, second]
    )
    assert window.median_baseband_power_db() == -65.0
    assert window.median_noise_density_db_hz() == -110.0


def test_freshness_age() -> None:
    window = MeasurementWindow.from_samples(
        channel_id="beacon-1",
        start_utc=start(),
        samples=[sample(start() + timedelta(seconds=9))],
    )
    assert window.freshness_age(start() + timedelta(seconds=12)) == timedelta(seconds=3)
