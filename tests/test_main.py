import json
from pathlib import Path

import pytest

from ka9q_beacon_monitor.main import build_parser, load_config


def test_parser_requires_config() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_load_config_requires_object(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    with pytest.raises(ValueError):
        load_config(path)


def test_load_config_reads_object(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"database": "monitor.db"}), encoding="utf-8")
    assert load_config(path) == {"database": "monitor.db"}
