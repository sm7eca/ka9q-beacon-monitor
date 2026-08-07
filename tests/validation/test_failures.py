from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ka9q_beacon_monitor.api.server import BeaconDefinition, create_app as create_api_app
from ka9q_beacon_monitor.ka9q import Ka9qStatusReceiver, MulticastEndpoint, StatusDecodeError
from ka9q_beacon_monitor.model import DemodMode, SampleQuality, StatusSample
from ka9q_beacon_monitor.observability import create_operations_router
from ka9q_beacon_monitor.repository import SQLiteRepository
from ka9q_beacon_monitor.validation import replay_status_samples

from .test_end_to_end import runtime_for, sample


class RejectOnceDecoder:
    def __init__(self):
        self.reject = True

    def decode(self, datagram, *, received_at_utc, source):
        if self.reject:
            self.reject = False
            raise StatusDecodeError("simulated radiod interruption")
        return sample("sig", 1, -90)


def test_malformed_or_interrupted_input_is_isolated_and_later_input_recovers() -> None:
    published = []
    decoder = RejectOnceDecoder()
    receiver = Ka9qStatusReceiver(MulticastEndpoint("239.1.2.3", 5006), decoder, published.append)
    import asyncio
    assert asyncio.run(receiver.process_datagram(b"first")) is None
    assert asyncio.run(receiver.process_datagram(b"second")) is not None
    assert receiver.counters.datagrams_rejected == 1
    assert receiver.counters.samples_published == 1
    assert len(published) == 1


class RestartDecoder:
    def decode(self, datagram, *, received_at_utc, source):
        channel_id = datagram.decode("ascii")
        power = -90.0 if channel_id == "sig" else -102.0
        return StatusSample(
            timestamp_utc=received_at_utc,
            channel_id=channel_id,
            frequency_hz=144_300_000.0,
            baseband_power_db=power,
            noise_density_db_hz=-120.0,
            gain_db=0.0,
            output_level_db=-10.0,
            headroom_db=6.0,
            pll_locked=None,
            demod_mode=DemodMode.LINEAR,
            sequence_number=int(received_at_utc.timestamp()),
            sample_quality=SampleQuality.VALID,
        )


@pytest.mark.asyncio
async def test_network_interruption_receiver_restart_preserves_data_and_resumes(tmp_path: Path) -> None:
    repo = SQLiteRepository(tmp_path / "monitor.db")
    runtime = runtime_for(repo)
    endpoint = MulticastEndpoint("239.1.2.3", 5006)
    decoder = RestartDecoder()

    receiver_before = Ka9qStatusReceiver(endpoint, decoder, runtime.ingest_sample)
    first_at = datetime(2026, 8, 7, 8, 0, 1, tzinfo=timezone.utc)
    assert await receiver_before.process_datagram(b"sig", received_at_utc=first_at) is not None
    assert await receiver_before.process_datagram(b"ref", received_at_utc=first_at) is not None
    await runtime.measurement_builder.flush()
    await runtime.aggregator.flush()
    assert repo.counts() == (1, 1)

    # Simulate loss of the radiod/multicast connection by disposing the receiver.
    await receiver_before.close()

    # Persisted state remains queryable while the transport is absent.
    api = create_api_app(repo, beacons=[BeaconDefinition(beacon_id="B1")])
    with TestClient(api) as client:
        assert client.get("/beacons/B1/observations").json()["count"] == 1
        assert client.get("/beacons/B1/summaries").json()["count"] == 1

    # Recreate the receiver as a restarted radiod/multicast session and resume.
    receiver_after = Ka9qStatusReceiver(endpoint, decoder, runtime.ingest_sample)
    second_at = first_at + timedelta(minutes=31)
    assert await receiver_after.process_datagram(b"sig", received_at_utc=second_at) is not None
    assert await receiver_after.process_datagram(b"ref", received_at_utc=second_at) is not None
    await runtime.measurement_builder.flush()
    await runtime.aggregator.flush()
    await receiver_after.close()

    assert repo.counts() == (2, 2)
    with TestClient(api) as client:
        assert client.get("/beacons/B1/observations").json()["count"] == 2
        assert client.get("/beacons/B1/summaries").json()["count"] == 2
    repo.close()


class FailingOnceRepository:
    def __init__(self, inner):
        self.inner = inner
        self.fail_next = True

    @property
    def schema_version(self): return self.inner.schema_version
    def counts(self): return self.inner.counts()
    def close(self): return self.inner.close()
    def save_observation(self, observation):
        if self.fail_next:
            self.fail_next = False
            raise OSError("simulated storage outage")
        return self.inner.save_observation(observation)
    def save_interval_summary(self, summary): return self.inner.save_interval_summary(summary)
    def get_observation(self, *a, **k): return self.inner.get_observation(*a, **k)
    def list_observations(self, *a, **k): return self.inner.list_observations(*a, **k)
    def get_interval_summary(self, *a, **k): return self.inner.get_interval_summary(*a, **k)
    def list_interval_summaries(self, *a, **k): return self.inner.list_interval_summaries(*a, **k)


@pytest.mark.asyncio
async def test_storage_failure_is_counted_and_later_window_recovers(tmp_path: Path) -> None:
    inner = SQLiteRepository(tmp_path / "monitor.db")
    repo = FailingOnceRepository(inner)
    errors = []
    runtime = runtime_for(repo, on_error=errors.append)

    await replay_status_samples(runtime, [sample("sig", 1, -90), sample("ref", 1, -102)])
    assert runtime.counters.pipeline_errors == 1
    assert runtime.counters.observations_persisted == 0
    assert inner.counts()[0] == 0

    await replay_status_samples(runtime, [sample("sig", 11, -90), sample("ref", 11, -102)])
    assert runtime.counters.observations_persisted == 1
    assert inner.counts()[0] == 1
    assert errors
    inner.close()


class OpsRuntime:
    def __init__(self):
        self.is_started = True
        self.counters = type("Counters", (), {"pipeline_errors": 0})()


def test_partial_dependency_outage_keeps_liveness_but_fails_readiness() -> None:
    dependency_ok = False
    app = FastAPI()
    app.include_router(create_operations_router(OpsRuntime(), readiness_check=lambda: dependency_ok))
    with TestClient(app) as client:
        assert client.get("/ops/live").status_code == 200
        assert client.get("/ops/ready").status_code == 503
