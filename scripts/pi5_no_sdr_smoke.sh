#!/bin/sh
set -eu
BASE_URL="${1:-http://127.0.0.1:8000}"

curl -fsS "$BASE_URL/ops/live" >/dev/null
curl -fsS "$BASE_URL/ops/ready" >/dev/null
curl -fsS "$BASE_URL/ops/diagnostics" >/dev/null
curl -fsS "$BASE_URL/ops/metrics" >/dev/null
curl -fsS "$BASE_URL/api/health" >/dev/null
curl -fsS "$BASE_URL/api/beacons" >/dev/null
curl -fsS "$BASE_URL/" >/dev/null
printf '%s\n' "KA9Q Beacon Monitor no-SDR smoke test: PASS"
