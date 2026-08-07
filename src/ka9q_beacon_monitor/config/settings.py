from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
import json
import os
from pathlib import Path
from typing import Mapping, Any

from ka9q_beacon_monitor.environment import OBSERVABILITY_ENV_KEYS


class ConfigError(ValueError):
    """Raised when runtime configuration is invalid before service startup."""


class SecretValue:
    """Small redacting wrapper for injected secret material."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not isinstance(value, str) or not value:
            raise ConfigError("secret value must be a non-empty string")
        self._value = value

    def get_secret_value(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return "SecretValue('********')"

    __str__ = __repr__


@dataclass(frozen=True)
class RuntimeSecrets:
    verification_token: SecretValue | None = None


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    status_multicast_group: str = "239.0.0.1"
    status_port: int = 5004
    api_bind_host: str = "127.0.0.1"
    api_port: int = 8000
    web_bind_host: str = "127.0.0.1"
    web_port: int = 8080
    web_refresh_seconds: int = 30
    log_level: str = "INFO"
    verification_enabled: bool = False

    def __post_init__(self) -> None:
        if not str(self.database_path):
            raise ConfigError("database_path is required")
        try:
            address = ip_address(self.status_multicast_group)
        except ValueError as exc:
            raise ConfigError("status_multicast_group must be a valid IP address") from exc
        if address.version != 4 or not address.is_multicast:
            raise ConfigError("status_multicast_group must be an IPv4 multicast address")
        for name, value in (("status_port", self.status_port), ("api_port", self.api_port), ("web_port", self.web_port)):
            if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 65535:
                raise ConfigError(f"{name} must be an integer in range 1..65535")
        if not 5 <= self.web_refresh_seconds <= 3600:
            raise ConfigError("web_refresh_seconds must be in range 5..3600")
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigError("log_level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        if not self.api_bind_host or not self.web_bind_host:
            raise ConfigError("bind hosts must be non-empty")


@dataclass(frozen=True)
class RuntimeConfiguration:
    app: AppConfig
    secrets: RuntimeSecrets


_FILE_KEYS = {
    "database_path",
    "status_multicast_group",
    "status_port",
    "api_bind_host",
    "api_port",
    "web_bind_host",
    "web_port",
    "web_refresh_seconds",
    "log_level",
    "verification_enabled",
}
_ENV_KEYS = {
    "KA9Q_DATABASE_PATH": "database_path",
    "KA9Q_STATUS_MULTICAST_GROUP": "status_multicast_group",
    "KA9Q_STATUS_PORT": "status_port",
    "KA9Q_API_BIND_HOST": "api_bind_host",
    "KA9Q_API_PORT": "api_port",
    "KA9Q_WEB_BIND_HOST": "web_bind_host",
    "KA9Q_WEB_PORT": "web_port",
    "KA9Q_WEB_REFRESH_SECONDS": "web_refresh_seconds",
    "KA9Q_LOG_LEVEL": "log_level",
    "KA9Q_VERIFICATION_ENABLED": "verification_enabled",
}
_SECRET_ENV_KEYS = {"KA9Q_VERIFICATION_TOKEN": "verification_token"}
_FORBIDDEN_SECRET_NAMES = {"verification_token", "secrets", "password", "token", "api_key"}


def _parse_bool(value: Any, *, name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    raise ConfigError(f"{name} must be a boolean")


def _coerce(name: str, value: Any) -> Any:
    if name in {"status_port", "api_port", "web_port", "web_refresh_seconds"}:
        if isinstance(value, bool):
            raise ConfigError(f"{name} must be an integer")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"{name} must be an integer") from exc
    if name == "verification_enabled":
        return _parse_bool(value, name=name)
    if name == "database_path":
        if not isinstance(value, (str, os.PathLike)) or not str(value):
            raise ConfigError("database_path must be a non-empty path")
        return Path(value)
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be a string")
    return value


def _read_config_file(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"configuration file is not valid JSON: {path}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("configuration root must be a JSON object")
    for key in raw:
        lowered = key.lower()
        if lowered in _FORBIDDEN_SECRET_NAMES or any(word in lowered for word in ("secret", "password", "token", "api_key")):
            raise ConfigError(f"secret-like key '{key}' is forbidden in configuration files")
        if key not in _FILE_KEYS:
            raise ConfigError(f"unknown configuration key: {key}")
    return raw


def load_runtime_configuration(
    config_path: str | os.PathLike[str] | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> RuntimeConfiguration:
    """Load and fully validate runtime configuration without opening external resources.

    Precedence: environment overrides JSON file values. Secret material is accepted only
    from dedicated environment variables and is wrapped in a redacting SecretValue.
    """

    env = os.environ if environ is None else environ

    known_env_keys = set(_ENV_KEYS) | set(_SECRET_ENV_KEYS) | set(OBSERVABILITY_ENV_KEYS)
    unknown_ka9q_keys = sorted(
        name for name in env if name.startswith("KA9Q_") and name not in known_env_keys
    )
    if unknown_ka9q_keys:
        raise ConfigError(
            "unknown KA9Q environment variable(s): " + ", ".join(unknown_ka9q_keys)
        )

    values: dict[str, Any] = {}
    if config_path is not None:
        values.update(_read_config_file(Path(config_path)))

    for env_name, field_name in _ENV_KEYS.items():
        if env_name in env:
            values[field_name] = env[env_name]

    if "database_path" not in values:
        raise ConfigError("database_path is required (file key or KA9Q_DATABASE_PATH)")

    coerced = {name: _coerce(name, value) for name, value in values.items()}
    app = AppConfig(**coerced)

    secret_values: dict[str, SecretValue | None] = {}
    for env_name, field_name in _SECRET_ENV_KEYS.items():
        raw_value = env.get(env_name)
        secret_values[field_name] = SecretValue(raw_value) if raw_value else None

    if app.verification_enabled and secret_values["verification_token"] is None:
        raise ConfigError("KA9Q_VERIFICATION_TOKEN is required when verification is enabled")

    # Do not preserve or expose unrelated environment variables, secret or otherwise.
    secrets = RuntimeSecrets(**secret_values)
    return RuntimeConfiguration(app=app, secrets=secrets)
