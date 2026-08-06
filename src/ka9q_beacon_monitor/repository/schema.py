from __future__ import annotations

import sqlite3
from collections.abc import Iterable

SCHEMA_VERSION = 1

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at_utc TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS beacons (
        beacon_id TEXT PRIMARY KEY,
        callsign TEXT NOT NULL,
        frequency_hz INTEGER NOT NULL CHECK (frequency_hz > 0),
        enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
        created_at_utc TEXT NOT NULL,
        updated_at_utc TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS observations (
        observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        beacon_id TEXT NOT NULL,
        window_start_utc TEXT NOT NULL,
        window_end_utc TEXT NOT NULL,
        detection_state TEXT NOT NULL,
        measurement_source TEXT NOT NULL,
        derived_local_snr_db REAL,
        verification_snr_db REAL,
        ka9q_reported_snr_db REAL,
        measurement_quality TEXT NOT NULL,
        verification_quality TEXT NOT NULL,
        identification_quality TEXT NOT NULL,
        verification_accepted INTEGER NOT NULL CHECK (verification_accepted IN (0, 1)),
        frequency_offset_hz REAL,
        identified_callsign TEXT,
        reason_code TEXT NOT NULL,
        created_at_utc TEXT NOT NULL,
        FOREIGN KEY (beacon_id) REFERENCES beacons(beacon_id),
        UNIQUE (beacon_id, window_start_utc)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS observations_beacon_time_idx
    ON observations(beacon_id, window_start_utc)
    """,
    """
    CREATE TABLE IF NOT EXISTS interval_summaries (
        beacon_id TEXT NOT NULL,
        interval_start_utc TEXT NOT NULL,
        interval_end_utc TEXT NOT NULL,
        expected_observation_count INTEGER NOT NULL CHECK (expected_observation_count > 0),
        observation_count INTEGER NOT NULL CHECK (observation_count >= 0),
        valid_observation_count INTEGER NOT NULL CHECK (valid_observation_count >= 0),
        verified_observation_count INTEGER NOT NULL CHECK (verified_observation_count >= 0),
        audible_observation_count INTEGER NOT NULL CHECK (audible_observation_count >= 0),
        data_coverage_percent REAL NOT NULL CHECK (data_coverage_percent BETWEEN 0 AND 100),
        audible_percent REAL NOT NULL CHECK (audible_percent BETWEEN 0 AND 100),
        median_classification_snr_db REAL,
        maximum_classification_snr_db REAL,
        median_frequency_offset_hz REAL,
        final_state TEXT NOT NULL,
        quality TEXT NOT NULL,
        updated_at_utc TEXT NOT NULL,
        PRIMARY KEY (beacon_id, interval_start_utc),
        FOREIGN KEY (beacon_id) REFERENCES beacons(beacon_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS summaries_time_idx
    ON interval_summaries(interval_start_utc)
    """,
    """
    CREATE TABLE IF NOT EXISTS health_events (
        health_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        occurred_at_utc TEXT NOT NULL,
        component_id TEXT NOT NULL,
        severity TEXT NOT NULL,
        event_code TEXT NOT NULL,
        detail TEXT,
        UNIQUE (occurred_at_utc, component_id, event_code)
    )
    """,
)

REQUIRED_TABLES = frozenset(
    {"schema_version", "beacons", "observations", "interval_summaries", "health_events"}
)


def apply_schema(connection: sqlite3.Connection) -> None:
    """Apply the complete version-1 schema in one transaction."""
    connection.execute("PRAGMA foreign_keys = ON")
    with connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.execute(
            "INSERT OR IGNORE INTO schema_version(version, applied_at_utc) "
            "VALUES (?, strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))",
            (SCHEMA_VERSION,),
        )


def list_tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )
    return {row[0] for row in rows}


def validate_schema(connection: sqlite3.Connection) -> list[str]:
    """Return human-readable schema errors; an empty list means valid."""
    errors: list[str] = []
    missing = REQUIRED_TABLES - list_tables(connection)
    if missing:
        errors.append(f"missing tables: {', '.join(sorted(missing))}")

    version_row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
    if version_row is None or version_row[0] != SCHEMA_VERSION:
        errors.append(f"schema version must be {SCHEMA_VERSION}")

    unique_indexes = _unique_index_columns(connection, "observations")
    if ("beacon_id", "window_start_utc") not in unique_indexes:
        errors.append("observations must be unique by beacon_id and window_start_utc")

    summary_pk = _primary_key_columns(connection, "interval_summaries")
    if summary_pk != ("beacon_id", "interval_start_utc"):
        errors.append("interval_summaries primary key is invalid")
    return errors


def _primary_key_columns(connection: sqlite3.Connection, table: str) -> tuple[str, ...]:
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    keyed = sorted(((row[5], row[1]) for row in rows if row[5] > 0), key=lambda item: item[0])
    return tuple(name for _, name in keyed)


def _unique_index_columns(connection: sqlite3.Connection, table: str) -> set[tuple[str, ...]]:
    result: set[tuple[str, ...]] = set()
    for row in connection.execute(f"PRAGMA index_list({table})"):
        if not row[2]:
            continue
        index_name = row[1]
        columns = tuple(item[2] for item in connection.execute(f"PRAGMA index_info({index_name})"))
        result.add(columns)
    return result
