"""Deterministic status-driven beacon classification."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable

from ka9q_beacon_monitor.model import (
    DetectionState,
    MeasurementSource,
    MeasurementWindow,
    Observation,
    QualityLevel,
)


@dataclass(frozen=True, slots=True)
class ClassifierConfig:
    """Thresholds and quality gates for one classifier instance."""

    minimum_signal_coverage_ratio: float = 0.5
    minimum_reference_coverage_ratio: float = 0.5
    minimum_reference_windows: int = 1
    signal_present_enter_db: float = 6.0
    signal_present_exit_db: float = 4.5
    probable_beacon_enter_db: float = 9.0
    probable_beacon_exit_db: float = 7.5
    high_quality_coverage_ratio: float = 0.9
    nominal_quality_coverage_ratio: float = 0.7
    maximum_reference_spread_db: float = 6.0

    def __post_init__(self) -> None:
        for name in (
            "minimum_signal_coverage_ratio",
            "minimum_reference_coverage_ratio",
            "high_quality_coverage_ratio",
            "nominal_quality_coverage_ratio",
        ):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.minimum_reference_windows < 1:
            raise ValueError("minimum_reference_windows must be at least 1")
        if self.signal_present_exit_db > self.signal_present_enter_db:
            raise ValueError("signal_present_exit_db must not exceed enter threshold")
        if self.probable_beacon_exit_db > self.probable_beacon_enter_db:
            raise ValueError("probable_beacon_exit_db must not exceed enter threshold")
        if self.probable_beacon_enter_db < self.signal_present_enter_db:
            raise ValueError("probable threshold must not be below signal threshold")
        if self.nominal_quality_coverage_ratio > self.high_quality_coverage_ratio:
            raise ValueError("nominal quality threshold must not exceed high threshold")
        if self.maximum_reference_spread_db < 0:
            raise ValueError("maximum_reference_spread_db must be non-negative")


@dataclass(frozen=True, slots=True)
class ClassificationInput:
    """One beacon's signal window and its local reference windows."""

    beacon_id: str
    signal_window: MeasurementWindow
    reference_windows: tuple[MeasurementWindow, ...]
    previous_state: DetectionState | None = None

    def __post_init__(self) -> None:
        if not self.beacon_id.strip():
            raise ValueError("beacon_id must not be empty")
        for reference in self.reference_windows:
            if reference.start_utc != self.signal_window.start_utc:
                raise ValueError("all windows must share the same start_utc")
            if reference.end_utc != self.signal_window.end_utc:
                raise ValueError("all windows must share the same end_utc")
            if reference.channel_id == self.signal_window.channel_id:
                raise ValueError("reference channel must differ from signal channel")

    @classmethod
    def from_windows(
        cls,
        *,
        beacon_id: str,
        signal_window: MeasurementWindow,
        reference_windows: Iterable[MeasurementWindow],
        previous_state: DetectionState | None = None,
    ) -> "ClassificationInput":
        return cls(
            beacon_id=beacon_id,
            signal_window=signal_window,
            reference_windows=tuple(reference_windows),
            previous_state=previous_state,
        )


class BeaconClassifier:
    """Create a status-only Observation from synchronized windows.

    The classifier derives local SNR from median signal-channel baseband power
    minus the median baseband power of accepted local reference windows.
    KA9Q-reported DEMOD_SNR is intentionally not a classification dependency.
    """

    def __init__(self, config: ClassifierConfig | None = None) -> None:
        self.config = config or ClassifierConfig()

    def classify(self, input_data: ClassificationInput) -> Observation:
        signal = input_data.signal_window
        references = self._usable_references(input_data.reference_windows)
        signal_power = signal.median_baseband_power_db()

        if (
            signal_power is None
            or signal.coverage_ratio < self.config.minimum_signal_coverage_ratio
            or len(references) < self.config.minimum_reference_windows
        ):
            return self._observation(
                input_data=input_data,
                state=DetectionState.NO_DATA,
                derived_snr=None,
                quality=QualityLevel.INVALID,
                reason="insufficient_measurement_evidence",
            )

        reference_powers = [
            value
            for window in references
            if (value := window.median_baseband_power_db()) is not None
        ]
        if len(reference_powers) < self.config.minimum_reference_windows:
            return self._observation(
                input_data=input_data,
                state=DetectionState.NO_DATA,
                derived_snr=None,
                quality=QualityLevel.INVALID,
                reason="missing_reference_power",
            )

        reference_spread = max(reference_powers) - min(reference_powers)
        derived_snr = signal_power - median(reference_powers)
        quality = self._quality(signal, references, reference_spread)

        if reference_spread > self.config.maximum_reference_spread_db:
            return self._observation(
                input_data=input_data,
                state=DetectionState.INTERFERENCE,
                derived_snr=derived_snr,
                quality=QualityLevel.DEGRADED,
                reason="reference_channels_disagree",
            )

        state = self._state_for_snr(derived_snr, input_data.previous_state)
        reason = {
            DetectionState.NO_SIGNAL: "snr_below_signal_threshold",
            DetectionState.SIGNAL_PRESENT: "snr_above_signal_threshold",
            DetectionState.PROBABLE_BEACON: "snr_above_probable_threshold",
        }[state]
        return self._observation(
            input_data=input_data,
            state=state,
            derived_snr=derived_snr,
            quality=quality,
            reason=reason,
        )

    def _usable_references(
        self, windows: tuple[MeasurementWindow, ...]
    ) -> tuple[MeasurementWindow, ...]:
        return tuple(
            window
            for window in windows
            if window.coverage_ratio >= self.config.minimum_reference_coverage_ratio
            and window.median_baseband_power_db() is not None
        )

    def _state_for_snr(
        self, snr_db: float, previous_state: DetectionState | None
    ) -> DetectionState:
        if previous_state is DetectionState.PROBABLE_BEACON:
            if snr_db >= self.config.probable_beacon_exit_db:
                return DetectionState.PROBABLE_BEACON
        if previous_state is DetectionState.SIGNAL_PRESENT:
            if snr_db >= self.config.probable_beacon_enter_db:
                return DetectionState.PROBABLE_BEACON
            if snr_db >= self.config.signal_present_exit_db:
                return DetectionState.SIGNAL_PRESENT

        if snr_db >= self.config.probable_beacon_enter_db:
            return DetectionState.PROBABLE_BEACON
        if snr_db >= self.config.signal_present_enter_db:
            return DetectionState.SIGNAL_PRESENT
        return DetectionState.NO_SIGNAL

    def _quality(
        self,
        signal: MeasurementWindow,
        references: tuple[MeasurementWindow, ...],
        reference_spread_db: float,
    ) -> QualityLevel:
        minimum_coverage = min(
            [signal.coverage_ratio, *(window.coverage_ratio for window in references)]
        )
        if reference_spread_db > self.config.maximum_reference_spread_db:
            return QualityLevel.DEGRADED
        if minimum_coverage >= self.config.high_quality_coverage_ratio and len(references) >= 2:
            return QualityLevel.HIGH
        if minimum_coverage >= self.config.nominal_quality_coverage_ratio:
            return QualityLevel.NOMINAL
        return QualityLevel.DEGRADED

    @staticmethod
    def _observation(
        *,
        input_data: ClassificationInput,
        state: DetectionState,
        derived_snr: float | None,
        quality: QualityLevel,
        reason: str,
    ) -> Observation:
        signal = input_data.signal_window
        return Observation(
            beacon_id=input_data.beacon_id,
            window_start_utc=signal.start_utc,
            window_end_utc=signal.end_utc,
            detection_state=state,
            measurement_source=MeasurementSource.STATUS_ONLY,
            derived_local_snr_db=derived_snr,
            verification_snr_db=None,
            ka9q_reported_snr_db=None,
            measurement_quality=quality,
            verification_quality=QualityLevel.INVALID,
            identification_quality=QualityLevel.INVALID,
            verification_accepted=False,
            frequency_offset_hz=None,
            identified_callsign=None,
            reason_code=reason,
        )
