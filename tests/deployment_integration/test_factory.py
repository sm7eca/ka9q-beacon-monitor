from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ka9q_beacon_monitor.deployment_factory import (
    DeploymentConfigurationError,
    create_app,
    load_deployment_configuration,
)


def write_runtime(tmp_path: Path, *, verification_enabled: bool = False) -> Path:
    path = tmp_path / "runtime.json"
    path.write_text(
        json.dumps(
            {
                "database_path": str(tmp_path / "monitor.db"),
                "status_multicast_group": "239.1.2.3",
                "status_port": 5006,
                "api_bind_host": "0.0.0.0",
                "api_port": 8000,
                "web_bind_host": "0.0.0.0",
                "web_port": 8000,
                "web_refresh_seconds": 10,
                "log_level": "INFO",
                "verification_enabled": verification_enabled,
            }
        ),
        encoding="utf-8",
    )
    return path


def write_deployment(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "deployment.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_no_sdr_factory_starts_full_app_without_receiver(tmp_path: Path) -> None:
    runtime_path = write_runtime(tmp_path)
    write_deployment(tmp_path, {"mode": "no_sdr", "beacons": []})

    app = create_app(config_path=runtime_path)
    with TestClient(app) as client:
        assert client.get("/ops/live").status_code == 200
        assert client.get("/ops/ready").status_code == 200
        assert client.get("/api/health").json()["observation_count"] == 0
        assert client.get("/api/beacons").json() == []
        assert client.get("/").status_code == 200
    assert (tmp_path / "monitor.db").exists()


def test_no_sdr_mode_does_not_require_bridge_executables(tmp_path: Path) -> None:
    path = write_deployment(
        tmp_path,
        {
            "mode": "no_sdr",
            "beacons": [],
            "status_bridge": None,
            "verification_bridge": None,
        },
    )
    config = load_deployment_configuration(path)
    assert config.mode == "no_sdr"
    assert config.status_bridge is None


def test_ka9q_mode_requires_status_bridge(tmp_path: Path) -> None:
    path = write_deployment(tmp_path, {"mode": "ka9q", "beacons": []})
    with pytest.raises(DeploymentConfigurationError, match="requires status_bridge"):
        load_deployment_configuration(path)


def test_deployment_config_rejects_unknown_keys(tmp_path: Path) -> None:
    path = write_deployment(tmp_path, {"mode": "no_sdr", "beacons": [], "surprise": True})
    with pytest.raises(DeploymentConfigurationError, match="unknown deployment key"):
        load_deployment_configuration(path)


def test_beacon_definition_is_exposed_by_api(tmp_path: Path) -> None:
    runtime_path = write_runtime(tmp_path)
    write_deployment(
        tmp_path,
        {
            "mode": "no_sdr",
            "beacons": [
                {
                    "beacon_id": "B1",
                    "signal_channel_id": "sig",
                    "reference_channel_ids": ["ref"],
                    "expected_callsign": "TEST",
                    "callsign": "TEST",
                    "frequency_hz": 144300000,
                    "description": "deployment smoke beacon",
                }
            ],
        },
    )
    app = create_app(config_path=runtime_path)
    with TestClient(app) as client:
        item = client.get("/api/beacons/B1")
        assert item.status_code == 200
        assert item.json()["callsign"] == "TEST"


def test_verification_enabled_requires_verification_bridge(tmp_path: Path, monkeypatch) -> None:
    runtime_path = write_runtime(tmp_path, verification_enabled=True)
    write_deployment(tmp_path, {"mode": "no_sdr", "beacons": []})
    monkeypatch.setenv("KA9Q_VERIFICATION_TOKEN", "secret")
    with pytest.raises(DeploymentConfigurationError, match="verification_bridge"):
        create_app(config_path=runtime_path)
