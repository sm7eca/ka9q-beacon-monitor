from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from ka9q_beacon_monitor.api import BeaconDefinition, create_app


class FakeRepository:
    schema_version = 1

    def __init__(self) -> None:
        self.observations = {
            ("SK6VHF", "2026-08-06T12:00:00.000000Z"): {
                "beacon_id": "SK6VHF",
                "window_start_utc": "2026-08-06T12:00:00.000000Z",
                "detection_state": "probable_beacon",
            }
        }
        self.summaries = {
            ("SK6VHF", "2026-08-06T12:00:00.000000Z"): {
                "beacon_id": "SK6VHF",
                "interval_start_utc": "2026-08-06T12:00:00.000000Z",
                "final_state": "audible",
            }
        }

    def counts(self) -> tuple[int, int]:
        return len(self.observations), len(self.summaries)

    @staticmethod
    def _key(value: datetime | str) -> str:
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
        return value

    def get_observation(self, beacon_id: str, window_start_utc: datetime | str) -> dict[str, Any] | None:
        return self.observations.get((beacon_id, self._key(window_start_utc)))

    def list_observations(self, beacon_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        return [value for (candidate, _), value in self.observations.items() if candidate == beacon_id][:limit]

    def get_interval_summary(self, beacon_id: str, interval_start_utc: datetime | str) -> dict[str, Any] | None:
        return self.summaries.get((beacon_id, self._key(interval_start_utc)))

    def list_interval_summaries(self, beacon_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        return [value for (candidate, _), value in self.summaries.items() if candidate == beacon_id][:limit]


def client() -> TestClient:
    app = create_app(
        FakeRepository(),
        beacons=[BeaconDefinition("SK6VHF", callsign="SK6VHF", frequency_hz=144_412_000.0)],
    )
    return TestClient(app)


def test_health_exposes_repository_state() -> None:
    response = client().get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["schema_version"] == 1
    assert body["observation_count"] == 1
    assert body["interval_summary_count"] == 1
    assert body["checked_at_utc"].endswith("Z")


def test_beacons_are_sorted_and_retrievable() -> None:
    response = client().get("/beacons")
    assert response.status_code == 200
    assert response.json()[0]["beacon_id"] == "SK6VHF"
    assert client().get("/beacons/SK6VHF").status_code == 200
    assert client().get("/beacons/UNKNOWN").status_code == 404


def test_observation_list_and_lookup() -> None:
    api = client()
    page = api.get("/beacons/SK6VHF/observations?limit=10")
    assert page.status_code == 200
    assert page.json()["count"] == 1
    item = api.get("/beacons/SK6VHF/observations/2026-08-06T12:00:00Z")
    assert item.status_code == 200
    assert item.json()["detection_state"] == "probable_beacon"


def test_summary_list_and_lookup() -> None:
    api = client()
    page = api.get("/beacons/SK6VHF/summaries")
    assert page.status_code == 200
    assert page.json()["items"][0]["final_state"] == "audible"
    item = api.get("/beacons/SK6VHF/summaries/2026-08-06T12:00:00Z")
    assert item.status_code == 200



def test_unknown_beacon_is_rejected_for_all_history_routes() -> None:
    api = client()
    assert api.get("/beacons/UNKNOWN/observations").status_code == 404
    assert api.get("/beacons/UNKNOWN/observations/2026-08-06T12:00:00Z").status_code == 404
    assert api.get("/beacons/UNKNOWN/summaries").status_code == 404
    assert api.get("/beacons/UNKNOWN/summaries/2026-08-06T12:00:00Z").status_code == 404

def test_timestamp_requires_utc() -> None:
    api = client()
    assert api.get("/beacons/SK6VHF/observations/not-a-date").status_code == 422
    assert api.get("/beacons/SK6VHF/observations/2026-08-06T12:00:00").status_code == 422
    assert api.get("/beacons/SK6VHF/observations/2026-08-06T14:00:00%2B02:00").status_code == 422


def test_limit_validation_is_enforced() -> None:
    api = client()
    assert api.get("/beacons/SK6VHF/observations?limit=0").status_code == 422
    assert api.get("/beacons/SK6VHF/observations?limit=1001").status_code == 422


def test_openapi_contains_public_routes() -> None:
    schema = client().get("/openapi.json").json()
    assert "/health" in schema["paths"]
    assert "/beacons/{beacon_id}/observations" in schema["paths"]
    assert "/beacons/{beacon_id}/summaries" in schema["paths"]


def test_duplicate_beacon_ids_are_rejected() -> None:
    repository = FakeRepository()
    try:
        create_app(repository, beacons=[BeaconDefinition("A"), BeaconDefinition("A")])
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("expected duplicate beacon IDs to be rejected")
