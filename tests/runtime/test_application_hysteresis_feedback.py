from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from ka9q_beacon_monitor.model import (
    DemodMode,
    DetectionState,
    MeasurementSource,
    Observation,
    QualityLevel,
    SampleQuality,
    StatusSample,
)
from ka9q_beacon_monitor.processing import BeaconClassifier
from ka9q_beacon_monitor.runtime import BeaconPipelineConfig, BeaconRuntime


class MemoryRepository:
    schema_version = 1

    def __init__(self) -> None:
        self.observations: list[Observation] = []
        self.summaries: list[object] = []

    def save_observation(self, observation: Observation) -> None:
        self.observations.append(observation)

    def save_interval_summary(self, summary: object) -> None:
        self.summaries.append(summary)

    def close(self) -> None:
        return None


class VerifyFirstObservation:
    def __init__(self) -> None:
        self.calls = 0

    async def verify(
        self,
        observation: Observation,
        *,
        expected_callsign: str | None = None,
    ) -> Observation:
        self.calls += 1
        if self.calls != 1:
            return observation
        return replace(
            observation,
            detection_state=DetectionState.VERIFIED_BEACON,
            measurement_source=MeasurementSource.VERIFIED_CW,
            verification_snr_db=observation.derived_local_snr_db,
            verification_quality=QualityLevel.NOMINAL,
            identification_quality=QualityLevel.NOMINAL,
            verification_accepted=True,
            reason_code="verification_accepted",
        )


def sample(channel_id: str, second: int, power: float) -> StatusSample:
    return StatusSample(
        timestamp_utc=datetime(2026, 8, 6, 12, 0, second, tzinfo=timezone.utc),
        channel_id=channel_id,
        frequency_hz=144_300_000.0,
        baseband_power_db=power,
        noise_density_db_hz=-120.0,
        gain_db=0.0,
        output_level_db=-10.0,
        headroom_db=6.0,
        pll_locked=None,
        demod_mode=DemodMode.LINEAR,
        sample_quality=SampleQuality.VALID,
        sequence_number=second,
    )


@pytest.mark.asyncio
async def test_verified_observation_preserves_classifier_hysteresis_feedback() -> None:
    repository = MemoryRepository()
    runtime = BeaconRuntime(
        repository=repository,  # type: ignore[arg-type]
        classifier=BeaconClassifier(),
        verifier=VerifyFirstObservation(),  # type: ignore[arg-type]
        beacon_pipelines=[BeaconPipelineConfig("B1", "sig", ("ref",))],
        expected_status_rate_hz=0.1,
    )

    # First window: 10 dB, so classifier emits PROBABLE_BEACON and verifier
    # upgrades the persisted observation to VERIFIED_BEACON.
    await runtime.ingest_sample(sample("sig", 1, -90.0))
    await runtime.ingest_sample(sample("ref", 1, -100.0))
    await runtime.advance_time(datetime(2026, 8, 6, 12, 0, 10, tzinfo=timezone.utc))

    # Second window: 8 dB lies below probable-enter (9.0) but above
    # probable-exit (7.5). It remains PROBABLE_BEACON only when the raw
    # classifier state from the first cycle is retained for hysteresis.
    await runtime.ingest_sample(sample("sig", 11, -92.0))
    await runtime.ingest_sample(sample("ref", 11, -100.0))
    await runtime.advance_time(datetime(2026, 8, 6, 12, 0, 20, tzinfo=timezone.utc))

    assert [item.detection_state for item in repository.observations] == [
        DetectionState.VERIFIED_BEACON,
        DetectionState.PROBABLE_BEACON,
    ]
