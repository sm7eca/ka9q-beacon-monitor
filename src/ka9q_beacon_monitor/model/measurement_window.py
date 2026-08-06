from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Iterable

from .status_sample import StatusSample


WINDOW_DURATION = timedelta(seconds=10)


@dataclass(frozen=True, slots=True)
class MeasurementWindow:
    """Immutable ten-second collection of KA9Q status samples for one channel.

    The window owns temporal grouping and coverage metrics only. It does not
    classify beacon state and does not calculate beacon-specific SNR.
    """

    channel_id: str
    start_utc: datetime
    samples: tuple[StatusSample, ...] = field(default_factory=tuple)
    expected_status_rate_hz: float = 2.0

    def __post_init__(self) -> None:
        if not self.channel_id or not self.channel_id.strip():
            raise ValueError("channel_id must be non-empty")
        if self.start_utc.tzinfo is None or self.start_utc.utcoffset() is None:
            raise ValueError("start_utc must be timezone-aware")
        if self.start_utc.utcoffset() != timedelta(0):
            raise ValueError("start_utc must be UTC")
        if self.expected_status_rate_hz <= 0:
            raise ValueError("expected_status_rate_hz must be positive")

        ordered = tuple(sorted(self.samples, key=lambda sample: sample.timestamp_utc))
        object.__setattr__(self, "samples", ordered)

        for sample in ordered:
            if sample.channel_id != self.channel_id:
                raise ValueError("all samples must belong to channel_id")
            if sample.timestamp_utc < self.start_utc or sample.timestamp_utc >= self.end_utc:
                raise ValueError("all samples must be inside [start_utc, end_utc)")

    @classmethod
    def from_samples(
        cls,
        *,
        channel_id: str,
        start_utc: datetime,
        samples: Iterable[StatusSample],
        expected_status_rate_hz: float = 2.0,
    ) -> "MeasurementWindow":
        return cls(
            channel_id=channel_id,
            start_utc=start_utc,
            samples=tuple(samples),
            expected_status_rate_hz=expected_status_rate_hz,
        )

    @property
    def end_utc(self) -> datetime:
        return self.start_utc + WINDOW_DURATION

    @property
    def duration_seconds(self) -> float:
        return WINDOW_DURATION.total_seconds()

    @property
    def sample_count(self) -> int:
        return len(self.samples)

    @property
    def expected_sample_count(self) -> int:
        return round(self.duration_seconds * self.expected_status_rate_hz)

    @property
    def coverage_ratio(self) -> float:
        expected = self.expected_sample_count
        if expected <= 0:
            return 0.0
        return min(self.sample_count / expected, 1.0)

    @property
    def coverage_percent(self) -> float:
        return self.coverage_ratio * 100.0

    @property
    def is_empty(self) -> bool:
        return not self.samples

    @property
    def first_sample_utc(self) -> datetime | None:
        return self.samples[0].timestamp_utc if self.samples else None

    @property
    def last_sample_utc(self) -> datetime | None:
        return self.samples[-1].timestamp_utc if self.samples else None

    def median_baseband_power_db(self) -> float | None:
        values = [s.baseband_power_db for s in self.samples if s.baseband_power_db is not None]
        return median(values) if values else None

    def median_noise_density_db_hz(self) -> float | None:
        values = [s.noise_density_db_hz for s in self.samples if s.noise_density_db_hz is not None]
        return median(values) if values else None

    def freshness_age(self, now_utc: datetime) -> timedelta | None:
        if now_utc.tzinfo is None or now_utc.utcoffset() is None:
            raise ValueError("now_utc must be timezone-aware")
        if now_utc.utcoffset() != timedelta(0):
            raise ValueError("now_utc must be UTC")
        if self.last_sample_utc is None:
            return None
        return now_utc - self.last_sample_utc
