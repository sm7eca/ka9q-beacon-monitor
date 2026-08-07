from datetime import datetime, timezone
import json, os
from pathlib import Path
import stat
import pytest

from ka9q_beacon_monitor.ka9q.production_adapters import BridgeCommand, Ka9qStatusBridgeDecoder
from ka9q_beacon_monitor.ka9q.status_receiver import StatusDecodeError

UTC = timezone.utc

def _bridge(tmp_path: Path, payload: dict, *, exit_code: int = 0) -> Path:
    path = tmp_path / "bridge.py"
    path.write_text(
        "#!/usr/bin/env python3\nimport sys,json\nsys.stdin.buffer.read()\n"
        + (f"sys.exit({exit_code})\n" if exit_code else f"print({json.dumps(json.dumps(payload))})\n"),
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path

def test_status_bridge_maps_normalized_fields(tmp_path):
    bridge = _bridge(tmp_path, {"channel_id":"sig-1","frequency_hz":144300000.0,"baseband_power_db":-82.5,"noise_density_db_hz":-121.0,"demod_mode":"linear","sequence_number":4})
    decoder = Ka9qStatusBridgeDecoder(BridgeCommand((str(bridge),)))
    sample = decoder.decode(b"raw-ka9q-datagram", received_at_utc=datetime(2026,8,7,tzinfo=UTC), source=("127.0.0.1",5004))
    assert sample.channel_id == "sig-1"
    assert sample.baseband_power_db == -82.5
    assert sample.noise_density_db_hz == -121.0
    assert sample.sequence_number == 4
    assert sample.sample_quality.value == "valid"

def test_status_bridge_rejects_missing_identity(tmp_path):
    bridge = _bridge(tmp_path, {"frequency_hz":144300000})
    decoder = Ka9qStatusBridgeDecoder(BridgeCommand((str(bridge),)))
    with pytest.raises(StatusDecodeError):
        decoder.decode(b"x", received_at_utc=datetime(2026,8,7,tzinfo=UTC), source=None)

def test_status_bridge_nonzero_exit_is_decode_error(tmp_path):
    bridge = _bridge(tmp_path, {}, exit_code=3)
    decoder = Ka9qStatusBridgeDecoder(BridgeCommand((str(bridge),)))
    with pytest.raises(StatusDecodeError):
        decoder.decode(b"x", received_at_utc=datetime(2026,8,7,tzinfo=UTC), source=None)

@pytest.mark.asyncio
async def test_verification_bridge_maps_evidence_and_keeps_token_out_of_request(tmp_path, monkeypatch):
    from ka9q_beacon_monitor.ka9q.production_adapters import Ka9qVerificationBridgeBackend, VerificationBridgeConfig
    from ka9q_beacon_monitor.processing.verification_analyzer import VerificationRequest
    capture = tmp_path / "request.json"
    bridge = tmp_path / "verify.py"
    bridge.write_text(
        "#!/usr/bin/env python3\nimport json,os,sys,pathlib\n"
        f"p=pathlib.Path({str(capture)!r}); raw=sys.stdin.read(); p.write_text(raw)\n"
        "req=json.loads(raw)\n"
        "assert os.environ.get('KA9Q_VERIFICATION_TOKEN') == 'secret-value'\n"
        "print(json.dumps({'beacon_id':req['beacon_id'],'window_start_utc':req['window_start_utc'],'window_end_utc':req['window_end_utc'],'measurement_source':'verified_cw','cw_detected':True,'verification_snr_db':8.5,'frequency_offset_hz':1.2,'verification_quality':'nominal','identification_quality':'nominal','identified_callsign':'SK6ABC'}))\n",
        encoding="utf-8",
    )
    bridge.chmod(bridge.stat().st_mode | stat.S_IXUSR)
    backend = Ka9qVerificationBridgeBackend(VerificationBridgeConfig(BridgeCommand((str(bridge),)), token="secret-value"))
    start=datetime(2026,8,7,10,0,tzinfo=UTC)
    request=VerificationRequest(beacon_id="b1", window_start_utc=start, window_end_utc=start.replace(minute=1), expected_callsign="SK6ABC")
    evidence=await backend.analyze(request)
    assert evidence.identified_callsign == "SK6ABC"
    assert "secret-value" not in capture.read_text()

@pytest.mark.asyncio
async def test_verification_bridge_nonzero_exit_is_backend_error(tmp_path):
    from ka9q_beacon_monitor.ka9q.production_adapters import Ka9qVerificationBridgeBackend, VerificationBridgeConfig
    from ka9q_beacon_monitor.processing.verification_analyzer import VerificationRequest
    bridge = _bridge(tmp_path, {}, exit_code=4)
    backend = Ka9qVerificationBridgeBackend(VerificationBridgeConfig(BridgeCommand((str(bridge),))))
    start=datetime(2026,8,7,10,0,tzinfo=UTC)
    request=VerificationRequest(beacon_id="b1", window_start_utc=start, window_end_utc=start.replace(minute=1))
    with pytest.raises(RuntimeError):
        await backend.analyze(request)

def test_status_bridge_missing_timestamp_uses_receiver_arrival_time(tmp_path):
    bridge = _bridge(tmp_path, {"channel_id":"sig-1","frequency_hz":144300000.0,"baseband_power_db":-82.5,"noise_density_db_hz":-121.0})
    decoder = Ka9qStatusBridgeDecoder(BridgeCommand((str(bridge),)))
    arrival = datetime(2026,8,7,12,0,tzinfo=UTC)
    sample = decoder.decode(b"x", received_at_utc=arrival, source=None)
    assert sample.timestamp_utc == arrival


def test_status_bridge_invalid_present_timestamp_is_rejected(tmp_path):
    bridge = _bridge(tmp_path, {"channel_id":"sig-1","frequency_hz":144300000.0,"baseband_power_db":-82.5,"noise_density_db_hz":-121.0,"timestamp_utc":"not-a-valid-timestamp"})
    decoder = Ka9qStatusBridgeDecoder(BridgeCommand((str(bridge),)))
    with pytest.raises(StatusDecodeError):
        decoder.decode(b"x", received_at_utc=datetime(2026,8,7,12,0,tzinfo=UTC), source=None)
