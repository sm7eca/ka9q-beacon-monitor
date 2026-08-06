import sqlite3

import pytest

from ka9q_beacon_monitor.repository.schema import (
    REQUIRED_TABLES,
    SCHEMA_VERSION,
    apply_schema,
    list_tables,
    validate_schema,
)


def connection() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys = ON")
    return db


def seed_beacon(db: sqlite3.Connection) -> None:
    db.execute(
        "INSERT INTO beacons VALUES (?, ?, ?, ?, ?, ?)",
        ("sk6vhf", "SK6VHF", 144412000, 1, "2026-08-06T12:00:00Z", "2026-08-06T12:00:00Z"),
    )


def observation_values() -> tuple[object, ...]:
    return (
        "sk6vhf", "2026-08-06T12:00:00Z", "2026-08-06T12:00:10Z",
        "signal_present", "status_only", 7.0, None, None,
        "nominal", "invalid", "invalid", 0, None, None,
        "stable_signal", "2026-08-06T12:00:10Z",
    )


def test_apply_and_validate_schema() -> None:
    db = connection()
    apply_schema(db)
    assert REQUIRED_TABLES <= list_tables(db)
    assert db.execute("SELECT MAX(version) FROM schema_version").fetchone()[0] == SCHEMA_VERSION
    assert validate_schema(db) == []


def test_apply_schema_is_idempotent() -> None:
    db = connection()
    apply_schema(db)
    apply_schema(db)
    assert validate_schema(db) == []
    assert db.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == 1


def test_observation_unique_key_prevents_duplicates() -> None:
    db = connection()
    apply_schema(db)
    seed_beacon(db)
    sql = """INSERT INTO observations (
        beacon_id, window_start_utc, window_end_utc, detection_state,
        measurement_source, derived_local_snr_db, verification_snr_db,
        ka9q_reported_snr_db, measurement_quality, verification_quality,
        identification_quality, verification_accepted, frequency_offset_hz,
        identified_callsign, reason_code, created_at_utc
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    db.execute(sql, observation_values())
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(sql, observation_values())


def test_summary_primary_key_supports_upsert() -> None:
    db = connection()
    apply_schema(db)
    seed_beacon(db)
    sql = """INSERT INTO interval_summaries VALUES (
        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
    ) ON CONFLICT(beacon_id, interval_start_utc) DO UPDATE SET
        observation_count=excluded.observation_count,
        updated_at_utc=excluded.updated_at_utc"""
    first = ("sk6vhf", "2026-08-06T12:00:00Z", "2026-08-06T12:30:00Z", 180, 170, 165, 10, 100, 91.7, 60.6, 8.0, 18.0, 1.0, "AUDIBLE", "valid", "2026-08-06T12:30:05Z")
    second = list(first)
    second[4] = 171
    second[-1] = "2026-08-06T12:31:00Z"
    db.execute(sql, first)
    db.execute(sql, tuple(second))
    assert db.execute("SELECT observation_count FROM interval_summaries").fetchone()[0] == 171


def test_foreign_key_rejects_unknown_beacon() -> None:
    db = connection()
    apply_schema(db)
    values = list(observation_values())
    values[0] = "unknown"
    sql = """INSERT INTO observations (
        beacon_id, window_start_utc, window_end_utc, detection_state,
        measurement_source, derived_local_snr_db, verification_snr_db,
        ka9q_reported_snr_db, measurement_quality, verification_quality,
        identification_quality, verification_accepted, frequency_offset_hz,
        identified_callsign, reason_code, created_at_utc
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(sql, tuple(values))


def test_validate_schema_reports_missing_tables() -> None:
    db = connection()
    db.execute("CREATE TABLE schema_version(version INTEGER PRIMARY KEY, applied_at_utc TEXT NOT NULL)")
    db.execute("INSERT INTO schema_version VALUES (1, '2026-08-06T12:00:00Z')")
    errors = validate_schema(db)
    assert any("missing tables" in error for error in errors)
