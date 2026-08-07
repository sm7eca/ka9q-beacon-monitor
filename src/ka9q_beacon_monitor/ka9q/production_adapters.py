"""Production-facing KA9Q adapter boundaries for M5.4.

KA9Q's metadata wire protocol is version-sensitive.  This module therefore does
not duplicate that binary grammar in Python.  A deployment supplies a small
bridge executable built/tested against the selected ka9q-radio release.  The
bridge accepts one raw status datagram on stdin and emits one normalized JSON
object on stdout.  This keeps version-specific parsing behind the already
approved StatusDatagramDecoder boundary while making failure handling explicit
and testable.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ka9q_beacon_monitor.ka9q.status_receiver import StatusDecodeError
from ka9q_beacon_monitor.model import DemodMode, SampleQuality, StatusSample
from ka9q_beacon_monitor.processing.verification_analyzer import (
    VerificationBackend,
    VerificationEvidence,
    VerificationRequest,
)
from ka9q_beacon_monitor.model import MeasurementSource, QualityLevel


class AdapterConfigurationError(ValueError):
    """Raised before startup when a production adapter is not usable."""


@dataclass(frozen=True, slots=True)
class BridgeCommand:
    argv: tuple[str, ...]
    timeout_seconds: float = 2.0

    def __post_init__(self) -> None:
        if not self.argv or not all(isinstance(part, str) and part for part in self.argv):
            raise AdapterConfigurationError("bridge argv must contain non-empty strings")
        if self.timeout_seconds <= 0:
            raise AdapterConfigurationError("bridge timeout_seconds must be positive")

    @property
    def executable(self) -> str:
        return self.argv[0]

    def validate_executable(self) -> None:
        exe = Path(self.executable)
        if exe.is_absolute() or "/" in self.executable:
            if not exe.is_file():
                raise AdapterConfigurationError(f"bridge executable not found: {exe}")


class Ka9qStatusBridgeDecoder:
    """Decode a raw radiod status datagram through a selected-release bridge.

    The bridge JSON schema is intentionally narrow and maps directly to
    StatusSample. Unknown bridge fields are ignored diagnostically; required
    normalized fields are validated here.
    """

    def __init__(self, command: BridgeCommand) -> None:
        command.validate_executable()
        self.command = command

    def decode(
        self,
        datagram: bytes,
        *,
        received_at_utc: datetime,
        source: tuple[str, int] | None,
    ) -> StatusSample:
        import subprocess

        if received_at_utc.tzinfo is None or received_at_utc.utcoffset() != timezone.utc.utcoffset(received_at_utc):
            raise StatusDecodeError("received_at_utc must be timezone-aware UTC")
        try:
            completed = subprocess.run(
                self.command.argv,
                input=datagram,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.command.timeout_seconds,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise StatusDecodeError("KA9Q status bridge execution failed") from exc
        if completed.returncode != 0:
            raise StatusDecodeError(
                f"KA9Q status bridge rejected datagram (exit {completed.returncode})"
            )
        try:
            payload = json.loads(completed.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StatusDecodeError("KA9Q status bridge returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise StatusDecodeError("KA9Q status bridge JSON root must be an object")
        return self._sample_from_payload(payload, received_at_utc)

    @staticmethod
    def _sample_from_payload(payload: Mapping[str, Any], received_at_utc: datetime) -> StatusSample:
        required = ("channel_id", "frequency_hz")
        missing = [name for name in required if name not in payload]
        if missing:
            raise StatusDecodeError("bridge output missing required field(s): " + ", ".join(missing))
        try:
            baseband = _optional_float(payload.get("baseband_power_db"))
            noise = _optional_float(payload.get("noise_density_db_hz"))
            quality_raw = payload.get("sample_quality")
            if quality_raw is None:
                quality = SampleQuality.VALID if baseband is not None and noise is not None else SampleQuality.PARTIAL
            else:
                quality = SampleQuality(str(quality_raw).lower())
            mode = DemodMode(str(payload.get("demod_mode", "unknown")).lower())
            timestamp = _parse_optional_utc(payload.get("timestamp_utc")) or received_at_utc
            return StatusSample(
                timestamp_utc=timestamp,
                channel_id=str(payload["channel_id"]),
                frequency_hz=float(payload["frequency_hz"]),
                baseband_power_db=baseband,
                noise_density_db_hz=noise,
                gain_db=_optional_float(payload.get("gain_db")),
                output_level_db=_optional_float(payload.get("output_level_db")),
                headroom_db=_optional_float(payload.get("headroom_db")),
                demod_mode=mode,
                pll_locked=_optional_bool(payload.get("pll_locked")),
                sequence_number=_optional_int(payload.get("sequence_number")),
                sample_quality=quality,
            )
        except (TypeError, ValueError) as exc:
            raise StatusDecodeError("bridge output violates StatusSample contract") from exc


@dataclass(frozen=True, slots=True)
class VerificationBridgeConfig:
    command: BridgeCommand
    token: str | None = None


class Ka9qVerificationBridgeBackend(VerificationBackend):
    """Verification backend using a deployment-provided PCM/IQ bridge command."""

    def __init__(self, config: VerificationBridgeConfig) -> None:
        config.command.validate_executable()
        self.config = config

    async def analyze(self, request: VerificationRequest) -> VerificationEvidence:
        body = {
            "beacon_id": request.beacon_id,
            "window_start_utc": _format_utc(request.window_start_utc),
            "window_end_utc": _format_utc(request.window_end_utc),
            "expected_callsign": request.expected_callsign,
        }
        env = None
        if self.config.token is not None:
            import os
            env = dict(os.environ)
            env["KA9Q_VERIFICATION_TOKEN"] = self.config.token
        proc = await asyncio.create_subprocess_exec(
            *self.config.command.argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        try:
            stdout, _stderr = await asyncio.wait_for(
                proc.communicate(json.dumps(body, separators=(",", ":")).encode("utf-8")),
                timeout=self.config.command.timeout_seconds,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError("KA9Q verification bridge timed out")
        if proc.returncode != 0:
            raise RuntimeError(f"KA9Q verification bridge failed (exit {proc.returncode})")
        try:
            payload = json.loads(stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("KA9Q verification bridge returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("KA9Q verification bridge JSON root must be an object")
        try:
            return VerificationEvidence(
                beacon_id=str(payload["beacon_id"]),
                window_start_utc=_parse_required_utc(payload["window_start_utc"]),
                window_end_utc=_parse_required_utc(payload["window_end_utc"]),
                measurement_source=MeasurementSource(str(payload["measurement_source"]).lower()),
                cw_detected=bool(payload["cw_detected"]),
                verification_snr_db=_optional_float(payload.get("verification_snr_db")),
                frequency_offset_hz=_optional_float(payload.get("frequency_offset_hz")),
                verification_quality=QualityLevel(str(payload["verification_quality"]).lower()),
                identification_quality=QualityLevel(str(payload["identification_quality"]).lower()),
                identified_callsign=(str(payload["identified_callsign"]) if payload.get("identified_callsign") is not None else None),
                reason_code=str(payload.get("reason_code", "verification_complete")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("KA9Q verification bridge output violates evidence contract") from exc


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_bool(value: Any) -> bool | None:
    if value is None or isinstance(value, bool):
        return value
    raise ValueError("boolean field must be true, false, or null")


def _parse_optional_utc(value: Any) -> datetime | None:
    return None if value is None else _parse_required_utc(value)


def _parse_required_utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("UTC timestamp must be a string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("timestamp must be UTC")
    return parsed.astimezone(timezone.utc)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
