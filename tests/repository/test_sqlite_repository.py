from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum

import pytest

from ka9q_beacon_monitor.repository import SCHEMA_VERSION, SQLiteRepository


class State(StrEnum):
    PROBABLE = "probable_beacon"


@dataclass(frozen=True)
class ObservationRecord:
    beacon_id: str
    window_start_utc: datetime
    window_end_utc: datetime
    state: State
    snr_db: float | None


@dataclass(frozen=True)
class SummaryRecord:
    beacon_id: str
    interval_start_utc: datetime
    interval_end_utc: datetime
    observation_count: int


@pytest.fixture
def repository(tmp_path):
    with SQLiteRepository(tmp_path / "test.sqlite3") as repo:
        yield repo


def utc(second: int = 0) -> datetime:
    return datetime(2026, 8, 6, 12, 0, second, tzinfo=timezone.utc)


def observation(second: int = 0, snr: float = 7.0) -> ObservationRecord:
    return ObservationRecord("SK6VHF", utc(second), utc(second) + timedelta(seconds=10), State.PROBABLE, snr)


def summary(minute: int = 0) -> SummaryRecord:
    start = datetime(2026, 8, 6, 12, minute, tzinfo=timezone.utc)
    return SummaryRecord("SK6VHF", start, start + timedelta(minutes=30), 180)


def test_schema_is_created_and_versioned(repository):
    assert repository.schema_version == SCHEMA_VERSION
    assert repository.counts() == (0, 0)


def test_observation_round_trip(repository):
    repository.save_observation(observation())
    stored = repository.get_observation("SK6VHF", utc())
    assert stored["beacon_id"] == "SK6VHF"
    assert stored["state"] == "probable_beacon"
    assert stored["snr_db"] == 7.0


def test_observation_upsert_is_idempotent(repository):
    repository.save_observation(observation(snr=7.0))
    repository.save_observation(observation(snr=8.5))
    assert repository.counts() == (1, 0)
    assert repository.get_observation("SK6VHF", utc())["snr_db"] == 8.5


def test_summary_round_trip(repository):
    value = summary()
    repository.save_interval_summary(value)
    stored = repository.get_interval_summary("SK6VHF", value.interval_start_utc)
    assert stored["observation_count"] == 180


def test_summary_upsert_is_idempotent(repository):
    value = summary()
    repository.save_interval_summary(value)
    repository.save_interval_summary(SummaryRecord(value.beacon_id, value.interval_start_utc, value.interval_end_utc, 179))
    assert repository.counts() == (0, 1)
    assert repository.get_interval_summary("SK6VHF", value.interval_start_utc)["observation_count"] == 179


def test_lists_are_reverse_chronological(repository):
    repository.save_observation(observation(0))
    repository.save_observation(observation(20))
    rows = repository.list_observations("SK6VHF")
    assert rows[0]["window_start_utc"].endswith("20.000000Z")


def test_list_limit_must_be_positive(repository):
    with pytest.raises(ValueError):
        repository.list_observations("SK6VHF", limit=0)


def test_purge_before_removes_only_older_rows(repository):
    repository.save_observation(observation(0))
    repository.save_observation(observation(20))
    old_summary = summary(0)
    repository.save_interval_summary(old_summary)
    removed = repository.purge_before(utc(15))
    assert removed == (1, 0)
    assert repository.counts() == (1, 1)


def test_naive_datetime_is_rejected(repository):
    bad = ObservationRecord("SK6VHF", datetime(2026, 8, 6, 12), utc(10), State.PROBABLE, 7.0)
    with pytest.raises(ValueError):
        repository.save_observation(bad)


def test_missing_key_field_is_rejected(repository):
    with pytest.raises(ValueError):
        repository.save_observation({"window_start_utc": utc(), "window_end_utc": utc(10)})


def test_transaction_rolls_back_on_error(repository):
    with pytest.raises(RuntimeError):
        with repository.transaction() as connection:
            connection.execute(
                "INSERT INTO observations VALUES(?,?,?,?,?)",
                ("SK6VHF", "a", "b", "{}", "now"),
            )
            raise RuntimeError("boom")
    assert repository.counts() == (0, 0)


def test_context_manager_closes_cleanly(tmp_path):
    with SQLiteRepository(tmp_path / "db.sqlite3") as repo:
        repo.save_observation(observation())
    with SQLiteRepository(tmp_path / "db.sqlite3") as repo:
        assert repo.counts() == (1, 0)


def test_mixed_microsecond_timestamps_sort_chronologically(repository):
    whole = ObservationRecord(
        "SK6VHF",
        datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 6, 12, 0, 10, tzinfo=timezone.utc),
        State.PROBABLE,
        7.0,
    )
    fractional = ObservationRecord(
        "SK6VHF",
        datetime(2026, 8, 6, 12, 0, 0, 500000, tzinfo=timezone.utc),
        datetime(2026, 8, 6, 12, 0, 10, 500000, tzinfo=timezone.utc),
        State.PROBABLE,
        8.0,
    )
    repository.save_observation(whole)
    repository.save_observation(fractional)

    rows = repository.list_observations("SK6VHF")

    assert rows[0]["window_start_utc"].endswith("00.500000Z")
    assert rows[1]["window_start_utc"].endswith("00.000000Z")


def test_purge_before_handles_fractional_cutoff_within_same_second(repository):
    value = ObservationRecord(
        "SK6VHF",
        datetime(2026, 8, 6, 12, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 8, 6, 12, 0, 10, tzinfo=timezone.utc),
        State.PROBABLE,
        7.0,
    )
    repository.save_observation(value)

    removed = repository.purge_before(
        datetime(2026, 8, 6, 12, 0, 10, 500000, tzinfo=timezone.utc)
    )

    assert removed == (1, 0)
    assert repository.counts() == (0, 0)
