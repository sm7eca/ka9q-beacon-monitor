from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ka9q_beacon_monitor.model import IntervalSummary, Observation

SummaryHandler = Callable[[IntervalSummary], Awaitable[None] | None]
ErrorHandler = Callable[[Exception], Awaitable[None] | None]


@dataclass(frozen=True, slots=True)
class AggregatorPolicy:
    interval_seconds: int = 1800
    observation_period_seconds: int = 10
    minimum_valid_coverage_percent: float = 20.0
    weak_threshold_db: float = 3.0
    audible_threshold_db: float = 6.0
    strong_threshold_db: float = 15.0

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        if self.observation_period_seconds <= 0:
            raise ValueError("observation_period_seconds must be positive")
        if self.interval_seconds % self.observation_period_seconds != 0:
            raise ValueError("interval_seconds must be divisible by observation_period_seconds")
        if not 0.0 <= self.minimum_valid_coverage_percent <= 100.0:
            raise ValueError("minimum_valid_coverage_percent must be between 0 and 100")
        if not self.weak_threshold_db <= self.audible_threshold_db <= self.strong_threshold_db:
            raise ValueError("SNR thresholds must be non-decreasing")


@dataclass(slots=True)
class AggregatorCounters:
    observations_received: int = 0
    observations_accepted: int = 0
    observations_rejected: int = 0
    summaries_published: int = 0
    summary_handler_failures: int = 0


class IntervalAggregator:
    """Aggregate observations into aligned, non-overlapping interval summaries.

    State is serialized per beacon. Empty intervals are never synthesized.
    """

    def __init__(
        self,
        *,
        on_summary: SummaryHandler,
        on_error: ErrorHandler | None = None,
        policy: AggregatorPolicy | None = None,
    ) -> None:
        self._on_summary = on_summary
        self._on_error = on_error
        self.policy = policy or AggregatorPolicy()
        self.counters = AggregatorCounters()
        self._open: dict[str, tuple[datetime, list[Observation]]] = {}
        self._last_closed_end: dict[str, datetime] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def add_observation(self, observation: Observation) -> bool:
        self.counters.observations_received += 1
        beacon_id = observation.beacon_id
        async with self._lock_for(beacon_id):
            interval_start = align_interval_start(
                observation.window_start_utc,
                self.policy.interval_seconds,
            )
            interval_end = interval_start + timedelta(seconds=self.policy.interval_seconds)
            last_closed_end = self._last_closed_end.get(beacon_id)
            if last_closed_end is not None and interval_start < last_closed_end:
                self.counters.observations_rejected += 1
                return False

            active = self._open.get(beacon_id)
            if active is None:
                self._open[beacon_id] = (interval_start, [observation])
                self.counters.observations_accepted += 1
                return True

            current_start, current_observations = active
            if interval_start < current_start:
                self.counters.observations_rejected += 1
                return False
            if interval_start == current_start:
                if any(item.window_start_utc == observation.window_start_utc for item in current_observations):
                    self.counters.observations_rejected += 1
                    return False
                current_observations.append(observation)
                current_observations.sort(key=lambda item: item.window_start_utc)
                self.counters.observations_accepted += 1
                return True

            await self._emit(beacon_id, current_start, current_observations)
            self._open[beacon_id] = (interval_start, [observation])
            self.counters.observations_accepted += 1
            return True

    async def advance_time(self, now_utc: datetime) -> None:
        _require_utc("now_utc", now_utc)
        snapshot = sorted(
            ((start, beacon_id) for beacon_id, (start, _) in self._open.items()),
            key=lambda item: (item[0], item[1]),
        )
        for start, beacon_id in snapshot:
            end = start + timedelta(seconds=self.policy.interval_seconds)
            if end > now_utc:
                continue
            async with self._lock_for(beacon_id):
                active = self._open.get(beacon_id)
                if active is not None and active[0] == start:
                    await self._emit(beacon_id, active[0], active[1])
                    self._open.pop(beacon_id, None)

    async def flush(self) -> None:
        snapshot = sorted(
            ((start, beacon_id) for beacon_id, (start, _) in self._open.items()),
            key=lambda item: (item[0], item[1]),
        )
        for start, beacon_id in snapshot:
            async with self._lock_for(beacon_id):
                active = self._open.get(beacon_id)
                if active is not None and active[0] == start:
                    await self._emit(beacon_id, active[0], active[1])
                    self._open.pop(beacon_id, None)

    async def _emit(
        self,
        beacon_id: str,
        interval_start: datetime,
        observations: list[Observation],
    ) -> None:
        interval_end = interval_start + timedelta(seconds=self.policy.interval_seconds)
        summary = IntervalSummary.from_observations(
            beacon_id=beacon_id,
            interval_start_utc=interval_start,
            interval_end_utc=interval_end,
            observations=tuple(observations),
            observation_period_seconds=self.policy.observation_period_seconds,
            minimum_valid_coverage_percent=self.policy.minimum_valid_coverage_percent,
            weak_threshold_db=self.policy.weak_threshold_db,
            audible_threshold_db=self.policy.audible_threshold_db,
            strong_threshold_db=self.policy.strong_threshold_db,
        )
        try:
            result = self._on_summary(summary)
            if isinstance(result, Awaitable):
                await result
            self.counters.summaries_published += 1
        except Exception as exc:  # noqa: BLE001
            self.counters.summary_handler_failures += 1
            await self._report_error(exc)
        finally:
            self._last_closed_end[beacon_id] = interval_end

    async def _report_error(self, exc: Exception) -> None:
        if self._on_error is None:
            return
        try:
            result = self._on_error(exc)
            if isinstance(result, Awaitable):
                await result
        except Exception:  # noqa: BLE001
            return

    def _lock_for(self, beacon_id: str) -> asyncio.Lock:
        lock = self._locks.get(beacon_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[beacon_id] = lock
        return lock


def align_interval_start(value: datetime, interval_seconds: int = 1800) -> datetime:
    _require_utc("value", value)
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")
    epoch_seconds = int(value.timestamp())
    aligned = epoch_seconds - (epoch_seconds % interval_seconds)
    return datetime.fromtimestamp(aligned, tz=timezone.utc)


def _require_utc(name: str, value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    if value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{name} must be expressed in UTC")
