from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from statistics import median
import math
from typing import Iterable

from .observation import DetectionState, MeasurementQuality, Observation


class SummaryState(StrEnum):
    NO_DATA = "NO_DATA"
    NOT_HEARD = "NOT_HEARD"
    WEAK = "WEAK"
    AUDIBLE = "AUDIBLE"
    STRONG = "STRONG"
    INTERFERED = "INTERFERED"


@dataclass(frozen=True, slots=True)
class IntervalSummary:
    beacon_id: str
    interval_start_utc: datetime
    interval_end_utc: datetime
    expected_observation_count: int
    observation_count: int
    valid_observation_count: int
    verified_observation_count: int
    audible_observation_count: int
    data_coverage_percent: float
    audible_percent: float
    median_classification_snr_db: float | None
    maximum_classification_snr_db: float | None
    median_frequency_offset_hz: float | None
    final_state: SummaryState
    quality: MeasurementQuality

    def __post_init__(self) -> None:
        if not self.beacon_id.strip():
            raise ValueError("beacon_id must not be empty")
        if self.interval_start_utc.tzinfo is None or self.interval_end_utc.tzinfo is None:
            raise ValueError("interval timestamps must be timezone-aware")
        if self.interval_end_utc <= self.interval_start_utc:
            raise ValueError("interval_end_utc must be after interval_start_utc")
        if self.expected_observation_count <= 0:
            raise ValueError("expected_observation_count must be positive")
        counts = (
            self.observation_count,
            self.valid_observation_count,
            self.verified_observation_count,
            self.audible_observation_count,
        )
        if any(value < 0 for value in counts):
            raise ValueError("observation counts must not be negative")
        if self.valid_observation_count > self.observation_count:
            raise ValueError("valid_observation_count exceeds observation_count")
        if self.verified_observation_count > self.valid_observation_count:
            raise ValueError("verified_observation_count exceeds valid_observation_count")
        if self.audible_observation_count > self.valid_observation_count:
            raise ValueError("audible_observation_count exceeds valid_observation_count")
        for name in ("data_coverage_percent", "audible_percent"):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0.0 <= value <= 100.0:
                raise ValueError(f"{name} must be between 0 and 100")
        for name in ("median_classification_snr_db", "maximum_classification_snr_db", "median_frequency_offset_hz"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(value):
                raise ValueError(f"{name} must be finite when present")

    @classmethod
    def from_observations(
        cls,
        *,
        beacon_id: str,
        interval_start_utc: datetime,
        interval_end_utc: datetime,
        observations: Iterable[Observation],
        observation_period_seconds: int = 10,
        minimum_valid_coverage_percent: float = 20.0,
        weak_threshold_db: float = 3.0,
        audible_threshold_db: float = 6.0,
        strong_threshold_db: float = 15.0,
    ) -> "IntervalSummary":
        if interval_start_utc.tzinfo is None or interval_end_utc.tzinfo is None:
            raise ValueError("interval timestamps must be timezone-aware")
        duration_seconds = (interval_end_utc - interval_start_utc).total_seconds()
        if duration_seconds <= 0:
            raise ValueError("interval_end_utc must be after interval_start_utc")
        if observation_period_seconds <= 0:
            raise ValueError("observation_period_seconds must be positive")
        expected = int(round(duration_seconds / observation_period_seconds))
        if expected <= 0:
            raise ValueError("interval is too short for the observation period")

        selected = sorted(
            [
                observation
                for observation in observations
                if observation.beacon_id == beacon_id
                and interval_start_utc <= observation.window_start_utc < interval_end_utc
            ],
            key=lambda item: item.window_start_utc,
        )
        valid = [item for item in selected if item.detection_state != DetectionState.NO_DATA]
        verified = [item for item in valid if item.detection_state == DetectionState.VERIFIED_BEACON]
        audible_states = {
            DetectionState.SIGNAL_PRESENT,
            DetectionState.PROBABLE_BEACON,
            DetectionState.VERIFIED_BEACON,
        }
        audible = [item for item in valid if item.detection_state in audible_states]
        interfered = [item for item in valid if item.detection_state == DetectionState.INTERFERENCE]

        snrs = [item.classification_snr_db for item in valid if item.classification_snr_db is not None]
        offsets = [item.frequency_offset_hz for item in valid if item.frequency_offset_hz is not None]

        coverage = min(100.0, 100.0 * len(valid) / expected)
        audible_percent = 0.0 if not valid else 100.0 * len(audible) / len(valid)
        median_snr = median(snrs) if snrs else None
        maximum_snr = max(snrs) if snrs else None
        median_offset = median(offsets) if offsets else None

        final_state = _classify_summary(
            coverage=coverage,
            audible_percent=audible_percent,
            median_snr=median_snr,
            valid_count=len(valid),
            interference_count=len(interfered),
            minimum_valid_coverage_percent=minimum_valid_coverage_percent,
            weak_threshold_db=weak_threshold_db,
            audible_threshold_db=audible_threshold_db,
            strong_threshold_db=strong_threshold_db,
        )
        quality = _classify_quality(
            coverage=coverage,
            verified_count=len(verified),
            valid_count=len(valid),
            minimum_valid_coverage_percent=minimum_valid_coverage_percent,
        )

        return cls(
            beacon_id=beacon_id,
            interval_start_utc=interval_start_utc,
            interval_end_utc=interval_end_utc,
            expected_observation_count=expected,
            observation_count=len(selected),
            valid_observation_count=len(valid),
            verified_observation_count=len(verified),
            audible_observation_count=len(audible),
            data_coverage_percent=coverage,
            audible_percent=audible_percent,
            median_classification_snr_db=median_snr,
            maximum_classification_snr_db=maximum_snr,
            median_frequency_offset_hz=median_offset,
            final_state=final_state,
            quality=quality,
        )


def _classify_summary(
    *,
    coverage: float,
    audible_percent: float,
    median_snr: float | None,
    valid_count: int,
    interference_count: int,
    minimum_valid_coverage_percent: float,
    weak_threshold_db: float,
    audible_threshold_db: float,
    strong_threshold_db: float,
) -> SummaryState:
    if coverage < minimum_valid_coverage_percent or valid_count == 0:
        return SummaryState.NO_DATA
    if interference_count / valid_count > 0.5:
        return SummaryState.INTERFERED
    if audible_percent >= 50.0 and median_snr is not None and median_snr >= strong_threshold_db:
        return SummaryState.STRONG
    if audible_percent >= 50.0 and median_snr is not None and median_snr >= audible_threshold_db:
        return SummaryState.AUDIBLE
    if audible_percent >= 10.0 and median_snr is not None and median_snr >= weak_threshold_db:
        return SummaryState.WEAK
    return SummaryState.NOT_HEARD


def _classify_quality(
    *,
    coverage: float,
    verified_count: int,
    valid_count: int,
    minimum_valid_coverage_percent: float,
) -> MeasurementQuality:
    if coverage < minimum_valid_coverage_percent or valid_count == 0:
        return MeasurementQuality.INVALID
    if verified_count > 0 and coverage >= 80.0:
        return MeasurementQuality.VERIFIED
    if coverage >= 80.0:
        return MeasurementQuality.VALID
    return MeasurementQuality.DEGRADED
