"""Deterministic replay support for M5.5 acceptance validation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter
from typing import Iterable

from ka9q_beacon_monitor.model import DemodMode, SampleQuality, StatusSample


@dataclass(frozen=True, slots=True)
class ReplayReport:
    samples_submitted: int
    observations_persisted: int
    summaries_persisted: int
    pipeline_errors: int
    elapsed_seconds: float

    @property
    def samples_per_second(self) -> float:
        if self.elapsed_seconds <= 0:
            return float("inf")
        return self.samples_submitted / self.elapsed_seconds


async def replay_status_samples(runtime, samples: Iterable[StatusSample]) -> ReplayReport:
    """Replay normalized samples through the approved runtime composition root.

    Input is sorted by event time and channel for deterministic execution. The
    function does not bypass MeasurementBuilder, Classifier, VerificationAnalyzer,
    Repository, or IntervalAggregator.
    """
    ordered = sorted(samples, key=lambda item: (item.timestamp_utc, item.channel_id))
    before_observations = runtime.counters.observations_persisted
    before_summaries = runtime.counters.summaries_persisted
    before_errors = runtime.counters.pipeline_errors
    started = perf_counter()
    for sample in ordered:
        await runtime.ingest_sample(sample)
    if ordered:
        await runtime.advance_time(ordered[-1].timestamp_utc.replace(microsecond=0))
    await runtime.measurement_builder.flush()
    await runtime.aggregator.flush()
    elapsed = perf_counter() - started
    return ReplayReport(
        samples_submitted=len(ordered),
        observations_persisted=runtime.counters.observations_persisted - before_observations,
        summaries_persisted=runtime.counters.summaries_persisted - before_summaries,
        pipeline_errors=runtime.counters.pipeline_errors - before_errors,
        elapsed_seconds=elapsed,
    )


def load_status_replay(path: str | Path) -> tuple[StatusSample, ...]:
    """Load repository-controlled JSONL replay data into validated StatusSample objects."""
    result: list[StatusSample] = []
    for line_number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        try:
            payload = json.loads(raw)
            timestamp = datetime.fromisoformat(str(payload["timestamp_utc"]).replace("Z", "+00:00"))
            if timestamp.tzinfo is None or timestamp.utcoffset() != timezone.utc.utcoffset(timestamp):
                raise ValueError("timestamp must be UTC")
            result.append(StatusSample(
                timestamp_utc=timestamp.astimezone(timezone.utc),
                channel_id=str(payload["channel_id"]),
                frequency_hz=float(payload["frequency_hz"]),
                baseband_power_db=_optional_float(payload.get("baseband_power_db")),
                noise_density_db_hz=_optional_float(payload.get("noise_density_db_hz")),
                gain_db=_optional_float(payload.get("gain_db")),
                output_level_db=_optional_float(payload.get("output_level_db")),
                headroom_db=_optional_float(payload.get("headroom_db")),
                pll_locked=payload.get("pll_locked"),
                demod_mode=DemodMode(str(payload.get("demod_mode", "linear")).lower()),
                sequence_number=(None if payload.get("sequence_number") is None else int(payload["sequence_number"])),
                sample_quality=SampleQuality(str(payload.get("sample_quality", "valid")).lower()),
            ))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid replay record at line {line_number}") from exc
    if not result:
        raise ValueError("replay input must contain at least one sample")
    return tuple(result)


def _optional_float(value):
    return None if value is None else float(value)
