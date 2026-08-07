from __future__ import annotations

import hashlib
from pathlib import Path
import zipfile

import pytest

from ka9q_beacon_monitor.deployment import (
    DeploymentError,
    build_deployment_archive,
    install_release,
    rollback_release,
    verify_deployment_archive,
)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "src/pkg").mkdir(parents=True)
    (root / "deploy").mkdir()
    (root / "src/pkg/app.py").write_text("print('ok')\n", encoding="utf-8")
    (root / "deploy/run.sh").write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    (root / "pyproject.toml").write_text("[project]\nname='x'\nversion='1'\n", encoding="utf-8")
    return root


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_build_is_byte_for_byte_reproducible(tmp_path: Path):
    repo = _repo(tmp_path)
    a = build_deployment_archive(repo, tmp_path / "a.zip", version="1.2.3")
    b = build_deployment_archive(repo, tmp_path / "b.zip", version="1.2.3")
    assert _digest(a) == _digest(b)


def test_manifest_verifies_all_archive_files(tmp_path: Path):
    repo = _repo(tmp_path)
    archive = build_deployment_archive(repo, tmp_path / "release.zip", version="1.2.3")
    manifest = verify_deployment_archive(archive)
    assert manifest["version"] == "1.2.3"
    assert {f["path"] for f in manifest["files"]} == {
        "deploy/run.sh", "pyproject.toml", "src/pkg/app.py"
    }


def test_tampered_archive_is_rejected(tmp_path: Path):
    repo = _repo(tmp_path)
    archive = build_deployment_archive(repo, tmp_path / "release.zip", version="1.2.3")
    rewritten = tmp_path / "tampered.zip"
    with zipfile.ZipFile(archive, "r") as source, zipfile.ZipFile(rewritten, "w") as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "src/pkg/app.py":
                data = b"tampered"
            target.writestr(info, data)
    with pytest.raises(DeploymentError):
        verify_deployment_archive(rewritten)


def test_install_switches_current_atomically_and_preserves_previous(tmp_path: Path):
    repo = _repo(tmp_path)
    root = tmp_path / "install"
    one = build_deployment_archive(repo, tmp_path / "one.zip", version="1.0.0")
    install_release(one, root)
    assert (root / "current").resolve().name == "1.0.0"

    (repo / "src/pkg/app.py").write_text("print('v2')\n", encoding="utf-8")
    two = build_deployment_archive(repo, tmp_path / "two.zip", version="2.0.0")
    install_release(two, root)
    assert (root / "current").resolve().name == "2.0.0"
    assert (root / "previous").resolve().name == "1.0.0"


def test_rollback_swaps_current_and_previous(tmp_path: Path):
    repo = _repo(tmp_path)
    root = tmp_path / "install"
    install_release(build_deployment_archive(repo, tmp_path / "a.zip", version="1.0.0"), root)
    (repo / "src/pkg/app.py").write_text("v2\n", encoding="utf-8")
    install_release(build_deployment_archive(repo, tmp_path / "b.zip", version="2.0.0"), root)
    rollback_release(root)
    assert (root / "current").resolve().name == "1.0.0"
    assert (root / "previous").resolve().name == "2.0.0"


def test_duplicate_version_install_is_rejected(tmp_path: Path):
    repo = _repo(tmp_path)
    root = tmp_path / "install"
    archive = build_deployment_archive(repo, tmp_path / "a.zip", version="1.0.0")
    install_release(archive, root)
    with pytest.raises(DeploymentError):
        install_release(archive, root)


def test_archive_path_traversal_is_rejected(tmp_path: Path):
    repo = _repo(tmp_path)
    archive = build_deployment_archive(repo, tmp_path / "release.zip", version="1.2.3")
    malicious = tmp_path / "path-traversal.zip"
    with zipfile.ZipFile(archive, "r") as source, zipfile.ZipFile(malicious, "w") as target:
        for info in source.infolist():
            target.writestr(info, source.read(info.filename))
        target.writestr("../../etc/evil.txt", b"evil")
    with pytest.raises(DeploymentError, match="unsafe archive path"):
        verify_deployment_archive(malicious)


def test_extraction_failure_preserves_active_release_and_cleans_staging(tmp_path: Path, monkeypatch):
    repo = _repo(tmp_path)
    root = tmp_path / "install"
    one = build_deployment_archive(repo, tmp_path / "one.zip", version="1.0.0")
    install_release(one, root)
    current_before = (root / "current").resolve(strict=True)

    (repo / "src/pkg/app.py").write_text("print('v2')\n", encoding="utf-8")
    two = build_deployment_archive(repo, tmp_path / "two.zip", version="2.0.0")

    original_write_bytes = Path.write_bytes
    calls = {"count": 0}

    def failing_write_bytes(self: Path, data: bytes):
        if self.is_relative_to(root / "releases"):
            calls["count"] += 1
            if calls["count"] == 2:
                raise OSError("simulated disk failure mid-extraction")
        return original_write_bytes(self, data)

    monkeypatch.setattr(Path, "write_bytes", failing_write_bytes)

    with pytest.raises(OSError, match="simulated disk failure"):
        install_release(two, root)

    assert (root / "current").resolve(strict=True) == current_before
    assert not (root / "releases" / "2.0.0").exists()
    assert not any(path.name.startswith(".2.0.0.") for path in (root / "releases").iterdir())


def test_rollback_without_previous_is_rejected_without_changing_current(tmp_path: Path):
    repo = _repo(tmp_path)
    root = tmp_path / "install"
    archive = build_deployment_archive(repo, tmp_path / "one.zip", version="1.0.0")
    install_release(archive, root)
    current_before = (root / "current").resolve(strict=True)

    with pytest.raises(DeploymentError, match="rollback requires current and previous releases"):
        rollback_release(root)

    assert (root / "current").resolve(strict=True) == current_before
    assert not (root / "previous").exists()
