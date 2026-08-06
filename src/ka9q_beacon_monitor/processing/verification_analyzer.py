"""Selective verification orchestration for probable beacon observations.

The module owns verification policy and result application. Low-level PCM/IQ/CW
analysis is supplied by an injected backend, keeping transport and DSP adapters
replaceable and independently testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from typing import Awaitable, Protocol

from ka9q_beacon_monitor.model import (
    DetectionState,
    MeasurementSource,
    Observation,
    QualityLevel,
)


@dataclass(frozen=True, slots=True)
class VerificationPolicy:
    """Acceptance gates for verification evidence."""

    minimum_verification_snr_db: float = 3.0
    maximum_abs_frequency_offset_hz: float = 20.0
    require_callsign_for_morse: bool = True

    def __post_init__(self) -> None:
        if not isfinite(self.minimum_verification_snr_db):
            raise ValueError("minimum_verification_snr_db must be finite")
        if (
            not isfinite(self.maximum_abs_frequency_offset_hz)
            or self.maximum_abs_frequency_offset_hz < 0
        ):
            raise ValueError(
                "maximum_abs_frequency_offset_hz must be finite and non-negative"
            )


@dataclass(frozen=True, slots=True)
class VerificationRequest:
    """One selective verification request for one Observation."""

    beacon_id: str
    window_start_utc: datetime
    window_end_utc: datetime
    expected_callsign: str | None = None

    @classmethod
    def from_observation(
        cls, observation: Observation, *, expected_callsign: str | None = None
    ) -> "VerificationRequest":
        return cls(
            beacon_id=observation.beacon_id,
            window_start_utc=observation.window_start_utc,
            window_end_utc=observation.window_end_utc,
            expected_callsign=expected_callsign,
        )

    def __post_init__(self) -> None:
        if not self.beacon_id.strip():
            raise ValueError("beacon_id must not be empty")
        if self.window_end_utc <= self.window_start_utc:
            raise ValueError("window_end_utc must be after window_start_utc")
        if self.expected_callsign is not None and not self.expected_callsign.strip():
            raise ValueError("expected_callsign must be non-empty when present")


@dataclass(frozen=True, slots=True)
class VerificationEvidence:
    """Normalized result returned by a verification backend."""

    beacon_id: str
    window_start_utc: datetime
    window_end_utc: datetime
    measurement_source: MeasurementSource
    cw_detected: bool
    verification_snr_db: float | None
    frequency_offset_hz: float | None
    verification_quality: QualityLevel
    identification_quality: QualityLevel
    identified_callsign: str | None = None
    reason_code: str = "verification_complete"

    def __post_init__(self) -> None:
        if not self.beacon_id.strip():
            raise ValueError("beacon_id must not be empty")
        if self.window_end_utc <= self.window_start_utc:
            raise ValueError("window_end_utc must be after window_start_utc")
        if self.measurement_source is MeasurementSource.STATUS_ONLY:
            raise ValueError("verification evidence cannot use STATUS_ONLY")
        if not self.reason_code.strip():
            raise ValueError("reason_code must not be empty")
        for name in ("verification_snr_db", "frequency_offset_hz"):
            value = getattr(self, name)
            if value is not None and not isfinite(value):
                raise ValueError(f"{name} must be finite when present")
        if self.identified_callsign is not None and not self.identified_callsign.strip():
            raise ValueError("identified_callsign must be non-empty when present")


class VerificationBackend(Protocol):
    """Replaceable low-level verification provider."""

    def analyze(
        self, request: VerificationRequest
    ) -> Awaitable[VerificationEvidence]: ...


class VerificationAnalyzer:
    """Apply selective verification policy to status-only observations."""

    def __init__(
        self,
        backend: VerificationBackend,
        policy: VerificationPolicy | None = None,
    ) -> None:
        self._backend = backend
        self.policy = policy or VerificationPolicy()

    async def verify(
        self,
        observation: Observation,
        *,
        expected_callsign: str | None = None,
    ) -> Observation:
        """Verify one probable beacon observation.

        Non-probable and already verified observations are returned unchanged.
        Backend failures are isolated and represented as a rejected verification
        result rather than escaping into the runtime pipeline.
        """

        if observation.detection_state is not DetectionState.PROBABLE_BEACON:
            return observation

        request = VerificationRequest.from_observation(
            observation, expected_callsign=expected_callsign
        )
        try:
            evidence = await self._backend.analyze(request)
        except Exception:
            return self._rejected(
                observation,
                verification_quality=QualityLevel.INVALID,
                identification_quality=QualityLevel.INVALID,
                reason_code="verification_backend_error",
            )

        mismatch = self._identity_mismatch(request, evidence)
        if mismatch is not None:
            return self._rejected(
                observation,
                verification_quality=QualityLevel.INVALID,
                identification_quality=QualityLevel.INVALID,
                reason_code=mismatch,
            )

        rejection = self._rejection_reason(request, evidence)
        if rejection is not None:
            return self._rejected(
                observation,
                verification_snr_db=evidence.verification_snr_db,
                frequency_offset_hz=evidence.frequency_offset_hz,
                verification_quality=evidence.verification_quality,
                identification_quality=evidence.identification_quality,
                identified_callsign=evidence.identified_callsign,
                reason_code=rejection,
            )

        return Observation(
            beacon_id=observation.beacon_id,
            window_start_utc=observation.window_start_utc,
            window_end_utc=observation.window_end_utc,
            detection_state=DetectionState.VERIFIED_BEACON,
            measurement_source=evidence.measurement_source,
            derived_local_snr_db=observation.derived_local_snr_db,
            verification_snr_db=evidence.verification_snr_db,
            ka9q_reported_snr_db=observation.ka9q_reported_snr_db,
            measurement_quality=observation.measurement_quality,
            verification_quality=evidence.verification_quality,
            identification_quality=evidence.identification_quality,
            verification_accepted=True,
            frequency_offset_hz=evidence.frequency_offset_hz,
            identified_callsign=evidence.identified_callsign,
            reason_code="verification_accepted",
        )

    @staticmethod
    def _identity_mismatch(
        request: VerificationRequest, evidence: VerificationEvidence
    ) -> str | None:
        if evidence.beacon_id != request.beacon_id:
            return "verification_beacon_mismatch"
        if (
            evidence.window_start_utc != request.window_start_utc
            or evidence.window_end_utc != request.window_end_utc
        ):
            return "verification_window_mismatch"
        return None

    def _rejection_reason(
        self, request: VerificationRequest, evidence: VerificationEvidence
    ) -> str | None:
        if not evidence.cw_detected:
            return "cw_not_detected"
        if evidence.verification_snr_db is None:
            return "verification_snr_missing"
        if evidence.verification_snr_db < self.policy.minimum_verification_snr_db:
            return "verification_snr_below_threshold"
        if evidence.frequency_offset_hz is None:
            return "frequency_offset_missing"
        if (
            abs(evidence.frequency_offset_hz)
            > self.policy.maximum_abs_frequency_offset_hz
        ):
            return "frequency_offset_out_of_range"
        if evidence.verification_quality in (
            QualityLevel.INVALID,
            QualityLevel.DEGRADED,
        ):
            return "verification_quality_insufficient"

        callsign = self._normalized(evidence.identified_callsign)
        expected = self._normalized(request.expected_callsign)
        if (
            evidence.measurement_source is MeasurementSource.VERIFIED_MORSE
            and self.policy.require_callsign_for_morse
            and callsign is None
        ):
            return "morse_callsign_missing"
        if expected is not None and callsign != expected:
            return "callsign_mismatch"
        return None

    @staticmethod
    def _normalized(value: str | None) -> str | None:
        if value is None:
            return None
        return "".join(value.upper().split())

    @staticmethod
    def _rejected(
        observation: Observation,
        *,
        verification_snr_db: float | None = None,
        frequency_offset_hz: float | None = None,
        verification_quality: QualityLevel = QualityLevel.INVALID,
        identification_quality: QualityLevel = QualityLevel.INVALID,
        identified_callsign: str | None = None,
        reason_code: str,
    ) -> Observation:
        return Observation(
            beacon_id=observation.beacon_id,
            window_start_utc=observation.window_start_utc,
            window_end_utc=observation.window_end_utc,
            detection_state=DetectionState.PROBABLE_BEACON,
            measurement_source=MeasurementSource.STATUS_ONLY,
            derived_local_snr_db=observation.derived_local_snr_db,
            verification_snr_db=verification_snr_db,
            ka9q_reported_snr_db=observation.ka9q_reported_snr_db,
            measurement_quality=observation.measurement_quality,
            verification_quality=verification_quality,
            identification_quality=identification_quality,
            verification_accepted=False,
            frequency_offset_hz=frequency_offset_hz,
            identified_callsign=identified_callsign,
            reason_code=reason_code,
        )
