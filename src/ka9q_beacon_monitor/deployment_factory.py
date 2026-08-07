"""Concrete production deployment factory for the composed KA9Q Beacon Monitor.

The factory intentionally keeps deployment wiring outside reviewed domain modules.
It consumes the validated M5.1 runtime configuration plus a sibling
``deployment.json`` that describes beacon pipelines and adapter commands.

``mode = no_sdr`` starts the complete application without opening the KA9Q
multicast receiver. This is the supported software-deployment smoke-test mode for
hosts where radiod/SDR is intentionally unavailable. It does not constitute
Phase-0 field evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from fastapi import FastAPI

from ka9q_beacon_monitor.api.server import BeaconDefinition
from ka9q_beacon_monitor.config import ConfigError, RuntimeConfiguration, load_runtime_configuration
from ka9q_beacon_monitor.ka9q import (
    BridgeCommand,
    Ka9qStatusBridgeDecoder,
    Ka9qStatusReceiver,
    Ka9qVerificationBridgeBackend,
    MulticastEndpoint,
    VerificationBridgeConfig,
)
from ka9q_beacon_monitor.observability import BuildIdentity
from ka9q_beacon_monitor.processing import BeaconClassifier, VerificationAnalyzer
from ka9q_beacon_monitor.repository import SQLiteRepository
from ka9q_beacon_monitor.runtime import BeaconPipelineConfig, BeaconRuntime, create_main_app
from ka9q_beacon_monitor.web import WebUiConfig


class DeploymentConfigurationError(ValueError):
    """Raised before runtime start when deployment-specific wiring is invalid."""


@dataclass(frozen=True, slots=True)
class DeploymentBeacon:
    beacon_id: str
    signal_channel_id: str
    reference_channel_ids: tuple[str, ...]
    expected_callsign: str | None = None
    callsign: str | None = None
    frequency_hz: float | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        BeaconPipelineConfig(
            beacon_id=self.beacon_id,
            signal_channel_id=self.signal_channel_id,
            reference_channel_ids=self.reference_channel_ids,
            expected_callsign=self.expected_callsign,
        )
        BeaconDefinition(
            beacon_id=self.beacon_id,
            callsign=self.callsign,
            frequency_hz=self.frequency_hz,
            description=self.description,
        )


@dataclass(frozen=True, slots=True)
class DeploymentConfig:
    mode: str
    beacons: tuple[DeploymentBeacon, ...]
    status_bridge: BridgeCommand | None = None
    verification_bridge: BridgeCommand | None = None

    def __post_init__(self) -> None:
        if self.mode not in {"no_sdr", "ka9q"}:
            raise DeploymentConfigurationError("deployment mode must be 'no_sdr' or 'ka9q'")
        if self.mode == "ka9q" and self.status_bridge is None:
            raise DeploymentConfigurationError("ka9q mode requires status_bridge")
        ids = [item.beacon_id for item in self.beacons]
        if len(ids) != len(set(ids)):
            raise DeploymentConfigurationError("beacon_id values must be unique")


class _UnavailableVerificationBackend:
    async def analyze(self, request):
        raise RuntimeError("verification backend is disabled")


def _bridge_from_json(value: Any, *, name: str) -> BridgeCommand | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise DeploymentConfigurationError(f"{name} must be an object or null")
    unknown = set(value) - {"argv", "timeout_seconds"}
    if unknown:
        raise DeploymentConfigurationError(f"unknown {name} key(s): {', '.join(sorted(unknown))}")
    argv = value.get("argv")
    if not isinstance(argv, list) or not argv or not all(isinstance(part, str) and part for part in argv):
        raise DeploymentConfigurationError(f"{name}.argv must be a non-empty string list")
    timeout = value.get("timeout_seconds", 2.0)
    return BridgeCommand(tuple(argv), timeout_seconds=float(timeout))


def load_deployment_configuration(path: str | Path) -> DeploymentConfig:
    source = Path(path)
    try:
        raw = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DeploymentConfigurationError(f"deployment configuration not found: {source}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise DeploymentConfigurationError(f"deployment configuration is not valid JSON: {source}") from exc
    if not isinstance(raw, dict):
        raise DeploymentConfigurationError("deployment configuration root must be an object")
    unknown = set(raw) - {"mode", "beacons", "status_bridge", "verification_bridge"}
    if unknown:
        raise DeploymentConfigurationError("unknown deployment key(s): " + ", ".join(sorted(unknown)))
    if "mode" not in raw:
        raise DeploymentConfigurationError("deployment mode is required")
    beacons_raw = raw.get("beacons", [])
    if not isinstance(beacons_raw, list):
        raise DeploymentConfigurationError("beacons must be a list")
    beacons: list[DeploymentBeacon] = []
    allowed = {
        "beacon_id",
        "signal_channel_id",
        "reference_channel_ids",
        "expected_callsign",
        "callsign",
        "frequency_hz",
        "description",
    }
    for index, item in enumerate(beacons_raw):
        if not isinstance(item, dict):
            raise DeploymentConfigurationError(f"beacons[{index}] must be an object")
        extra = set(item) - allowed
        if extra:
            raise DeploymentConfigurationError(
                f"unknown beacons[{index}] key(s): {', '.join(sorted(extra))}"
            )
        try:
            references = item["reference_channel_ids"]
            if not isinstance(references, list):
                raise TypeError("reference_channel_ids must be a list")
            beacons.append(
                DeploymentBeacon(
                    beacon_id=str(item["beacon_id"]),
                    signal_channel_id=str(item["signal_channel_id"]),
                    reference_channel_ids=tuple(str(value) for value in references),
                    expected_callsign=(str(item["expected_callsign"]) if item.get("expected_callsign") is not None else None),
                    callsign=(str(item["callsign"]) if item.get("callsign") is not None else None),
                    frequency_hz=(float(item["frequency_hz"]) if item.get("frequency_hz") is not None else None),
                    description=(str(item["description"]) if item.get("description") is not None else None),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DeploymentConfigurationError(f"invalid beacons[{index}] definition") from exc
    return DeploymentConfig(
        mode=str(raw["mode"]),
        beacons=tuple(beacons),
        status_bridge=_bridge_from_json(raw.get("status_bridge"), name="status_bridge"),
        verification_bridge=_bridge_from_json(raw.get("verification_bridge"), name="verification_bridge"),
    )


def _build_runtime(runtime_config: RuntimeConfiguration, deployment: DeploymentConfig) -> BeaconRuntime:
    repository = SQLiteRepository(runtime_config.app.database_path)
    classifier = BeaconClassifier()

    if runtime_config.app.verification_enabled:
        if deployment.verification_bridge is None:
            repository.close()
            raise DeploymentConfigurationError(
                "verification_enabled requires deployment verification_bridge"
            )
        token = runtime_config.secrets.verification_token
        verifier_backend = Ka9qVerificationBridgeBackend(
            VerificationBridgeConfig(
                deployment.verification_bridge,
                token=(token.get_secret_value() if token is not None else None),
            )
        )
    else:
        verifier_backend = _UnavailableVerificationBackend()
    verifier = VerificationAnalyzer(verifier_backend)

    pipelines = [
        BeaconPipelineConfig(
            beacon_id=item.beacon_id,
            signal_channel_id=item.signal_channel_id,
            reference_channel_ids=item.reference_channel_ids,
            expected_callsign=item.expected_callsign,
        )
        for item in deployment.beacons
    ]
    runtime = BeaconRuntime(
        repository=repository,
        classifier=classifier,
        verifier=verifier,
        beacon_pipelines=pipelines,
    )

    if deployment.mode == "ka9q":
        assert deployment.status_bridge is not None
        decoder = Ka9qStatusBridgeDecoder(deployment.status_bridge)
        receiver = Ka9qStatusReceiver(
            MulticastEndpoint(
                group=runtime_config.app.status_multicast_group,
                port=runtime_config.app.status_port,
            ),
            decoder,
            runtime.ingest_sample,
        )
        runtime.receiver = receiver
    return runtime


def create_app(*, config_path: str | Path) -> FastAPI:
    """Create the concrete production ASGI app from repository-controlled config."""

    runtime_path = Path(config_path)
    runtime_config = load_runtime_configuration(runtime_path)
    deployment_path = runtime_path.with_name("deployment.json")
    deployment = load_deployment_configuration(deployment_path)
    runtime = _build_runtime(runtime_config, deployment)
    beacons = [
        BeaconDefinition(
            beacon_id=item.beacon_id,
            callsign=item.callsign,
            frequency_hz=item.frequency_hz,
            description=item.description,
        )
        for item in deployment.beacons
    ]
    return create_main_app(
        runtime,
        beacons=beacons,
        web_config=WebUiConfig(
            api_base_url="/api",
            refresh_seconds=runtime_config.app.web_refresh_seconds,
        ),
        build_identity=BuildIdentity.from_environment(),
    )
