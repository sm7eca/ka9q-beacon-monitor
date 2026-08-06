from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from ka9q_beacon_monitor.model.status_sample import (
    DemodMode,
    SampleQuality,
    StatusSample,
)


def make_sample(**overrides: object) -> StatusSample:
    values = {
        "timestamp_utc": datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc),
        "channel_id": "beacon-sk6vhf-signal",
        "frequency_hz": 144_412_000.0,
        "baseband_power_db": -91.5,
        "noise_density_db_hz": -122.0,
        "gain_db": 12.0,
        "output_level_db": -18.0,
        "headroom_db": 14.0,
        "demod_mode": DemodMode.LINEAR,
        "pll_locked": None,
        "sequence_number": 42,
        "sample_quality": SampleQuality.VALID,
    }
    values.update(overrides)
    return StatusSample(**values)  # type: ignore[arg-type]


def test_valid_sample_is_constructed() -> None:
    sample = make_sample()
    assert sample.channel_id == "beacon-sk6vhf-signal"
    assert sample.sample_quality is SampleQuality.VALID


def test_sample_is_immutable() -> None:
    sample = make_sample()
    with pytest.raises(FrozenInstanceError):
        sample.channel_id = "changed"  # type: ignore[misc]


def test_timestamp_must_be_timezone_aware_utc() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        make_sample(timestamp_utc=datetime(2026, 8, 6, 12, 0))


def test_frequency_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive finite"):
        make_sample(frequency_hz=0.0)


def test_non_finite_measurement_is_rejected() -> None:
    with pytest.raises(ValueError, match="baseband_power_db"):
        make_sample(baseband_power_db=float("nan"))


def test_valid_sample_requires_power_and_noise() -> None:
    with pytest.raises(ValueError, match="VALID samples require"):
        make_sample(baseband_power_db=None)


def test_partial_sample_may_omit_measurements() -> None:
    sample = make_sample(
        baseband_power_db=None,
        noise_density_db_hz=None,
        sample_quality=SampleQuality.PARTIAL,
    )
    assert sample.baseband_power_db is None


def test_invalid_sample_must_not_expose_measurements() -> None:
    with pytest.raises(ValueError, match="INVALID samples"):
        make_sample(sample_quality=SampleQuality.INVALID)


def test_invalid_sample_without_measurements_is_allowed() -> None:
    sample = make_sample(
        baseband_power_db=None,
        noise_density_db_hz=None,
        gain_db=None,
        output_level_db=None,
        headroom_db=None,
        sample_quality=SampleQuality.INVALID,
    )
    assert sample.sample_quality is SampleQuality.INVALID
