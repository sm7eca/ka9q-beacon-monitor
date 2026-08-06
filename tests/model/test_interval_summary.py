from datetime import datetime, timedelta, timezone

import pytest

from ka9q_beacon_monitor.model import (
    DetectionState,
    IntervalSummary,
    MeasurementQuality,
    MeasurementSource,
    Observation,
    SummaryState,
)

UTC = timezone.utc
START = datetime(2026, 8, 6, 12, 0, tzinfo=UTC)
END = START + timedelta(minutes=30)


def observation(index: int, state: DetectionState, snr: float | None, quality=MeasurementQuality.VALID, offset=None):
    window_start = START + timedelta(seconds=index * 10)
    return Observation(
        beacon_id="SK6VHF",
        window_start_utc=window_start,
        window_end_utc=window_start + timedelta(seconds=10),
        detection_state=state,
        measurement_source=MeasurementSource.STATUS_ONLY,
        measurement_quality=quality,
        classification_snr_db=snr,
        derived_local_snr_db=snr,
        frequency_offset_hz=offset,
        classification_reason="test",
    )


def test_empty_interval_is_no_data():
    summary = IntervalSummary.from_observations(
        beacon_id="SK6VHF", interval_start_utc=START, interval_end_utc=END, observations=[]
    )
    assert summary.expected_observation_count == 180
    assert summary.final_state == SummaryState.NO_DATA
    assert summary.quality == MeasurementQuality.INVALID


def test_strong_summary():
    items = [observation(i, DetectionState.VERIFIED_BEACON, 18.0, MeasurementQuality.VERIFIED) for i in range(180)]
    summary = IntervalSummary.from_observations(
        beacon_id="SK6VHF", interval_start_utc=START, interval_end_utc=END, observations=items
    )
    assert summary.final_state == SummaryState.STRONG
    assert summary.quality == MeasurementQuality.VERIFIED
    assert summary.audible_percent == 100.0
    assert summary.data_coverage_percent == 100.0


def test_audible_summary():
    items = [observation(i, DetectionState.PROBABLE_BEACON, 8.0) for i in range(180)]
    summary = IntervalSummary.from_observations(
        beacon_id="SK6VHF", interval_start_utc=START, interval_end_utc=END, observations=items
    )
    assert summary.final_state == SummaryState.AUDIBLE


def test_weak_summary():
    items = [observation(i, DetectionState.PROBABLE_BEACON, 4.0) for i in range(100)]
    items.extend(observation(100 + i, DetectionState.NO_SIGNAL, 0.0) for i in range(80))
    summary = IntervalSummary.from_observations(
        beacon_id="SK6VHF", interval_start_utc=START, interval_end_utc=END, observations=items
    )
    assert summary.final_state == SummaryState.WEAK


def test_interference_dominates():
    items = [observation(i, DetectionState.INTERFERENCE, 10.0) for i in range(100)]
    items.extend(observation(100 + i, DetectionState.NO_SIGNAL, 0.0) for i in range(80))
    summary = IntervalSummary.from_observations(
        beacon_id="SK6VHF", interval_start_utc=START, interval_end_utc=END, observations=items
    )
    assert summary.final_state == SummaryState.INTERFERED


def test_low_coverage_is_no_data():
    items = [observation(i, DetectionState.PROBABLE_BEACON, 12.0) for i in range(20)]
    summary = IntervalSummary.from_observations(
        beacon_id="SK6VHF", interval_start_utc=START, interval_end_utc=END, observations=items
    )
    assert summary.data_coverage_percent < 20.0
    assert summary.final_state == SummaryState.NO_DATA


def test_median_and_maximum_snr_and_offset():
    items = [
        observation(0, DetectionState.PROBABLE_BEACON, 4.0, offset=-2.0),
        observation(1, DetectionState.PROBABLE_BEACON, 8.0, offset=1.0),
        observation(2, DetectionState.PROBABLE_BEACON, 12.0, offset=4.0),
    ]
    summary = IntervalSummary.from_observations(
        beacon_id="SK6VHF",
        interval_start_utc=START,
        interval_end_utc=START + timedelta(seconds=30),
        observations=items,
    )
    assert summary.median_classification_snr_db == 8.0
    assert summary.maximum_classification_snr_db == 12.0
    assert summary.median_frequency_offset_hz == 1.0


def test_other_beacons_and_out_of_interval_observations_are_ignored():
    valid = observation(0, DetectionState.PROBABLE_BEACON, 8.0)
    other = Observation(
        beacon_id="OZ7IGY",
        window_start_utc=START,
        window_end_utc=START + timedelta(seconds=10),
        detection_state=DetectionState.PROBABLE_BEACON,
        measurement_source=MeasurementSource.STATUS_ONLY,
        measurement_quality=MeasurementQuality.VALID,
        classification_snr_db=20.0,
    )
    late = observation(180, DetectionState.PROBABLE_BEACON, 20.0)
    summary = IntervalSummary.from_observations(
        beacon_id="SK6VHF",
        interval_start_utc=START,
        interval_end_utc=START + timedelta(seconds=10),
        observations=[valid, other, late],
    )
    assert summary.observation_count == 1


def test_summary_is_immutable():
    summary = IntervalSummary.from_observations(
        beacon_id="SK6VHF", interval_start_utc=START, interval_end_utc=END, observations=[]
    )
    with pytest.raises(Exception):
        summary.final_state = SummaryState.STRONG


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
            quality=MeasurementQuality.INVALID,
        )
