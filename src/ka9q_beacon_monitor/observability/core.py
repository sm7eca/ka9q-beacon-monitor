from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from typing import Callable, Mapping, Protocol

from fastapi import APIRouter, HTTPException, Response


class RuntimeStatus(Protocol):
    @property
    def is_started(self) -> bool: ...
    @property
    def counters(self) -> object: ...


@dataclass(frozen=True, slots=True)
class BuildIdentity:
    version: str
    revision: str
    build_time_utc: str | None = None

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> "BuildIdentity":
        env = os.environ if environ is None else environ
        try:
            package_version = version("ka9q-beacon-monitor")
        except PackageNotFoundError:
            package_version = "0+unknown"
        return cls(
            version=env.get("KA9Q_BUILD_VERSION", package_version),
            revision=env.get("KA9Q_BUILD_REVISION", "unknown"),
            build_time_utc=env.get("KA9Q_BUILD_TIME_UTC"),
        )


class JsonFormatter(logging.Formatter):
    """Stable one-record-per-line JSON formatter for operational logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp_utc": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        event = getattr(record, "event", None)
        if event is not None:
            payload["event"] = str(event)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def configure_structured_logging(*, level: int = logging.INFO, stream=None) -> logging.Logger:
    logger = logging.getLogger("ka9q_beacon_monitor")
    logger.setLevel(level)
    logger.propagate = False
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.handlers[:] = [handler]
    return logger


def _counter_values(runtime: RuntimeStatus) -> dict[str, int]:
    counters = runtime.counters
    names = (
        "windows_received",
        "classifications_completed",
        "verifications_attempted",
        "observations_persisted",
        "summaries_persisted",
        "pipeline_errors",
    )
    return {name: int(getattr(counters, name, 0)) for name in names}


def render_prometheus_metrics(runtime: RuntimeStatus, *, build: BuildIdentity) -> str:
    lines = [
        "# HELP ka9q_runtime_started Whether the application runtime is started.",
        "# TYPE ka9q_runtime_started gauge",
        f"ka9q_runtime_started {1 if runtime.is_started else 0}",
    ]
    for name, value in _counter_values(runtime).items():
        metric = f"ka9q_{name}_total"
        lines.extend((f"# TYPE {metric} counter", f"{metric} {value}"))
    labels = json.dumps(build.version)[1:-1], json.dumps(build.revision)[1:-1]
    lines.extend(("# TYPE ka9q_build_info gauge", f'ka9q_build_info{{version="{labels[0]}",revision="{labels[1]}"}} 1'))
    return "\n".join(lines) + "\n"


def create_operations_router(
    runtime: RuntimeStatus,
    *,
    build: BuildIdentity | None = None,
    readiness_check: Callable[[], bool] | None = None,
) -> APIRouter:
    identity = build or BuildIdentity.from_environment()
    router = APIRouter(prefix="/ops", tags=["operations"])

    @router.get("/live")
    def live() -> dict[str, str]:
        return {"status": "alive"}

    @router.get("/ready")
    def ready() -> dict[str, str]:
        ready_now = runtime.is_started and (readiness_check() if readiness_check is not None else True)
        if not ready_now:
            raise HTTPException(status_code=503, detail="not ready")
        return {"status": "ready"}

    @router.get("/build")
    def build_info() -> dict[str, str | None]:
        return asdict(identity)

    @router.get("/diagnostics")
    def diagnostics() -> dict[str, object]:
        return {"started": runtime.is_started, "counters": _counter_values(runtime), "build": asdict(identity)}

    @router.get("/metrics")
    def metrics() -> Response:
        return Response(render_prometheus_metrics(runtime, build=identity), media_type="text/plain; version=0.0.4; charset=utf-8")

    return router
