from __future__ import annotations

import io
import json
import logging
from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ka9q_beacon_monitor.observability import BuildIdentity, JsonFormatter, configure_structured_logging, create_operations_router, render_prometheus_metrics


@dataclass
class Counters:
    windows_received: int = 2
    classifications_completed: int = 1
    verifications_attempted: int = 1
    observations_persisted: int = 1
    summaries_persisted: int = 0
    pipeline_errors: int = 3


class Runtime:
    def __init__(self, started: bool = True):
        self.is_started = started
        self.counters = Counters()


def client(runtime: Runtime, *, ready=None) -> TestClient:
    app = FastAPI()
    app.include_router(create_operations_router(runtime, build=BuildIdentity("1.2.3", "abc123", "2026-08-07T00:00:00Z"), readiness_check=ready))
    return TestClient(app)


def test_liveness_is_process_level_not_readiness() -> None:
    c = client(Runtime(False))
    assert c.get("/ops/live").json() == {"status": "alive"}
    assert c.get("/ops/ready").status_code == 503


def test_readiness_requires_started_runtime() -> None:
    assert client(Runtime(True)).get("/ops/ready").status_code == 200


def test_readiness_can_include_dependency_check() -> None:
    assert client(Runtime(True), ready=lambda: False).get("/ops/ready").status_code == 503


def test_build_identity_endpoint_is_explicit() -> None:
    data = client(Runtime()).get("/ops/build").json()
    assert data == {"version": "1.2.3", "revision": "abc123", "build_time_utc": "2026-08-07T00:00:00Z"}


def test_diagnostics_exposes_runtime_counters() -> None:
    data = client(Runtime()).get("/ops/diagnostics").json()
    assert data["started"] is True
    assert data["counters"]["pipeline_errors"] == 3
    assert data["counters"]["windows_received"] == 2


def test_metrics_are_prometheus_text() -> None:
    response = client(Runtime()).get("/ops/metrics")
    assert response.status_code == 200
    assert "ka9q_pipeline_errors_total 3" in response.text
    assert 'ka9q_build_info{version="1.2.3",revision="abc123"} 1' in response.text


def test_metrics_reflect_stopped_runtime() -> None:
    assert "ka9q_runtime_started 0" in render_prometheus_metrics(Runtime(False), build=BuildIdentity("v", "r"))


def test_build_identity_uses_only_named_build_environment() -> None:
    identity = BuildIdentity.from_environment({"KA9Q_BUILD_VERSION": "9", "KA9Q_BUILD_REVISION": "deadbeef", "KA9Q_VERIFICATION_TOKEN": "SECRET"})
    assert identity.version == "9"
    assert identity.revision == "deadbeef"
    assert "SECRET" not in repr(identity)


def test_json_formatter_is_parseable_and_structured() -> None:
    record = logging.LogRecord("ka9q_beacon_monitor.runtime", logging.WARNING, __file__, 1, "receiver %s", ("down",), None)
    record.event = "receiver_failure"
    data = json.loads(JsonFormatter().format(record))
    assert data["level"] == "WARNING"
    assert data["message"] == "receiver down"
    assert data["event"] == "receiver_failure"
    assert data["timestamp_utc"].endswith("Z")


def test_configure_logging_replaces_handlers_and_emits_one_json_line() -> None:
    stream = io.StringIO()
    logger = configure_structured_logging(stream=stream)
    logger.info("started", extra={"event": "startup"})
    lines = stream.getvalue().splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["event"] == "startup"


def test_formatter_does_not_serialize_arbitrary_record_extras() -> None:
    record = logging.LogRecord("x", logging.INFO, __file__, 1, "safe", (), None)
    record.secret_token = "DO-NOT-LOG"
    assert "DO-NOT-LOG" not in JsonFormatter().format(record)
