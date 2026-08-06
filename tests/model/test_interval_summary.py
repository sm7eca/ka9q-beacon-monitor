from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from ka9q_beacon_monitor.model import (
    DetectionState,
    IntervalSummary,
    MeasurementSource,
    Observation,
    QualityLevel,
    SummaryState,
)

UTC = timezone.utc
START = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)
END = START + timedelta(minutes=30)


def observation(index: int, state: DetectionState, snr: float | None, offset=None) -> Observation:
    window_start = START + timedelta(seconds=index * 10)
    verified = state is DetectionState.VERIFIED_BEACON
    return Observation(
        beacon_id="SK6VHF",
        window_start_utc=window_start,
        window_end_utc=window_start + timedelta(seconds=10),
        detection_state=state,
        measurement_source=(MeasurementSource.VERIFIED_IQ if verified else MeasurementSource.STATUS_ONLY),
        derived_local_snr_db=None if state is DetectionState.NO_DATA else snr,
        verification_snr_db=snr if verified else None,
        ka9q_reported_snr_db=None,
        measurement_quality=QualityLevel.INVALID if state is DetectionState.NO_DATA else QualityLevel.NOMINAL,
        verification_quality=QualityLevel.HIGH if verified else QualityLevel.INVALID,
        identification_quality=QualityLevel.HIGH if verified else QualityLevel.DEGRADED,
        verification_accepted=verified,
        frequency_offset_hz=offset,
        reason_code="test",
    )


def summarize(items, *, end=END):
    return IntervalSummary.from_observations(
        beacon_id="SK6VHF", interval_start_utc=START, interval_end_utc=end, observations=items
    )


def test_empty_interval_is_no_data():
    summary = summarize([])
    assert summary.expected_observation_count == 180
    assert summary.final_state is SummaryState.NO_DATA
    assert summary.quality is QualityLevel.INVALID


def test_strong_summary_and_high_quality():
    summary = summarize([observation(i, DetectionState.VERIFIED_BEACON, 18.0) for i in range(180)])
    assert summary.final_state is SummaryState.STRONG
    assert summary.quality is QualityLevel.HIGH
    assert summary.audible_percent == 100.0
    assert summary.data_coverage_percent == 100.0


def test_audible_summary_and_nominal_quality():
    summary = summarize([observation(i, DetectionState.PROBABLE_BEACON, 8.0) for i in range(180)])
    assert summary.final_state is SummaryState.AUDIBLE
    assert summary.quality is QualityLevel.NOMINAL


def test_weak_summary():
    items = [observation(i, DetectionState.PROBABLE_BEACON, 4.0) for i in range(100)]
    items += [observation(100 + i, DetectionState.NO_SIGNAL, 0.0) for i in range(80)]
    assert summarize(items).final_state is SummaryState.WEAK


def test_interference_dominates_when_coverage_is_sufficient():
    items = [observation(i, DetectionState.INTERFERENCE, 10.0) for i in range(100)]
    items += [observation(100 + i, DetectionState.NO_SIGNAL, 0.0) for i in range(80)]
    assert summarize(items).final_state is SummaryState.INTERFERED


def test_low_coverage_wins_before_interference():
    items = [observation(i, DetectionState.INTERFERENCE, 10.0) for i in range(20)]
    summary = summarize(items)
    assert summary.data_coverage_percent < 20.0
    assert summary.final_state is SummaryState.NO_DATA


def test_median_and_maximum_snr_and_offset():
    items = [
        observation(0, DetectionState.PROBABLE_BEACON, 4.0, -2.0),
        observation(1, DetectionState.PROBABLE_BEACON, 8.0, 1.0),
        observation(2, DetectionState.PROBABLE_BEACON, 12.0, 4.0),
    ]
    summary = summarize(items, end=START + timedelta(seconds=30))
    assert summary.median_classification_snr_db == 8.0
    assert summary.maximum_classification_snr_db == 12.0
    assert summary.median_frequency_offset_hz == 1.0


def test_other_beacons_and_out_of_interval_are_ignored():
    valid = observation(0, DetectionState.PROBABLE_BEACON, 8.0)
    other = Observation(
        beacon_id="OZ7IGY",
        window_start_utc=START,
        window_end_utc=START + timedelta(seconds=10),
        detection_state=DetectionState.PROBABLE_BEACON,
        measurement_source=MeasurementSource.STATUS_ONLY,
        derived_local_snr_db=20.0,
        verification_snr_db=None,
        ka9q_reported_snr_db=None,
        measurement_quality=QualityLevel.NOMINAL,
        verification_quality=QualityLevel.INVALID,
        identification_quality=QualityLevel.DEGRADED,
        verification_accepted=False,
        reason_code="test",
    )
    late = observation(180, DetectionState.PROBABLE_BEACON, 20.0)
    summary = summarize([valid, other, late], end=START + timedelta(seconds=10))
    assert summary.observation_count == 1


def test_summary_is_immutable():
    summary = summarize([])
    with pytest.raises(FrozenInstanceError):
        summary.final_state = SummaryState.STRONG  # type: ignore[misc]


def test_invalid_counts_are_rejected():
    with pytest.raises(ValueError):
        IntervalSummary(
            beacon_id="SK6VHF",
            interval_start_utc=START,
            interval_end_utc=END,
            expected_observation_count=180,
            observation_count=1,
            valid_observation_count=2,
            verified_observation_count=0,
            audible_observation_count=0,
            data_coverage_percent=1.0,
            audible_percent=0.0,
            median_classification_snr_db=None,
            maximum_classification_snr_db=None,
            median_frequency_offset_hz=None,
            final_state=SummaryState.NO_DATA,
            quality=QualityLevel.INVALID,
        )


def test_summary_state_values_use_lowercase_convention():
    assert SummaryState.NO_DATA.value == "no_data"
    assert SummaryState.STRONG.value == "strong"
