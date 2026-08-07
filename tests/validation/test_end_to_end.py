from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

from ka9q_beacon_monitor.api.server import BeaconDefinition, create_app as create_api_app
from ka9q_beacon_monitor.ka9q import BridgeCommand, Ka9qStatusBridgeDecoder
from ka9q_beacon_monitor.model import DemodMode, SampleQuality, StatusSample
from ka9q_beacon_monitor.processing import BeaconClassifier
from ka9q_beacon_monitor.repository import SQLiteRepository
from ka9q_beacon_monitor.runtime import BeaconPipelineConfig, BeaconRuntime, create_main_app
from ka9q_beacon_monitor.validation import replay_status_samples
from ka9q_beacon_monitor.web import WebUiConfig


class NoopVerifier:
    async def verify(self, observation, *, expected_callsign=None):
        return observation


def sample(channel: str, second: int, power: float) -> StatusSample:
    return StatusSample(
        timestamp_utc=datetime(2026, 8, 7, 8, 0, second, tzinfo=timezone.utc),
        channel_id=channel,
        frequency_hz=144_300_000.0,
        baseband_power_db=power,
        noise_density_db_hz=-120.0,
        gain_db=0.0,
        output_level_db=-10.0,
        headroom_db=6.0,
        pll_locked=None,
        demod_mode=DemodMode.LINEAR,
        sequence_number=second,
        sample_quality=SampleQuality.VALID,
    )


def runtime_for(repo, *, on_error=None):
    return BeaconRuntime(
        repository=repo,
        classifier=BeaconClassifier(),
        verifier=NoopVerifier(),
        beacon_pipelines=[BeaconPipelineConfig("B1", "sig", ("ref",), expected_callsign="TEST")],
        expected_status_rate_hz=0.1,
        on_error=on_error,
    )


@pytest.mark.asyncio
async def test_replay_reaches_persistence_aggregation_api_and_web(tmp_path: Path) -> None:
    repo = SQLiteRepository(tmp_path / "monitor.db")
    runtime = runtime_for(repo)
    report = await replay_status_samples(runtime, [sample("sig", 1, -90), sample("ref", 1, -102)])

    assert report.samples_submitted == 2
    assert report.observations_persisted == 1
    assert report.summaries_persisted == 1
    assert report.pipeline_errors == 0
    assert report.elapsed_seconds >= 0
    assert report.samples_per_second > 0

    app = create_main_app(
        runtime,
        beacons=[BeaconDefinition(beacon_id="B1", callsign="TEST", frequency_hz=144_300_000.0)],
        web_config=WebUiConfig(api_base_url="/api"),
    )
    with TestClient(app) as client:
        observations = client.get("/api/beacons/B1/observations")
        summaries = client.get("/api/beacons/B1/summaries")
        dashboard = client.get("/")
        assert observations.status_code == 200 and observations.json()["count"] == 1
        assert summaries.status_code == 200 and summaries.json()["count"] == 1
        assert dashboard.status_code == 200
        assert 'id="beacons"' in dashboard.text
        assert '/assets/app.js' in dashboard.text


@pytest.mark.asyncio
async def test_process_restart_reopens_persisted_data(tmp_path: Path) -> None:
    db = tmp_path / "monitor.db"
    repo = SQLiteRepository(db)
    runtime = runtime_for(repo)
    await replay_status_samples(runtime, [sample("sig", 1, -90), sample("ref", 1, -102)])
    repo.close()

    reopened = SQLiteRepository(db)
    api = create_api_app(reopened, beacons=[BeaconDefinition(beacon_id="B1")])
    with TestClient(api) as client:
        assert client.get("/beacons/B1/observations").json()["count"] == 1
        assert client.get("/beacons/B1/summaries").json()["count"] == 1
    reopened.close()


def test_production_status_adapter_boundary_can_feed_validated_sample(tmp_path: Path) -> None:
    bridge = tmp_path / "bridge.py"
    bridge.write_text(
        "import json,sys\n"
        "kind=sys.stdin.buffer.read().decode()\n"
        "p={'channel_id':kind,'frequency_hz':144300000,'baseband_power_db':-90 if kind=='sig' else -102,'noise_density_db_hz':-120,'demod_mode':'linear'}\n"
        "print(json.dumps(p))\n",
        encoding="utf-8",
    )
    decoder = Ka9qStatusBridgeDecoder(BridgeCommand((sys.executable, str(bridge))))
    received = datetime(2026, 8, 7, 8, 0, 1, tzinfo=timezone.utc)
    decoded = decoder.decode(b"sig", received_at_utc=received, source=("127.0.0.1", 5006))
    assert decoded.channel_id == "sig"
    assert decoded.timestamp_utc == received
    # This is synthetic boundary validation and is deliberately not Phase-0 field evidence.
