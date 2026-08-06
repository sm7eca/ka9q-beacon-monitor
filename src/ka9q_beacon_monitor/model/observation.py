from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from math import isfinite


class DetectionState(StrEnum):
    NO_SIGNAL = "no_signal"
    SIGNAL_PRESENT = "signal_present"
    PROBABLE_BEACON = "probable_beacon"
    VERIFIED_BEACON = "verified_beacon"
    INTERFERENCE = "interference"
    NO_DATA = "no_data"


class MeasurementSource(StrEnum):
    STATUS_ONLY = "status_only"
    VERIFIED_PCM = "verified_pcm"
    VERIFIED_IQ = "verified_iq"
    VERIFIED_CW = "verified_cw"
    VERIFIED_MORSE = "verified_morse"


class QualityLevel(StrEnum):
    INVALID = "invalid"
    DEGRADED = "degraded"
    NOMINAL = "nominal"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class Observation:
    """One immutable result for one beacon and one closed measurement window.

    classification_snr_db follows a deterministic policy:
    - use verification_snr_db when verification is accepted;
    - otherwise use derived_local_snr_db;
    - never use ka9q_reported_snr_db as a classification dependency.
    """

    beacon_id: str
    window_start_utc: datetime
    window_end_utc: datetime
    detection_state: DetectionState
    measurement_source: MeasurementSource

    derived_local_snr_db: float | None
    verification_snr_db: float | None
    ka9q_reported_snr_db: float | None

    measurement_quality: QualityLevel
    verification_quality: QualityLevel
    identification_quality: QualityLevel

    verification_accepted: bool
    frequency_offset_hz: float | None = None
    identified_callsign: str | None = None
    reason_code: str = "unspecified"

    def __post_init__(self) -> None:
        if not self.beacon_id.strip():
            raise ValueError("beacon_id must not be empty")
        self._require_utc("window_start_utc", self.window_start_utc)
        self._require_utc("window_end_utc", self.window_end_utc)
        if self.window_end_utc <= self.window_start_utc:
            raise ValueError("window_end_utc must be after window_start_utc")
        if not self.reason_code.strip():
            raise ValueError("reason_code must not be empty")

        for name in (
            "derived_local_snr_db",
            "verification_snr_db",
            "ka9q_reported_snr_db",
            "frequency_offset_hz",
        ):
            value = getattr(self, name)
            if value is not None and not isfinite(value):
                raise ValueError(f"{name} must be finite when present")

        if self.verification_accepted:
            if self.verification_snr_db is None:
                raise ValueError(
                    "verification_snr_db is required when verification_accepted is true"
                )
            if self.measurement_source is MeasurementSource.STATUS_ONLY:
                raise ValueError(
                    "measurement_source cannot be STATUS_ONLY when verification is accepted"
                )
        elif self.detection_state is DetectionState.VERIFIED_BEACON:
            raise ValueError(
                "VERIFIED_BEACON requires verification_accepted to be true"
            )

        if self.detection_state is DetectionState.NO_DATA:
            if self.classification_snr_db is not None:
                raise ValueError("NO_DATA must not expose classification_snr_db")
            if self.measurement_quality is not QualityLevel.INVALID:
                raise ValueError("NO_DATA requires INVALID measurement_quality")

        if self.identified_callsign is not None and not self.identified_callsign.strip():
            raise ValueError("identified_callsign must be non-empty when present")

    @property
    def classification_snr_db(self) -> float | None:
        """Return the only SNR value permitted for classification."""
        if self.detection_state is DetectionState.NO_DATA:
            return None
        if self.verification_accepted:
            return self.verification_snr_db
        return self.derived_local_snr_db

    @staticmethod
    def _require_utc(name: str, value: datetime) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name} must be timezone-aware")
        if value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError(f"{name} must be expressed in UTC")
