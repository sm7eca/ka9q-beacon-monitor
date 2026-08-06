from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ka9q_beacon_monitor.model import (
    DemodMode,
    DetectionState,
    MeasurementWindow,
    QualityLevel,
    SampleQuality,
    StatusSample,
)
from ka9q_beacon_monitor.processing import (
    BeaconClassifier,
    ClassificationInput,
    ClassifierConfig,
)

UTC = timezone.utc
START = datetime(2026, 8, 6, 12, 0, 0, tzinfo=UTC)


def window(channel: str, power_db: float, *, count: int = 20) -> MeasurementWindow:
    samples = tuple(
        StatusSample(
            timestamp_utc=START + timedelta(milliseconds=500 * index),
            channel_id=channel,
            frequency_hz=144_300_000.0,
            baseband_power_db=power_db,
            noise_density_db_hz=-120.0,
            gain_db=12.0,
            output_level_db=-18.0,
            headroom_db=6.0,
            demod_mode=DemodMode.LINEAR,
            pll_locked=None,
            sequence_number=index,
            sample_quality=SampleQuality.VALID,
        )
        for index in range(count)
    )
    return MeasurementWindow(channel_id=channel, start_utc=START, samples=samples)


def classify(
    signal_power: float,
    reference_powers: tuple[float, ...] = (-100.0, -100.0),
    *,
    previous_state: DetectionState | None = None,
):
    return BeaconClassifier().classify(
        ClassificationInput.from_windows(
            beacon_id="SK4MPI",
            signal_window=window("signal", signal_power),
            reference_windows=[
                window(f"ref-{index}", value)
                for index, value in enumerate(reference_powers)
            ],
            previous_state=previous_state,
        )
    )


def test_probable_beacon_at_high_local_snr() -> None:
    observation = classify(-90.0)
    assert observation.detection_state is DetectionState.PROBABLE_BEACON
    assert observation.derived_local_snr_db == pytest.approx(10.0)
    assert observation.measurement_quality is QualityLevel.HIGH
    assert observation.reason_code == "snr_above_probable_threshold"


def test_signal_present_between_thresholds() -> None:
    observation = classify(-93.0)
    assert observation.detection_state is DetectionState.SIGNAL_PRESENT
    assert observation.classification_snr_db == pytest.approx(7.0)


def test_no_signal_below_threshold() -> None:
    observation = classify(-95.0)
    assert observation.detection_state is DetectionState.NO_SIGNAL
    assert observation.classification_snr_db == pytest.approx(5.0)


def test_probable_state_uses_exit_hysteresis() -> None:
    observation = classify(-92.0, previous_state=DetectionState.PROBABLE_BEACON)
    assert observation.detection_state is DetectionState.PROBABLE_BEACON


def test_signal_state_uses_exit_hysteresis() -> None:
    observation = classify(-95.0, previous_state=DetectionState.SIGNAL_PRESENT)
    assert observation.detection_state is DetectionState.SIGNAL_PRESENT


def test_missing_reference_windows_returns_no_data() -> None:
    observation = classify(-90.0, ())
    assert observation.detection_state is DetectionState.NO_DATA
    assert observation.measurement_quality is QualityLevel.INVALID
    assert observation.classification_snr_db is None


def test_low_signal_coverage_returns_no_data() -> None:
    input_data = ClassificationInput.from_windows(
        beacon_id="SK4MPI",
        signal_window=window("signal", -90.0, count=5),
        reference_windows=[window("ref-a", -100.0), window("ref-b", -100.0)],
    )
    observation = BeaconClassifier().classify(input_data)
    assert observation.detection_state is DetectionState.NO_DATA


def test_reference_disagreement_is_interference() -> None:
    observation = classify(-90.0, (-104.0, -96.0))
    assert observation.detection_state is DetectionState.INTERFERENCE
    assert observation.measurement_quality is QualityLevel.DEGRADED
    assert observation.reason_code == "reference_channels_disagree"


def test_one_reference_can_produce_nominal_quality() -> None:
    observation = classify(-92.0, (-100.0,))
    assert observation.measurement_quality is QualityLevel.NOMINAL


def test_classifier_never_uses_ka9q_reported_snr_for_classification() -> None:
    observation = classify(-90.0)
    assert observation.ka9q_reported_snr_db is None
    assert observation.classification_snr_db == observation.derived_local_snr_db


def test_input_rejects_unsynchronized_windows() -> None:
    shifted = MeasurementWindow(
        channel_id="ref",
        start_utc=START + timedelta(seconds=10),
        samples=(),
    )
    with pytest.raises(ValueError):
        ClassificationInput(
            beacon_id="SK4MPI",
            signal_window=window("signal", -90.0),
            reference_windows=(shifted,),
        )


def test_config_rejects_invalid_threshold_order() -> None:
    with pytest.raises(ValueError):
        ClassifierConfig(
            signal_present_enter_db=6.0,
            probable_beacon_enter_db=5.0,
        )


def test_classifier_is_deterministic_for_same_input() -> None:
    input_data = ClassificationInput.from_windows(
        beacon_id="SK4MPI",
        signal_window=window("signal", -91.0),
        reference_windows=[window("ref-a", -100.0), window("ref-b", -100.0)],
    )
    classifier = BeaconClassifier()
    assert classifier.classify(input_data) == classifier.classify(input_data)
