from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone

import pytest

from ka9q_beacon_monitor.model.observation import (
    DetectionState,
    MeasurementSource,
    Observation,
    QualityLevel,
)

START = datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc)
END = START + timedelta(seconds=10)


def make_observation(**overrides):
    values = dict(
        beacon_id="SK6VHF",
        window_start_utc=START,
        window_end_utc=END,
        detection_state=DetectionState.PROBABLE_BEACON,
        measurement_source=MeasurementSource.STATUS_ONLY,
        derived_local_snr_db=7.5,
        verification_snr_db=None,
        ka9q_reported_snr_db=None,
        measurement_quality=QualityLevel.NOMINAL,
        verification_quality=QualityLevel.INVALID,
        identification_quality=QualityLevel.DEGRADED,
        verification_accepted=False,
        frequency_offset_hz=1.2,
        reason_code="stable_status_signal",
    )
    values.update(overrides)
    return Observation(**values)


def test_status_only_uses_derived_snr():
    observation = make_observation(ka9q_reported_snr_db=99.0)
    assert observation.classification_snr_db == 7.5


def test_accepted_verification_uses_verification_snr():
    observation = make_observation(
        detection_state=DetectionState.VERIFIED_BEACON,
        measurement_source=MeasurementSource.VERIFIED_IQ,
        verification_snr_db=10.25,
        verification_quality=QualityLevel.HIGH,
        verification_accepted=True,
    )
    assert observation.classification_snr_db == 10.25


def test_ka9q_reported_snr_is_diagnostic_only():
    observation = make_observation(ka9q_reported_snr_db=42.0)
    assert observation.classification_snr_db != observation.ka9q_reported_snr_db


def test_no_data_has_no_classification_snr():
    observation = make_observation(
        detection_state=DetectionState.NO_DATA,
        derived_local_snr_db=None,
        measurement_quality=QualityLevel.INVALID,
        reason_code="missing_reference_samples",
    )
    assert observation.classification_snr_db is None


def test_no_data_rejects_non_invalid_measurement_quality():
    with pytest.raises(ValueError, match="INVALID measurement_quality"):
        make_observation(
            detection_state=DetectionState.NO_DATA,
            derived_local_snr_db=None,
            measurement_quality=QualityLevel.DEGRADED,
        )


def test_verified_state_requires_accepted_verification():
    with pytest.raises(ValueError, match="VERIFIED_BEACON"):
        make_observation(detection_state=DetectionState.VERIFIED_BEACON)


def test_accepted_verification_requires_snr():
    with pytest.raises(ValueError, match="verification_snr_db"):
        make_observation(
            measurement_source=MeasurementSource.VERIFIED_PCM,
            verification_accepted=True,
        )


def test_accepted_verification_rejects_status_only_source():
    with pytest.raises(ValueError, match="STATUS_ONLY"):
        make_observation(
            verification_snr_db=8.0,
            verification_accepted=True,
        )


def test_timestamps_must_be_utc():
    with pytest.raises(ValueError, match="UTC"):
        make_observation(
            window_start_utc=START.astimezone(timezone(timedelta(hours=2)))
        )


def test_non_finite_values_are_rejected():
    with pytest.raises(ValueError, match="finite"):
        make_observation(derived_local_snr_db=float("nan"))


def test_observation_is_immutable():
    observation = make_observation()
    with pytest.raises(FrozenInstanceError):
        observation.beacon_id = "OTHER"  # type: ignore[misc]
