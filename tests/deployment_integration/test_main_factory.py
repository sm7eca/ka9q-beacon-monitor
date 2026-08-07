from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from ka9q_beacon_monitor import main as main_module


def test_main_resolves_factory_and_passes_config_path(tmp_path: Path, monkeypatch) -> None:
    config = tmp_path / "runtime.json"
    config.write_text("{}", encoding="utf-8")
    app = FastAPI()
    seen = {}

    def factory(*, config_path):
        seen["config_path"] = config_path
        return app

    monkeypatch.setattr(main_module, "resolve_factory", lambda spec: factory)
    monkeypatch.setattr(main_module.uvicorn, "run", lambda active, **kwargs: seen.update(app=active, kwargs=kwargs))

    assert main_module.main(["--config", str(config), "--factory", "x:y", "--host", "0.0.0.0", "--port", "9000"]) == 0
    assert seen["config_path"] == config
    assert seen["app"] is app
    assert seen["kwargs"] == {"host": "0.0.0.0", "port": 9000}
