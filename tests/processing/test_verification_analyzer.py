from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ka9q_beacon_monitor.model import (
    DetectionState,
    MeasurementSource,
    Observation,
    QualityLevel,
)
from ka9q_beacon_monitor.processing.verification_analyzer import (
    VerificationAnalyzer,
    VerificationEvidence,
    VerificationPolicy,
)


START = datetime(2026, 1, 1, tzinfo=timezone.utc)
END = START + timedelta(seconds=10)


def observation(state: DetectionState = DetectionState.PROBABLE_BEACON) -> Observation:
    return Observation(
        beacon_id="SK6VHF",
        window_start_utc=START,
        window_end_utc=END,
        detection_state=state,
        measurement_source=MeasurementSource.STATUS_ONLY,
        derived_local_snr_db=10.0 if state is not DetectionState.NO_DATA else None,
        verification_snr_db=None,
        ka9q_reported_snr_db=None,
        measurement_quality=(
            QualityLevel.INVALID if state is DetectionState.NO_DATA else QualityLevel.HIGH
        ),
        verification_quality=QualityLevel.INVALID,
        identification_quality=QualityLevel.INVALID,
        verification_accepted=False,
        reason_code="status_classification",
    )


def evidence(**overrides: object) -> VerificationEvidence:
    values: dict[str, object] = {
        "beacon_id": "SK6VHF",
        "window_start_utc": START,
        "window_end_utc": END,
        "measurement_source": MeasurementSource.VERIFIED_CW,
        "cw_detected": True,
        "verification_snr_db": 8.0,
        "frequency_offset_hz": 2.5,
        "verification_quality": QualityLevel.HIGH,
        "identification_quality": QualityLevel.NOMINAL,
        "identified_callsign": None,
    }
    values.update(overrides)
    return VerificationEvidence(**values)  # type: ignore[arg-type]


class Backend:
    def __init__(self, result: VerificationEvidence | Exception) -> None:
        self.result = result
        self.calls = 0

    async def analyze(self, request):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.mark.asyncio
async def test_accepted_cw_evidence_upgrades_observation() -> None:
    analyzer = VerificationAnalyzer(Backend(evidence()))
    result = await analyzer.verify(observation())
    assert result.detection_state is DetectionState.VERIFIED_BEACON
    assert result.measurement_source is MeasurementSource.VERIFIED_CW
    assert result.verification_accepted is True
    assert result.classification_snr_db == 8.0


@pytest.mark.asyncio
async def test_non_probable_observation_is_returned_without_backend_call() -> None:
    backend = Backend(evidence())
    item = observation(DetectionState.SIGNAL_PRESENT)
    result = await VerificationAnalyzer(backend).verify(item)
    assert result is item
    assert backend.calls == 0


@pytest.mark.asyncio
async def test_backend_failure_is_isolated() -> None:
    result = await VerificationAnalyzer(Backend(RuntimeError("boom"))).verify(observation())
    assert result.detection_state is DetectionState.PROBABLE_BEACON
    assert result.verification_accepted is False
    assert result.reason_code == "verification_backend_error"


@pytest.mark.asyncio
async def test_beacon_mismatch_is_rejected() -> None:
    result = await VerificationAnalyzer(
        Backend(evidence(beacon_id="OTHER"))
    ).verify(observation())
    assert result.reason_code == "verification_beacon_mismatch"


@pytest.mark.asyncio
async def test_window_mismatch_is_rejected() -> None:
    result = await VerificationAnalyzer(
        Backend(evidence(window_end_utc=END + timedelta(seconds=10)))
    ).verify(observation())
    assert result.reason_code == "verification_window_mismatch"


@pytest.mark.asyncio
async def test_cw_must_be_detected() -> None:
    result = await VerificationAnalyzer(
        Backend(evidence(cw_detected=False))
    ).verify(observation())
    assert result.reason_code == "cw_not_detected"


@pytest.mark.asyncio
async def test_snr_must_meet_policy_threshold() -> None:
    analyzer = VerificationAnalyzer(
        Backend(evidence(verification_snr_db=2.9)),
        VerificationPolicy(minimum_verification_snr_db=3.0),
    )
    result = await analyzer.verify(observation())
    assert result.reason_code == "verification_snr_below_threshold"


@pytest.mark.asyncio
async def test_frequency_offset_must_be_within_policy() -> None:
    analyzer = VerificationAnalyzer(
        Backend(evidence(frequency_offset_hz=20.1)),
        VerificationPolicy(maximum_abs_frequency_offset_hz=20.0),
    )
    result = await analyzer.verify(observation())
    assert result.reason_code == "frequency_offset_out_of_range"


@pytest.mark.asyncio
async def test_degraded_evidence_is_not_accepted() -> None:
    result = await VerificationAnalyzer(
        Backend(evidence(verification_quality=QualityLevel.DEGRADED))
    ).verify(observation())
    assert result.reason_code == "verification_quality_insufficient"


@pytest.mark.asyncio
async def test_morse_requires_callsign() -> None:
    result = await VerificationAnalyzer(
        Backend(evidence(measurement_source=MeasurementSource.VERIFIED_MORSE))
    ).verify(observation(), expected_callsign="SK6VHF")
    assert result.reason_code == "morse_callsign_missing"


@pytest.mark.asyncio
async def test_morse_callsign_is_normalized_and_matched() -> None:
    result = await VerificationAnalyzer(
        Backend(
            evidence(
                measurement_source=MeasurementSource.VERIFIED_MORSE,
                identified_callsign=" sk6 vhf ",
                identification_quality=QualityLevel.HIGH,
            )
        )
    ).verify(observation(), expected_callsign="SK6VHF")
    assert result.detection_state is DetectionState.VERIFIED_BEACON
    assert result.identified_callsign == " sk6 vhf "


@pytest.mark.asyncio
async def test_wrong_callsign_is_rejected() -> None:
    result = await VerificationAnalyzer(
        Backend(
            evidence(
                measurement_source=MeasurementSource.VERIFIED_MORSE,
                identified_callsign="SK7VHF",
            )
        )
    ).verify(observation(), expected_callsign="SK6VHF")
    assert result.reason_code == "callsign_mismatch"


def test_evidence_rejects_status_only_source() -> None:
    with pytest.raises(ValueError, match="STATUS_ONLY"):
        evidence(measurement_source=MeasurementSource.STATUS_ONLY)


def test_policy_rejects_negative_frequency_limit() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        VerificationPolicy(maximum_abs_frequency_offset_hz=-1)
