# KA9Q Beacon Monitor

KA9Q Beacon Monitor is a Linux service for continuous monitoring of selected VHF radio beacons using KA9Q-radio as the radio/channelization layer. The application provides persistence, JSON APIs, operational diagnostics and a browser-based beacon overview.

## Current status

**M5 Production Readiness is software-approved through M5.7.4.**

- M5.7 Production Deployment Integration: **APPROVED**
- Full automated test suite: **223/223 passed**
- Raspberry Pi 5 deployment verified on Debian GNU/Linux 13 (Trixie), ARM64
- systemd service deployment verified
- Web UI verified from another host on the LAN
- `/ops/live`, `/ops/ready`, `/ops/diagnostics` and `/api/health` verified
- Explicit **no-SDR** deployment mode verified on real Raspberry Pi 5 hardware
- Build identity via `KA9Q_BUILD_*` verified in systemd operation

The no-SDR mode validates software and deployment only. It does not create synthetic radio observations or count as KA9Q/SDR field evidence.

## Phase 0 status

Phase 0 radio evidence remains **UNVERIFIED** for P0-A-001 through P0-A-003.

The next project step is hardware-backed validation with an SDR connected to KA9Q `radiod`. Phase 0 must verify the installed KA9Q version and actual radio/status behavior before the radio integration is considered field-validated.

## Raspberry Pi 5 deployment

Verified deployment locations:

```text
/opt/ka9q-beacon-monitor          application repository
/etc/ka9q-beacon-monitor          runtime/deployment configuration
/var/lib/ka9q-beacon-monitor      persistent application data
```

Useful operational commands:

```bash
systemctl status ka9q-beacon-monitor --no-pager
sudo journalctl -u ka9q-beacon-monitor -n 100 --no-pager
sudo systemctl restart ka9q-beacon-monitor
```

Health checks:

```bash
curl -s http://127.0.0.1:8000/ops/live
curl -s http://127.0.0.1:8000/ops/ready
curl -s http://127.0.0.1:8000/ops/diagnostics
curl -s http://127.0.0.1:8000/api/health
```

Web UI:

```text
http://<pi-address>:8000/
```

In no-SDR mode, an empty beacon overview and zero radio-observation counters are expected.

## Deployment configuration

Repository-controlled Pi/no-SDR examples are provided under `deploy/`. Production configuration is installed under `/etc/ka9q-beacon-monitor`.

M5.7 provides the concrete application factory and CLI-to-factory composition required for reproducible systemd startup. Environment-variable validation remains fail-closed for unknown `KA9Q_*` names, while legitimate observability build-identity variables use the common environment registry.

## Web interface

The current browser interface is a monitoring/status interface. Web-based dynamic beacon administration is **not implemented**.

Investigation of dynamic beacon/frequency administration is deliberately deferred until KA9Q control behavior is verified against the installed `radiod` version during hardware-backed work.

## KA9Q integration boundary

KA9Q `radiod` is installed and configured separately from Beacon Monitor. The application consumes KA9Q-provided radio/status data rather than duplicating KA9Q's low-level DSP and channelization responsibilities.

Exact KA9Q status/control fields and hardware behavior must be verified against the installed KA9Q version and real SDR data before those assumptions are promoted to verified field behavior.

## Development and tests

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e .
python3 -m pytest -q
```

Current approved baseline:

```text
223 passed
```

## Review and evidence discipline

Software review approval and hardware field evidence are tracked separately. A successful automated test, no-SDR smoke test or systemd deployment must not change a Phase 0 field assumption from `UNVERIFIED` without the required real KA9Q/SDR evidence.

Review milestone packaging and evidence tracking are maintained in `tools/review_milestones.json` and the repository review/AKB material.

## Next step

Connect the SDR and execute Phase 0 against the installed KA9Q `radiod` environment. The immediate goal is reproducible evidence for P0-A-001, P0-A-002 and P0-A-003 while preserving the verified M5.7.4 deployment baseline.
