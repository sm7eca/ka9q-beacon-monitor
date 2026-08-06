from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from inspect import isawaitable

from ka9q_beacon_monitor.model import MeasurementWindow, StatusSample
from ka9q_beacon_monitor.model.measurement_window import WINDOW_DURATION

WindowHandler = Callable[[MeasurementWindow], Awaitable[None] | None]
ErrorHandler = Callable[[Exception], Awaitable[None] | None]


def _require_utc(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must be UTC")


def align_window_start(timestamp_utc: datetime) -> datetime:
    """Return the inclusive ten-second boundary containing timestamp_utc."""

    _require_utc(timestamp_utc, "timestamp_utc")
    second = timestamp_utc.second - (timestamp_utc.second % int(WINDOW_DURATION.total_seconds()))
    return timestamp_utc.replace(second=second, microsecond=0)


@dataclass(frozen=True, slots=True)
class BuilderCounters:
    samples_received: int = 0
    samples_accepted: int = 0
    samples_late: int = 0
    windows_emitted: int = 0
    handler_failures: int = 0


class MeasurementBuilder:
    """Group normalized status samples into deterministic ten-second windows.

    The builder is event-time based. A sample belongs to the UTC-aligned window
    containing its source timestamp. A newer sample closes all earlier windows
    for that channel. ``advance_time`` closes windows when no newer sample
    arrives. Empty windows are not synthesized.
    """

    def __init__(
        self,
        *,
        on_window: WindowHandler,
        expected_status_rate_hz: float = 2.0,
        on_error: ErrorHandler | None = None,
    ) -> None:
        if expected_status_rate_hz <= 0:
            raise ValueError("expected_status_rate_hz must be positive")
        self._on_window = on_window
        self._on_error = on_error
        self._expected_status_rate_hz = expected_status_rate_hz
        self._open: dict[str, tuple[datetime, list[StatusSample]]] = {}
        self._channel_locks: dict[str, asyncio.Lock] = {}
        self._last_closed_end: dict[str, datetime] = {}
        self._counters = BuilderCounters()

    @property
    def counters(self) -> BuilderCounters:
        return self._counters

    @property
    def open_channel_count(self) -> int:
        return len(self._open)

    def _lock_for(self, channel_id: str) -> asyncio.Lock:
        lock = self._channel_locks.get(channel_id)
        if lock is None:
            lock = asyncio.Lock()
            self._channel_locks[channel_id] = lock
        return lock

    async def add_sample(self, sample: StatusSample) -> None:
        self._counters = replace(
            self._counters,
            samples_received=self._counters.samples_received + 1,
        )
        async with self._lock_for(sample.channel_id):
            start = align_window_start(sample.timestamp_utc)
            end = start + WINDOW_DURATION
            last_closed_end = self._last_closed_end.get(sample.channel_id)
            if last_closed_end is not None and end <= last_closed_end:
                self._counters = replace(
                    self._counters,
                    samples_late=self._counters.samples_late + 1,
                )
                return

            current = self._open.get(sample.channel_id)
            if current is not None:
                current_start, current_samples = current
                if start < current_start:
                    self._counters = replace(
                        self._counters,
                        samples_late=self._counters.samples_late + 1,
                    )
                    return
                if start > current_start:
                    await self._emit(sample.channel_id, current_start, current_samples)
                    current = None

            if current is None:
                self._open[sample.channel_id] = (start, [sample])
            else:
                current[1].append(sample)

            self._counters = replace(
                self._counters,
                samples_accepted=self._counters.samples_accepted + 1,
            )

    async def advance_time(self, now_utc: datetime) -> None:
        """Close each open window whose exclusive end is <= now_utc."""

        _require_utc(now_utc, "now_utc")
        due = sorted(
            (
                (channel_id, start, samples)
                for channel_id, (start, samples) in self._open.items()
                if start + WINDOW_DURATION <= now_utc
            ),
            key=lambda item: (item[1], item[0]),
        )
        for channel_id, start, samples in due:
            async with self._lock_for(channel_id):
                active = self._open.get(channel_id)
                if active is not None and active[0] == start:
                    await self._emit(channel_id, start, active[1])

    async def flush(self) -> None:
        """Emit all currently open non-empty windows in deterministic order."""

        pending = sorted(
            (
                (channel_id, start, samples)
                for channel_id, (start, samples) in self._open.items()
            ),
            key=lambda item: (item[1], item[0]),
        )
        for channel_id, start, samples in pending:
            async with self._lock_for(channel_id):
                active = self._open.get(channel_id)
                if active is not None and active[0] == start:
                    await self._emit(channel_id, start, active[1])

    async def _emit(
        self,
        channel_id: str,
        start_utc: datetime,
        samples: list[StatusSample],
    ) -> None:
        active = self._open.get(channel_id)
        if active is None or active[0] != start_utc:
            return
        del self._open[channel_id]
        window = MeasurementWindow.from_samples(
            channel_id=channel_id,
            start_utc=start_utc,
            samples=tuple(samples),
            expected_status_rate_hz=self._expected_status_rate_hz,
        )
        try:
            result = self._on_window(window)
            if isawaitable(result):
                await result
        except Exception as exc:  # consumer isolation is a module contract
            self._counters = replace(
                self._counters,
                handler_failures=self._counters.handler_failures + 1,
            )
            await self._report_error(exc)
        else:
            self._counters = replace(
                self._counters,
                windows_emitted=self._counters.windows_emitted + 1,
            )
        finally:
            self._last_closed_end[channel_id] = start_utc + WINDOW_DURATION

    async def _report_error(self, exc: Exception) -> None:
        if self._on_error is None:
            return
        try:
            result = self._on_error(exc)
            if isawaitable(result):
                await result
        except Exception:
            return
