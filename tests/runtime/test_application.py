from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from ka9q_beacon_monitor.api.server import BeaconDefinition
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
from ka9q_beacon_monitor.runtime import BeaconPipelineConfig, BeaconRuntime, create_main_app
from ka9q_beacon_monitor.web.app import WebUiConfig


class MemoryRepository:
    schema_version = 1

    def __init__(self) -> None:
        self.observations: list[Observation] = []
        self.summaries: list[object] = []
        self.closed = False

    def save_observation(self, observation: Observation) -> None:
        self.observations.append(observation)

    def save_interval_summary(self, summary: object) -> None:
        self.summaries.append(summary)

    def counts(self) -> tuple[int, int]:
        return len(self.observations), len(self.summaries)

    def list_observations(self, beacon_id: str, *, limit: int = 100):
        return []

    def get_observation(self, beacon_id: str, start):
        return None

    def list_interval_summaries(self, beacon_id: str, *, limit: int = 100):
        return []

    def get_interval_summary(self, beacon_id: str, start):
        return None

    def close(self) -> None:
        self.closed = True


class NoopVerifier:
    async def verify(self, observation: Observation, *, expected_callsign: str | None = None) -> Observation:
        return observation


@dataclass
class FakeReceiver:
    started: int = 0
    closed: int = 0

    async def start(self) -> None:
        self.started += 1

    async def close(self) -> None:
        self.closed += 1


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
async def test_runtime_joins_windows_classifies_and_persists() -> None:
    repo = MemoryRepository()
    runtime = BeaconRuntime(
        repository=repo,  # type: ignore[arg-type]
        classifier=BeaconClassifier(),
        verifier=NoopVerifier(),  # type: ignore[arg-type]
        beacon_pipelines=[BeaconPipelineConfig("B1", "sig", ("ref",))],
        expected_status_rate_hz=0.1,
    )

    await runtime.ingest_sample(sample("sig", 1, -90.0))
    await runtime.ingest_sample(sample("ref", 1, -102.0))
    await runtime.advance_time(datetime(2026, 8, 6, 12, 0, 10, tzinfo=timezone.utc))

    assert len(repo.observations) == 1
    assert repo.observations[0].beacon_id == "B1"
    assert repo.observations[0].detection_state in {
        DetectionState.SIGNAL_PRESENT,
        DetectionState.PROBABLE_BEACON,
    }
    assert runtime.counters.classifications_completed == 1
    assert runtime.counters.observations_persisted == 1


@pytest.mark.asyncio
async def test_start_and_close_are_ordered_and_idempotent() -> None:
    repo = MemoryRepository()
    receiver = FakeReceiver()
    runtime = BeaconRuntime(
        repository=repo,  # type: ignore[arg-type]
        classifier=BeaconClassifier(),
        verifier=NoopVerifier(),  # type: ignore[arg-type]
        beacon_pipelines=[BeaconPipelineConfig("B1", "sig", ("ref",))],
        receiver=receiver,
    )

    await runtime.start()
    assert runtime.is_started
    assert receiver.started == 1
    with pytest.raises(RuntimeError):
        await runtime.start()
    await runtime.close()
    await runtime.close()
    assert receiver.closed == 1
    assert repo.closed
    assert not runtime.is_started


def test_main_app_mounts_api_and_web_and_runs_lifecycle() -> None:
    repo = MemoryRepository()
    receiver = FakeReceiver()
    runtime = BeaconRuntime(
        repository=repo,  # type: ignore[arg-type]
        classifier=BeaconClassifier(),
        verifier=NoopVerifier(),  # type: ignore[arg-type]
        beacon_pipelines=[BeaconPipelineConfig("B1", "sig", ("ref",))],
        receiver=receiver,
    )
    app = create_main_app(
        runtime,
        beacons=[BeaconDefinition(beacon_id="B1", callsign="TEST")],
        web_config=WebUiConfig(api_base_url="/api", refresh_seconds=30),
    )

    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/").status_code == 200
        assert receiver.started == 1
    assert receiver.closed == 1
