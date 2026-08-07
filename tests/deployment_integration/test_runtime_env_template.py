from pathlib import Path

from ka9q_beacon_monitor.config import settings
from ka9q_beacon_monitor.environment import OBSERVABILITY_ENV_KEYS


def _example_keys() -> set[str]:
    example = Path("deploy/runtime.env.example").read_text(encoding="utf-8")
    return {
        line.split("=", 1)[0].strip()
        for line in example.splitlines()
        if line.strip().startswith("KA9Q_") and "=" in line
    }


def test_runtime_env_example_only_uses_registered_ka9q_environment_keys() -> None:
    configured_keys = _example_keys()
    registered_keys = (
        set(settings._ENV_KEYS)
        | set(settings._SECRET_ENV_KEYS)
        | set(OBSERVABILITY_ENV_KEYS)
    )
    assert configured_keys <= registered_keys


def test_runtime_env_example_can_supply_build_identity() -> None:
    configured_keys = _example_keys()
    assert "KA9Q_BUILD_VERSION" in configured_keys
    assert "KA9Q_BUILD_REVISION" in configured_keys
