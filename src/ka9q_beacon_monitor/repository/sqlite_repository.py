from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

SCHEMA_VERSION = 1


class RepositoryError(RuntimeError):
    """Raised when a repository operation cannot be completed safely."""


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime values must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return list(value)
    raise TypeError(f"unsupported JSON value: {type(value).__name__}")


def _to_mapping(value: Any) -> Mapping[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, Mapping):
        return value
    raise TypeError("repository values must be dataclasses or mappings")


def _payload(value: Any) -> str:
    return json.dumps(_to_mapping(value), default=_json_default, sort_keys=True, separators=(",", ":"))


def _required_text(mapping: Mapping[str, Any], *names: str) -> str:
    for name in names:
        value = mapping.get(name)
        if value is not None:
            if isinstance(value, datetime):
                return _json_default(value)
            text = str(value).strip()
            if text:
                return text
    raise ValueError(f"missing required field; expected one of: {', '.join(names)}")


class SQLiteRepository:
    """Transactional SQLite persistence for observations and interval summaries."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.database_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._connection.execute("PRAGMA synchronous = NORMAL")
        self.migrate()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteRepository":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            yield self._connection
        except Exception:
            self._connection.rollback()
            raise
        else:
            self._connection.commit()

    def migrate(self) -> None:
        with self.transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_metadata ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS observations ("
                "beacon_id TEXT NOT NULL,"
                "window_start_utc TEXT NOT NULL,"
                "window_end_utc TEXT NOT NULL,"
                "payload_json TEXT NOT NULL,"
                "updated_at_utc TEXT NOT NULL,"
                "PRIMARY KEY (beacon_id, window_start_utc))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_observations_beacon_end "
                "ON observations (beacon_id, window_end_utc)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS interval_summaries ("
                "beacon_id TEXT NOT NULL,"
                "interval_start_utc TEXT NOT NULL,"
                "interval_end_utc TEXT NOT NULL,"
                "payload_json TEXT NOT NULL,"
                "updated_at_utc TEXT NOT NULL,"
                "PRIMARY KEY (beacon_id, interval_start_utc))"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_summaries_beacon_end "
                "ON interval_summaries (beacon_id, interval_end_utc)"
            )
            connection.execute(
                "INSERT INTO schema_metadata(key, value) VALUES('schema_version', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (str(SCHEMA_VERSION),),
            )

    @property
    def schema_version(self) -> int:
        row = self._connection.execute(
            "SELECT value FROM schema_metadata WHERE key='schema_version'"
        ).fetchone()
        if row is None:
            raise RepositoryError("schema version metadata is missing")
        return int(row["value"])

    def save_observation(self, observation: Any) -> None:
        mapping = _to_mapping(observation)
        beacon_id = _required_text(mapping, "beacon_id")
        start = _required_text(mapping, "window_start_utc", "start_utc")
        end = _required_text(mapping, "window_end_utc", "end_utc")
        now = _json_default(datetime.now(timezone.utc))
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO observations(beacon_id, window_start_utc, window_end_utc, payload_json, updated_at_utc) "
                "VALUES(?,?,?,?,?) ON CONFLICT(beacon_id, window_start_utc) DO UPDATE SET "
                "window_end_utc=excluded.window_end_utc, payload_json=excluded.payload_json, "
                "updated_at_utc=excluded.updated_at_utc",
                (beacon_id, start, end, _payload(observation), now),
            )

    def save_interval_summary(self, summary: Any) -> None:
        mapping = _to_mapping(summary)
        beacon_id = _required_text(mapping, "beacon_id")
        start = _required_text(mapping, "interval_start_utc", "start_utc")
        end = _required_text(mapping, "interval_end_utc", "end_utc")
        now = _json_default(datetime.now(timezone.utc))
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO interval_summaries(beacon_id, interval_start_utc, interval_end_utc, payload_json, updated_at_utc) "
                "VALUES(?,?,?,?,?) ON CONFLICT(beacon_id, interval_start_utc) DO UPDATE SET "
                "interval_end_utc=excluded.interval_end_utc, payload_json=excluded.payload_json, "
                "updated_at_utc=excluded.updated_at_utc",
                (beacon_id, start, end, _payload(summary), now),
            )

    def get_observation(self, beacon_id: str, window_start_utc: datetime | str) -> dict[str, Any] | None:
        start = _json_default(window_start_utc) if isinstance(window_start_utc, datetime) else str(window_start_utc)
        row = self._connection.execute(
            "SELECT payload_json FROM observations WHERE beacon_id=? AND window_start_utc=?",
            (beacon_id, start),
        ).fetchone()
        return None if row is None else json.loads(row["payload_json"])

    def list_observations(self, beacon_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        rows = self._connection.execute(
            "SELECT payload_json FROM observations WHERE beacon_id=? "
            "ORDER BY window_start_utc DESC LIMIT ?",
            (beacon_id, limit),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def get_interval_summary(self, beacon_id: str, interval_start_utc: datetime | str) -> dict[str, Any] | None:
        start = _json_default(interval_start_utc) if isinstance(interval_start_utc, datetime) else str(interval_start_utc)
        row = self._connection.execute(
            "SELECT payload_json FROM interval_summaries WHERE beacon_id=? AND interval_start_utc=?",
            (beacon_id, start),
        ).fetchone()
        return None if row is None else json.loads(row["payload_json"])

    def list_interval_summaries(self, beacon_id: str, *, limit: int = 100) -> list[dict[str, Any]]:
        if limit <= 0:
            raise ValueError("limit must be positive")
        rows = self._connection.execute(
            "SELECT payload_json FROM interval_summaries WHERE beacon_id=? "
            "ORDER BY interval_start_utc DESC LIMIT ?",
            (beacon_id, limit),
        ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def purge_before(self, cutoff_utc: datetime) -> tuple[int, int]:
        cutoff = _json_default(cutoff_utc)
        with self.transaction() as connection:
            observations = connection.execute(
                "DELETE FROM observations WHERE window_end_utc < ?", (cutoff,)
            ).rowcount
            summaries = connection.execute(
                "DELETE FROM interval_summaries WHERE interval_end_utc < ?", (cutoff,)
            ).rowcount
        return observations, summaries

    def counts(self) -> tuple[int, int]:
        observations = self._connection.execute("SELECT COUNT(*) AS n FROM observations").fetchone()["n"]
        summaries = self._connection.execute("SELECT COUNT(*) AS n FROM interval_summaries").fetchone()["n"]
        return int(observations), int(summaries)
