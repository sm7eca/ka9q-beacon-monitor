import json
from pathlib import Path

import pytest

from ka9q_beacon_monitor.config import ConfigError, SecretValue, load_runtime_configuration


def write_config(tmp_path: Path, **overrides):
    payload = {
        "database_path": str(tmp_path / "beacons.sqlite3"),
        "status_multicast_group": "239.1.2.3",
        "status_port": 5004,
        "api_port": 8000,
        "web_port": 8080,
        "web_refresh_seconds": 30,
        "log_level": "INFO",
        "verification_enabled": False,
    }
    payload.update(overrides)
    path = tmp_path / "config.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_valid_file_loads_without_external_resources(tmp_path):
    config = load_runtime_configuration(write_config(tmp_path), environ={})
    assert config.app.database_path == tmp_path / "beacons.sqlite3"
    assert config.app.status_multicast_group == "239.1.2.3"
    assert config.secrets.verification_token is None


def test_environment_overrides_non_secret_file_values(tmp_path):
    config = load_runtime_configuration(
        write_config(tmp_path, api_port=8000),
        environ={"KA9Q_API_PORT": "9000", "KA9Q_LOG_LEVEL": "WARNING"},
    )
    assert config.app.api_port == 9000
    assert config.app.log_level == "WARNING"


def test_environment_only_configuration_is_supported(tmp_path):
    config = load_runtime_configuration(
        None,
        environ={"KA9Q_DATABASE_PATH": str(tmp_path / "runtime.sqlite3")},
    )
    assert config.app.database_path == tmp_path / "runtime.sqlite3"


def test_missing_database_path_fails_closed():
    with pytest.raises(ConfigError, match="database_path is required"):
        load_runtime_configuration(None, environ={})


def test_invalid_multicast_group_fails_closed(tmp_path):
    with pytest.raises(ConfigError, match="IPv4 multicast"):
        load_runtime_configuration(write_config(tmp_path, status_multicast_group="127.0.0.1"), environ={})


def test_invalid_port_fails_closed(tmp_path):
    with pytest.raises(ConfigError, match="api_port"):
        load_runtime_configuration(write_config(tmp_path, api_port=70000), environ={})


def test_unknown_file_key_is_rejected(tmp_path):
    path = write_config(tmp_path)
    payload = json.loads(path.read_text())
    payload["unexpected"] = "value"
    path.write_text(json.dumps(payload))
    with pytest.raises(ConfigError, match="unknown configuration key"):
        load_runtime_configuration(path, environ={})


def test_secret_like_keys_are_forbidden_in_config_file(tmp_path):
    path = write_config(tmp_path)
    payload = json.loads(path.read_text())
    payload["verification_token"] = "must-not-be-here"
    path.write_text(json.dumps(payload))
    with pytest.raises(ConfigError, match="secret-like key"):
        load_runtime_configuration(path, environ={})


def test_verification_secret_is_injected_only_from_environment(tmp_path):
    config = load_runtime_configuration(
        write_config(tmp_path, verification_enabled=True),
        environ={"KA9Q_VERIFICATION_TOKEN": "top-secret"},
    )
    assert config.secrets.verification_token.get_secret_value() == "top-secret"


def test_missing_required_secret_fails_without_secret_value_in_error(tmp_path):
    with pytest.raises(ConfigError) as exc_info:
        load_runtime_configuration(write_config(tmp_path, verification_enabled=True), environ={})
    assert "KA9Q_VERIFICATION_TOKEN" in str(exc_info.value)
    assert "top-secret" not in str(exc_info.value)


def test_secret_repr_and_str_are_redacted():
    secret = SecretValue("top-secret")
    assert "top-secret" not in repr(secret)
    assert "top-secret" not in str(secret)
    assert "********" in repr(secret)


def test_boolean_environment_value_is_strict(tmp_path):
    with pytest.raises(ConfigError, match="verification_enabled must be a boolean"):
        load_runtime_configuration(
            write_config(tmp_path),
            environ={"KA9Q_VERIFICATION_ENABLED": "maybe"},
        )


def test_malformed_json_fails_closed(tmp_path):
    path = tmp_path / "config.json"
    path.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_runtime_configuration(path, environ={})
