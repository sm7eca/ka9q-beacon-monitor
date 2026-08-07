"""Deterministic deployment-package construction and atomic release switching."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tempfile
import zipfile

_FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)
_PACKAGE_ROOTS = ("src", "deploy")
_PACKAGE_FILES = ("pyproject.toml",)
_EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".DS_Store"}


class DeploymentError(RuntimeError):
    """Raised when a deployment package is invalid or cannot be installed."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _iter_repository_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for root_name in _PACKAGE_ROOTS:
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(repo_root)
            if any(part in _EXCLUDED_PARTS for part in rel.parts):
                continue
            files.append(path)
    for name in _PACKAGE_FILES:
        path = repo_root / name
        if path.is_file():
            files.append(path)
    return sorted(set(files), key=lambda p: p.relative_to(repo_root).as_posix())


def _writestr(zf: zipfile.ZipFile, name: str, data: bytes, mode: int = 0o644) -> None:
    info = zipfile.ZipInfo(name, _FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (mode & 0xFFFF) << 16
    zf.writestr(info, data)


def build_deployment_archive(repo_root: Path, output_path: Path, *, version: str) -> Path:
    """Build a byte-for-byte deterministic deployment ZIP from repository inputs."""
    repo_root = Path(repo_root).resolve()
    output_path = Path(output_path).resolve()
    if not version or any(ch.isspace() for ch in version):
        raise DeploymentError("version must be non-empty and contain no whitespace")

    entries: dict[str, bytes] = {}
    for path in _iter_repository_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        entries[rel] = path.read_bytes()

    manifest = {
        "format_version": 1,
        "package": "ka9q-beacon-monitor",
        "version": version,
        "files": [
            {"path": name, "sha256": _sha256(entries[name]), "size": len(entries[name])}
            for name in sorted(entries)
        ],
    }
    entries["RELEASE_MANIFEST.json"] = (
        json.dumps(manifest, indent=2, sort_keys=True, separators=(",", ": ")).encode("utf-8") + b"\n"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w") as zf:
        for name in sorted(entries):
            mode = 0o755 if name.endswith(".sh") else 0o644
            _writestr(zf, name, entries[name], mode)
    return output_path


def _safe_member(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise DeploymentError(f"unsafe archive path: {name}")
    return path


def verify_deployment_archive(archive_path: Path) -> dict[str, object]:
    """Verify manifest completeness, paths and SHA-256 checksums."""
    archive_path = Path(archive_path)
    with zipfile.ZipFile(archive_path, "r") as zf:
        names = set(zf.namelist())
        for name in names:
            _safe_member(name)
        if "RELEASE_MANIFEST.json" not in names:
            raise DeploymentError("RELEASE_MANIFEST.json missing")
        manifest = json.loads(zf.read("RELEASE_MANIFEST.json"))
        declared = {item["path"]: item for item in manifest.get("files", [])}
        actual = names - {"RELEASE_MANIFEST.json"}
        if set(declared) != actual:
            raise DeploymentError("archive contents do not match release manifest")
        for name, item in declared.items():
            data = zf.read(name)
            if _sha256(data) != item.get("sha256") or len(data) != item.get("size"):
                raise DeploymentError(f"checksum or size mismatch: {name}")
        return manifest


def _atomic_symlink(link: Path, target: Path) -> None:
    tmp = link.with_name(link.name + ".next")
    try:
        tmp.unlink()
    except FileNotFoundError:
        pass
    relative_target = os.path.relpath(target, start=link.parent)
    os.symlink(relative_target, tmp)
    os.replace(tmp, link)


def install_release(archive_path: Path, install_root: Path) -> Path:
    """Install a verified archive into a versioned directory and atomically switch current."""
    manifest = verify_deployment_archive(archive_path)
    version = str(manifest["version"])
    install_root = Path(install_root).resolve()
    releases = install_root / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    final_dir = releases / version

    if final_dir.exists():
        raise DeploymentError(f"release already installed: {version}")

    staging = Path(tempfile.mkdtemp(prefix=f".{version}.", dir=releases))
    try:
        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in zf.namelist():
                _safe_member(name)
                target = staging / Path(*PurePosixPath(name).parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(name))
                if name.endswith(".sh"):
                    target.chmod(0o755)
        os.replace(staging, final_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    current = install_root / "current"
    previous = install_root / "previous"
    if current.is_symlink():
        old = current.resolve(strict=True)
        if old.parent == releases:
            _atomic_symlink(previous, old)
    _atomic_symlink(current, final_dir)
    return final_dir


def rollback_release(install_root: Path) -> Path:
    """Atomically swap current and previous releases."""
    install_root = Path(install_root).resolve()
    current = install_root / "current"
    previous = install_root / "previous"
    if not current.is_symlink() or not previous.is_symlink():
        raise DeploymentError("rollback requires current and previous releases")
    current_target = current.resolve(strict=True)
    previous_target = previous.resolve(strict=True)
    _atomic_symlink(current, previous_target)
    _atomic_symlink(previous, current_target)
    return previous_target
