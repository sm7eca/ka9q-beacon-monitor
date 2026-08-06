"""Application orchestration for the KA9Q beacon monitor.

This module wires the already-reviewed components without moving domain logic
into the composition root. All hardware- and DSP-specific adapters remain
injected dependencies.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from inspect import isawaitable
from typing import Protocol

from fastapi import FastAPI

from ka9q_beacon_monitor.api.server import BeaconDefinition, create_app as create_api_app
from ka9q_beacon_monitor.model import MeasurementWindow, Observation, StatusSample
from ka9q_beacon_monitor.processing import (
    BeaconClassifier,
    ClassificationInput,
    IntervalAggregator,
    MeasurementBuilder,
    VerificationAnalyzer,
)
from ka9q_beacon_monitor.repository.sqlite_repository import SQLiteRepository
from ka9q_beacon_monitor.web.app import WebUiConfig, create_web_app


class ReceiverLifecycle(Protocol):
    async def start(self) -> None: ...
    async def close(self) -> None: ...


ErrorHandler = Callable[[Exception], Awaitable[None] | None]


@dataclass(frozen=True, slots=True)
class BeaconPipelineConfig:
    beacon_id: str
    signal_channel_id: str
    reference_channel_ids: tuple[str, ...]
    expected_callsign: str | None = None

    def __post_init__(self) -> None:
        if not self.beacon_id.strip():
            raise ValueError("beacon_id must not be empty")
        if not self.signal_channel_id.strip():
            raise ValueError("signal_channel_id must not be empty")
        if not self.reference_channel_ids:
            raise ValueError("at least one reference_channel_id is required")
        if self.signal_channel_id in self.reference_channel_ids:
            raise ValueError("signal channel cannot also be a reference channel")
        if len(set(self.reference_channel_ids)) != len(self.reference_channel_ids):
            raise ValueError("reference_channel_ids must be unique")


@dataclass(slots=True)
class RuntimeCounters:
    windows_received: int = 0
    classifications_completed: int = 0
    verifications_attempted: int = 0
    observations_persisted: int = 0
    summaries_persisted: int = 0
    pipeline_errors: int = 0


class BeaconRuntime:
    """Coordinate measurement, classification, verification and persistence.

    Windows are joined by ``(beacon_id, start_utc)``. A classification is
    performed exactly once when the configured signal window and every required
    reference window are available. Previous state is retained per beacon to
    preserve classifier hysteresis.
    """

    def __init__(
        self,
        *,
        repository: SQLiteRepository,
        classifier: BeaconClassifier,
        verifier: VerificationAnalyzer,
        beacon_pipelines: Sequence[BeaconPipelineConfig],
        receiver: ReceiverLifecycle | None = None,
        expected_status_rate_hz: float = 2.0,
        on_error: ErrorHandler | None = None,
    ) -> None:
        self.repository = repository
        self.classifier = classifier
        self.verifier = verifier
        self.receiver = receiver
        self.on_error = on_error
        self.counters = RuntimeCounters()
        self._pipelines = {item.beacon_id: item for item in beacon_pipelines}
        if len(self._pipelines) != len(beacon_pipelines):
            raise ValueError("beacon_id values must be unique")

        self._channel_to_beacons: dict[str, set[str]] = {}
        for item in beacon_pipelines:
            for channel_id in (item.signal_channel_id, *item.reference_channel_ids):
                self._channel_to_beacons.setdefault(channel_id, set()).add(item.beacon_id)

        self._pending: dict[tuple[str, datetime], dict[str, MeasurementWindow]] = {}
        self._previous_state: dict[str, object] = {}
        self._pipeline_locks: dict[str, asyncio.Lock] = {}
        self.aggregator = IntervalAggregator(
            on_summary=self._persist_summary,
            on_error=self._handle_error,
        )
        self.measurement_builder = MeasurementBuilder(
            on_window=self._on_window,
            expected_status_rate_hz=expected_status_rate_hz,
            on_error=self._handle_error,
        )
        self._started = False

    @property
    def is_started(self) -> bool:
        return self._started

    async def start(self) -> None:
        if self._started:
            raise RuntimeError("runtime is already started")
        self._started = True
        try:
            if self.receiver is not None:
                await self.receiver.start()
        except Exception:
            self._started = False
            raise

    async def close(self) -> None:
        if not self._started:
            return
        try:
            if self.receiver is not None:
                await self.receiver.close()
            await self.measurement_builder.flush()
            await self.aggregator.flush()
        finally:
            self.repository.close()
            self._started = False

    async def ingest_sample(self, sample: StatusSample) -> bool:
        return await self.measurement_builder.add_sample(sample)

    async def advance_time(self, now_utc: datetime | None = None) -> None:
        active = now_utc or datetime.now(timezone.utc)
        await self.measurement_builder.advance_time(active)
        await self.aggregator.advance_time(active)

    async def _on_window(self, window: MeasurementWindow) -> None:
        self.counters.windows_received += 1
        beacon_ids = self._channel_to_beacons.get(window.channel_id, set())
        for beacon_id in sorted(beacon_ids):
            async with self._lock_for(beacon_id):
                await self._join_and_process(beacon_id, window)

    async def _join_and_process(self, beacon_id: str, window: MeasurementWindow) -> None:
        config = self._pipelines[beacon_id]
        key = (beacon_id, window.start_utc)
        joined = self._pending.setdefault(key, {})
        joined[window.channel_id] = window
        required = {config.signal_channel_id, *config.reference_channel_ids}
        if not required.issubset(joined):
            return

        signal = joined[config.signal_channel_id]
        references = tuple(joined[channel_id] for channel_id in config.reference_channel_ids)
        previous = self._previous_state.get(beacon_id)
        classified_observation = self.classifier.classify(
            ClassificationInput.from_windows(
                beacon_id=beacon_id,
                signal_window=signal,
                reference_windows=references,
                previous_state=previous,
            )
        )
        self.counters.classifications_completed += 1

        # Classifier hysteresis must use the classifier's own pre-verification
        # state. VERIFIED_BEACON is introduced by VerificationAnalyzer and is
        # intentionally not part of BeaconClassifier's state machine.
        self._previous_state[beacon_id] = classified_observation.detection_state

        self.counters.verifications_attempted += 1
        observation = await self.verifier.verify(
            classified_observation,
            expected_callsign=config.expected_callsign,
        )
        self.repository.save_observation(observation)
        self.counters.observations_persisted += 1
        await self.aggregator.add_observation(observation)
        self._pending.pop(key, None)

    def _persist_summary(self, summary: object) -> None:
        self.repository.save_interval_summary(summary)
        self.counters.summaries_persisted += 1

    async def _handle_error(self, exc: Exception) -> None:
        self.counters.pipeline_errors += 1
        if self.on_error is None:
            return
        try:
            result = self.on_error(exc)
            if isawaitable(result):
                await result
        except Exception:
            return

    def _lock_for(self, beacon_id: str) -> asyncio.Lock:
        lock = self._pipeline_locks.get(beacon_id)
        if lock is None:
            lock = asyncio.Lock()
            self._pipeline_locks[beacon_id] = lock
        return lock


def create_main_app(
    runtime: BeaconRuntime,
    *,
    beacons: Sequence[BeaconDefinition],
    web_config: WebUiConfig | None = None,
) -> FastAPI:
    """Create one ASGI app exposing API and dashboard with shared lifecycle."""

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await runtime.start()
        try:
            yield
        finally:
            await runtime.close()

    app = FastAPI(
        title="KA9Q Beacon Monitor",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    api_app = create_api_app(runtime.repository, beacons=beacons)
    ui_config = web_config or WebUiConfig(api_base_url="/api")
    web_app = create_web_app(ui_config)
    app.mount("/api", api_app)
    app.mount("/", web_app)
    return app
