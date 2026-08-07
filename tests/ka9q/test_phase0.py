from datetime import datetime, timedelta, timezone
import hashlib

from ka9q_beacon_monitor.ka9q.phase0 import CaptureProvenance, analyze_status_capture
from ka9q_beacon_monitor.model import DemodMode, SampleQuality, StatusSample

UTC = timezone.utc


def _sample(t, power):
    return StatusSample(
        timestamp_utc=t,
        channel_id="sig",
        frequency_hz=144300000,
        baseband_power_db=power,
        noise_density_db_hz=-120.0,
        gain_db=None,
        output_level_db=None,
        headroom_db=None,
        demod_mode=DemodMode.LINEAR,
        pll_locked=None,
        sequence_number=None,
        sample_quality=SampleQuality.VALID,
    )


def _provenance(start, end, payload=b"real-capture-bytes"):
    return CaptureProvenance(
        radiod_version="ka9q-radio 1.2.3",
        radiod_revision="abc123",
        hardware_id="rx-site-a",
        network_endpoint="239.1.2.3:5004",
        capture_sha256=hashlib.sha256(payload).hexdigest(),
        capture_start_utc=start,
        capture_end_utc=end,
    )


def test_phase0_synthetic_capture_stays_unverified_without_provenance():
    t = datetime(2026, 8, 7, tzinfo=UTC)
    evidence = analyze_status_capture(
        [_sample(t, -80), _sample(t + timedelta(milliseconds=500), -79)],
        source="synthetic",
    )
    assert evidence.status == "UNVERIFIED"
    assert evidence.cadence_median_ms == 500
    assert evidence.baseband_power_span_db == 1


def test_phase0_caller_cannot_claim_real_capture_with_bare_flag_equivalent():
    t = datetime(2026, 8, 7, tzinfo=UTC)
    samples = [_sample(t, -80), _sample(t + timedelta(milliseconds=500), -79)]
    evidence = analyze_status_capture(samples, source="totally-made-up-not-real-hardware")
    assert evidence.status == "UNVERIFIED"
    assert evidence.provenance is None


def test_phase0_complete_provenance_and_matching_capture_can_verify():
    payload = b"real-capture-bytes"
    t = datetime(2026, 8, 7, tzinfo=UTC)
    samples = [_sample(t, -80), _sample(t + timedelta(milliseconds=500), -79)]
    provenance = _provenance(t, t + timedelta(seconds=1), payload)
    evidence = analyze_status_capture(
        samples,
        source="field-session-2026-08-07",
        provenance=provenance,
        capture_bytes=payload,
    )
    assert evidence.status == "VERIFIED_CAPTURE"
    assert evidence.provenance["radiod_revision"] == "abc123"


def test_phase0_checksum_mismatch_stays_unverified():
    payload = b"real-capture-bytes"
    t = datetime(2026, 8, 7, tzinfo=UTC)
    provenance = _provenance(t, t + timedelta(seconds=1), payload)
    evidence = analyze_status_capture(
        [_sample(t, -80)],
        source="field-session",
        provenance=provenance,
        capture_bytes=b"different-bytes",
    )
    assert evidence.status == "UNVERIFIED"


def test_phase0_sample_outside_provenance_interval_stays_unverified():
    payload = b"real-capture-bytes"
    t = datetime(2026, 8, 7, tzinfo=UTC)
    provenance = _provenance(t, t + timedelta(seconds=1), payload)
    evidence = analyze_status_capture(
        [_sample(t + timedelta(seconds=2), -80)],
        source="field-session",
        provenance=provenance,
        capture_bytes=payload,
    )
    assert evidence.status == "UNVERIFIED"


def test_phase0_empty_capture_stays_unverified_even_with_provenance():
    payload = b"real-capture-bytes"
    t = datetime(2026, 8, 7, tzinfo=UTC)
    evidence = analyze_status_capture(
        [],
        source="field-session",
        provenance=_provenance(t, t + timedelta(seconds=1), payload),
        capture_bytes=payload,
    )
    assert evidence.status == "UNVERIFIED"
