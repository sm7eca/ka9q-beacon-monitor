"""Phase-0 evidence analysis for real radiod captures.

Synthetic fixtures may exercise the analyzer, but evidence can only be marked
VERIFIED_CAPTURE when a structured provenance record is complete and the
supplied capture bytes match the recorded SHA-256 checksum.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import re
from statistics import median
from typing import Iterable

from ka9q_beacon_monitor.model import StatusSample

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _is_utc(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() == timezone.utc.utcoffset(value)


@dataclass(frozen=True, slots=True)
class CaptureProvenance:
    radiod_version: str
    radiod_revision: str
    hardware_id: str
    network_endpoint: str
    capture_sha256: str
    capture_start_utc: datetime
    capture_end_utc: datetime

    def __post_init__(self) -> None:
        text_fields = {
            "radiod_version": self.radiod_version,
            "radiod_revision": self.radiod_revision,
            "hardware_id": self.hardware_id,
            "network_endpoint": self.network_endpoint,
        }
        for name, value in text_fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(self.capture_sha256, str) or not _SHA256_RE.fullmatch(self.capture_sha256.lower()):
            raise ValueError("capture_sha256 must be a 64-character hexadecimal SHA-256")
        if not _is_utc(self.capture_start_utc) or not _is_utc(self.capture_end_utc):
            raise ValueError("capture interval must use timezone-aware UTC timestamps")
        if self.capture_end_utc < self.capture_start_utc:
            raise ValueError("capture_end_utc must not precede capture_start_utc")

    def to_dict(self) -> dict[str, object]:
        return {
            "radiod_version": self.radiod_version,
            "radiod_revision": self.radiod_revision,
            "hardware_id": self.hardware_id,
            "network_endpoint": self.network_endpoint,
            "capture_sha256": self.capture_sha256.lower(),
            "capture_start_utc": _format_utc(self.capture_start_utc),
            "capture_end_utc": _format_utc(self.capture_end_utc),
        }


@dataclass(frozen=True, slots=True)
class Phase0Evidence:
    source: str
    captured_at_utc: str
    sample_count: int
    cadence_median_ms: float | None
    cadence_min_ms: float | None
    cadence_max_ms: float | None
    fields_present: tuple[str, ...]
    baseband_power_span_db: float | None
    status: str
    provenance: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def analyze_status_capture(
    samples: Iterable[StatusSample],
    *,
    source: str,
    provenance: CaptureProvenance | None = None,
    capture_bytes: bytes | None = None,
) -> Phase0Evidence:
    """Analyze normalized status samples without manufacturing field evidence.

    VERIFIED_CAPTURE requires all of the following:
    - at least one sample;
    - structured provenance;
    - actual capture bytes supplied to this call;
    - SHA-256 of those bytes matching provenance.capture_sha256;
    - all sample timestamps contained by the provenance UTC interval.

    This proves artifact integrity and provenance completeness, not physical
    truth by itself. Field operators remain responsible for ensuring the bytes
    came from the recorded radiod/hardware session.
    """
    ordered = sorted(samples, key=lambda sample: sample.timestamp_utc)
    deltas = [
        (right.timestamp_utc - left.timestamp_utc).total_seconds() * 1000.0
        for left, right in zip(ordered, ordered[1:])
        if right.timestamp_utc > left.timestamp_utc
    ]
    fields: set[str] = set()
    powers: list[float] = []
    for sample in ordered:
        for name in (
            "baseband_power_db",
            "noise_density_db_hz",
            "gain_db",
            "output_level_db",
            "headroom_db",
            "pll_locked",
            "sequence_number",
        ):
            if getattr(sample, name) is not None:
                fields.add(name)
        if sample.baseband_power_db is not None:
            powers.append(sample.baseband_power_db)

    span = max(powers) - min(powers) if len(powers) >= 2 else None
    captured_at = ordered[-1].timestamp_utc if ordered else datetime.now(timezone.utc)

    verified = False
    if ordered and provenance is not None and capture_bytes is not None:
        checksum_matches = hashlib.sha256(capture_bytes).hexdigest() == provenance.capture_sha256.lower()
        interval_contains_samples = (
            provenance.capture_start_utc <= ordered[0].timestamp_utc
            and ordered[-1].timestamp_utc <= provenance.capture_end_utc
        )
        verified = checksum_matches and interval_contains_samples

    return Phase0Evidence(
        source=source,
        captured_at_utc=_format_utc(captured_at),
        sample_count=len(ordered),
        cadence_median_ms=median(deltas) if deltas else None,
        cadence_min_ms=min(deltas) if deltas else None,
        cadence_max_ms=max(deltas) if deltas else None,
        fields_present=tuple(sorted(fields)),
        baseband_power_span_db=span,
        status="VERIFIED_CAPTURE" if verified else "UNVERIFIED",
        provenance=provenance.to_dict() if provenance is not None else None,
    )


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
