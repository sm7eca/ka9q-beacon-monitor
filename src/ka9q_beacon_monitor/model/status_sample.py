"""Normalized representation of one KA9Q radiod status sample."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import math


class DemodMode(StrEnum):
    """Normalized demodulator mode reported for a KA9Q channel."""

    LINEAR = "linear"
    FM = "fm"
    AM = "am"
    IQ = "iq"
    UNKNOWN = "unknown"


class SampleQuality(StrEnum):
    """Validation quality assigned while normalizing a status datagram."""

    VALID = "valid"
    PARTIAL = "partial"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class StatusSample:
    """One immutable, normalized KA9Q channel-status sample.

    This model contains receiver measurements only. It contains no beacon
    classification, derived local SNR, confidence, verification result, or
    persistence state.
    """

    timestamp_utc: datetime
    channel_id: str
    frequency_hz: float
    baseband_power_db: float | None
    noise_density_db_hz: float | None
    gain_db: float | None
    output_level_db: float | None
    headroom_db: float | None
    demod_mode: DemodMode
    pll_locked: bool | None
    sequence_number: int | None
    sample_quality: SampleQuality

    def __post_init__(self) -> None:
        if self.timestamp_utc.tzinfo is None:
            raise ValueError("timestamp_utc must be timezone-aware")
        if self.timestamp_utc.utcoffset() != timezone.utc.utcoffset(self.timestamp_utc):
            raise ValueError("timestamp_utc must be expressed in UTC")
        if not self.channel_id or not self.channel_id.strip():
            raise ValueError("channel_id must not be empty")
        if not math.isfinite(self.frequency_hz) or self.frequency_hz <= 0:
            raise ValueError("frequency_hz must be a positive finite value")
        if self.sequence_number is not None and self.sequence_number < 0:
            raise ValueError("sequence_number must be non-negative")

        for field_name in (
            "baseband_power_db",
            "noise_density_db_hz",
            "gain_db",
            "output_level_db",
            "headroom_db",
        ):
            value = getattr(self, field_name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{field_name} must be finite when present")

        if self.sample_quality is SampleQuality.VALID:
            if self.baseband_power_db is None or self.noise_density_db_hz is None:
                raise ValueError(
                    "VALID samples require baseband_power_db and noise_density_db_hz"
                )

        if self.sample_quality is SampleQuality.INVALID:
            if any(
                value is not None
                for value in (
                    self.baseband_power_db,
                    self.noise_density_db_hz,
                    self.gain_db,
                    self.output_level_db,
                    self.headroom_db,
                )
            ):
                raise ValueError("INVALID samples must not expose measurement values")
