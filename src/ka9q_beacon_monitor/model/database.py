from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RetentionPolicy:
    """Retention periods for persisted domain data.

    A value of ``None`` means that the record class is retained indefinitely.
    """

    observations_days: int = 90
    interval_summaries_days: int | None = None
    health_events_days: int = 30

    def __post_init__(self) -> None:
        for name in ("observations_days", "health_events_days"):
            value = getattr(self, name)
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if self.interval_summaries_days is not None and self.interval_summaries_days <= 0:
            raise ValueError("interval_summaries_days must be positive when present")


@dataclass(frozen=True, slots=True)
class DatabaseConfig:
    """SQLite database configuration owned by the persistence layer."""

    path: Path
    busy_timeout_ms: int = 5_000
    enable_wal: bool = True
    foreign_keys: bool = True

    def __post_init__(self) -> None:
        if not str(self.path):
            raise ValueError("path must not be empty")
        if self.busy_timeout_ms <= 0:
            raise ValueError("busy_timeout_ms must be positive")
