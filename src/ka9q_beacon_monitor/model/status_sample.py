from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

class DemodMode(StrEnum):
    LINEAR = "LINEAR"
    FM = "FM"

class SampleQuality(StrEnum):
    VALID = "VALID"
    DEGRADED = "DEGRADED"
    INVALID = "INVALID"

@dataclass(frozen=True, slots=True)
class StatusSample:
    timestamp_utc: datetime
    channel_id: str
    frequency_hz: float
    baseband_power_db: float | None
    noise_density_db_hz: float | None
    gain_db: float | None
    output_level_db: float | None
    headroom_db: float | None
    pll_lock: bool | None
    demod_mode: DemodMode
    sample_quality: SampleQuality
    def __post_init__(self):
        if self.timestamp_utc.tzinfo is None or self.timestamp_utc.utcoffset() is None:
            raise ValueError("timestamp_utc must be timezone-aware")
        if self.timestamp_utc.utcoffset() != timedelta(0):
            raise ValueError("timestamp_utc must be UTC")
        if not self.channel_id or not self.channel_id.strip():
            raise ValueError("channel_id must be non-empty")
