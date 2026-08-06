from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import zipfile

SCRIPT = Path(__file__).parents[1] / "tools" / "create_review_package.py"
spec = importlib.util.spec_from_file_location("create_review_package", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def _write(repo: Path, relative: str, text: str = "x") -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_build_m3_package(tmp_path: Path) -> None:
    for entry in module.MILESTONES["M3"]:
        if Path(entry).suffix:
            _write(tmp_path, entry)
        else:
            _write(tmp_path, f"{entry}/sample.py")

    output = module.build_package(tmp_path, "M3", tmp_path / "out", strict=True)
    assert output.exists()

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert "REVIEW_PACKAGE_MANIFEST.json" in names
        assert "reviews/M3/REVIEW_REQUEST.md" in names
        manifest = json.loads(archive.read("REVIEW_PACKAGE_MANIFEST.json"))
        assert manifest["milestone"] == "M3"
        assert manifest["missing_optional_or_required_inputs"] == []


def test_strict_mode_rejects_missing_inputs(tmp_path: Path) -> None:
    try:
        module.build_package(tmp_path, "M3", tmp_path / "out", strict=True)
    except FileNotFoundError as exc:
        assert "Required review inputs are missing" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_allow_missing_creates_partial_package(tmp_path: Path) -> None:
    _write(tmp_path, "reviews/M3/REVIEW_REQUEST.md")
    output = module.build_package(tmp_path, "M3", tmp_path / "out", strict=False)
    with zipfile.ZipFile(output) as archive:
        manifest = json.loads(archive.read("REVIEW_PACKAGE_MANIFEST.json"))
        assert manifest["missing_optional_or_required_inputs"]
