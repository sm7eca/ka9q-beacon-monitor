from pathlib import Path

import pytest

from ka9q_beacon_monitor.model.database import DatabaseConfig, RetentionPolicy


def test_default_retention_policy() -> None:
    policy = RetentionPolicy()
    assert policy.observations_days == 90
    assert policy.interval_summaries_days is None
    assert policy.health_events_days == 30


@pytest.mark.parametrize("field", ["observations_days", "health_events_days"])
def test_retention_periods_must_be_positive(field: str) -> None:
    values = {"observations_days": 90, "health_events_days": 30}
    values[field] = 0
    with pytest.raises(ValueError):
        RetentionPolicy(**values)


def test_optional_summary_retention_must_be_positive() -> None:
    with pytest.raises(ValueError):
        RetentionPolicy(interval_summaries_days=0)


def test_database_config_validation() -> None:
    config = DatabaseConfig(path=Path("beacons.db"), busy_timeout_ms=1000)
    assert config.enable_wal is True
    with pytest.raises(ValueError):
        DatabaseConfig(path=Path("beacons.db"), busy_timeout_ms=0)
