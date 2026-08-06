from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol, Sequence

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field


class ReadRepository(Protocol):
    """Read-only repository surface required by the REST API."""

    @property
    def schema_version(self) -> int: ...

    def counts(self) -> tuple[int, int]: ...

    def get_observation(self, beacon_id: str, window_start_utc: datetime | str) -> dict[str, Any] | None: ...

    def list_observations(self, beacon_id: str, *, limit: int = 100) -> list[dict[str, Any]]: ...

    def get_interval_summary(self, beacon_id: str, interval_start_utc: datetime | str) -> dict[str, Any] | None: ...

    def list_interval_summaries(self, beacon_id: str, *, limit: int = 100) -> list[dict[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class BeaconDefinition:
    beacon_id: str
    callsign: str | None = None
    frequency_hz: float | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if not self.beacon_id.strip():
            raise ValueError("beacon_id must not be empty")
        if self.frequency_hz is not None and self.frequency_hz <= 0:
            raise ValueError("frequency_hz must be positive when present")


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = "ok"
    schema_version: int
    observation_count: int
    interval_summary_count: int
    checked_at_utc: datetime


class BeaconResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    beacon_id: str
    callsign: str | None = None
    frequency_hz: float | None = None
    description: str | None = None


class RecordPage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    beacon_id: str
    count: int
    limit: int
    items: list[dict[str, Any]] = Field(default_factory=list)


def _parse_utc(value: str, *, parameter: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{parameter} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HTTPException(status_code=422, detail=f"{parameter} must include a UTC offset")
    if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise HTTPException(status_code=422, detail=f"{parameter} must be expressed in UTC")
    return parsed.astimezone(timezone.utc)


def create_app(
    repository: ReadRepository,
    *,
    beacons: Sequence[BeaconDefinition] = (),
    title: str = "KA9Q Beacon Monitor API",
) -> FastAPI:
    """Create a read-only REST API over approved repository data."""

    beacon_map = {item.beacon_id: item for item in beacons}
    if len(beacon_map) != len(beacons):
        raise ValueError("beacon_id values must be unique")

    app = FastAPI(title=title, version="1.0.0")

    @app.get("/health", response_model=HealthResponse, tags=["operations"])
    def health() -> HealthResponse:
        try:
            observation_count, summary_count = repository.counts()
            schema_version = repository.schema_version
        except Exception as exc:
            raise HTTPException(status_code=503, detail="repository unavailable") from exc
        return HealthResponse(
            schema_version=schema_version,
            observation_count=observation_count,
            interval_summary_count=summary_count,
            checked_at_utc=datetime.now(timezone.utc),
        )

    @app.get("/beacons", response_model=list[BeaconResponse], tags=["beacons"])
    def list_beacons() -> list[BeaconResponse]:
        return [BeaconResponse(**asdict(item)) for item in sorted(beacons, key=lambda item: item.beacon_id)]

    @app.get("/beacons/{beacon_id}", response_model=BeaconResponse, tags=["beacons"])
    def get_beacon(beacon_id: str) -> BeaconResponse:
        item = beacon_map.get(beacon_id)
        if item is None:
            raise HTTPException(status_code=404, detail="beacon not found")
        return BeaconResponse(**asdict(item))

    def require_beacon(beacon_id: str) -> BeaconDefinition:
        item = beacon_map.get(beacon_id)
        if item is None:
            raise HTTPException(status_code=404, detail="beacon not found")
        return item

    @app.get("/beacons/{beacon_id}/observations", response_model=RecordPage, tags=["observations"])
    def list_observations(
        beacon_id: str,
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> RecordPage:
        require_beacon(beacon_id)
        items = repository.list_observations(beacon_id, limit=limit)
        return RecordPage(beacon_id=beacon_id, count=len(items), limit=limit, items=items)

    @app.get("/beacons/{beacon_id}/observations/{window_start_utc}", tags=["observations"])
    def get_observation(beacon_id: str, window_start_utc: str) -> dict[str, Any]:
        require_beacon(beacon_id)
        start = _parse_utc(window_start_utc, parameter="window_start_utc")
        item = repository.get_observation(beacon_id, start)
        if item is None:
            raise HTTPException(status_code=404, detail="observation not found")
        return item

    @app.get("/beacons/{beacon_id}/summaries", response_model=RecordPage, tags=["summaries"])
    def list_summaries(
        beacon_id: str,
        limit: int = Query(default=100, ge=1, le=1000),
    ) -> RecordPage:
        require_beacon(beacon_id)
        items = repository.list_interval_summaries(beacon_id, limit=limit)
        return RecordPage(beacon_id=beacon_id, count=len(items), limit=limit, items=items)

    @app.get("/beacons/{beacon_id}/summaries/{interval_start_utc}", tags=["summaries"])
    def get_summary(beacon_id: str, interval_start_utc: str) -> dict[str, Any]:
        require_beacon(beacon_id)
        start = _parse_utc(interval_start_utc, parameter="interval_start_utc")
        item = repository.get_interval_summary(beacon_id, start)
        if item is None:
            raise HTTPException(status_code=404, detail="interval summary not found")
        return item

    return app
