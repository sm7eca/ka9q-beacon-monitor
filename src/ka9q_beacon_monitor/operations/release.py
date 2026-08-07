from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Any

from ka9q_beacon_monitor.repository.sqlite_repository import SCHEMA_VERSION


class OperationsError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def backup_sqlite_database(database_path: str | Path, backup_path: str | Path) -> dict[str, Any]:
    src = Path(database_path)
    dst = Path(backup_path)
    if not src.is_file():
        raise OperationsError(f"database does not exist: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    source = sqlite3.connect(src)
    try:
        target = sqlite3.connect(dst)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    return {"path": str(dst), "sha256": _sha256(dst), "size": dst.stat().st_size}


def restore_sqlite_database(backup_path: str | Path, database_path: str | Path, *, expected_sha256: str) -> None:
    src = Path(backup_path)
    dst = Path(database_path)
    if not src.is_file():
        raise OperationsError(f"backup does not exist: {src}")
    if _sha256(src) != expected_sha256:
        raise OperationsError("backup checksum mismatch")
    check = sqlite3.connect(src)
    try:
        result = check.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise OperationsError("backup integrity check failed")
    finally:
        check.close()
    dst.parent.mkdir(parents=True, exist_ok=True)
    staging = dst.with_name(dst.name + ".restore-next")
    try:
        shutil.copy2(src, staging)
        staging.replace(dst)
    except Exception:
        try:
            staging.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def build_release_manifest(
    *,
    version: str,
    revision: str,
    package_path: str | Path,
    review_decisions: Mapping[str, str],
    phase0_assumptions: Mapping[str, str],
    configuration_schema_version: str = "M5.1-1.0",
) -> dict[str, Any]:
    package = Path(package_path)
    if not package.is_file():
        raise OperationsError("release package is missing")
    blocked = sorted(k for k, v in phase0_assumptions.items() if v != "VERIFIED")
    nonapproved = sorted(k for k, v in review_decisions.items() if v != "APPROVED")
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "version": version,
        "revision": revision,
        "package": {"name": package.name, "sha256": _sha256(package), "size": package.stat().st_size},
        "configuration_schema_version": configuration_schema_version,
        "migration_state": {"repository_schema_version": SCHEMA_VERSION},
        "review_decisions": dict(sorted(review_decisions.items())),
        "phase0_assumptions": dict(sorted(phase0_assumptions.items())),
        "software_release_ready": not nonapproved,
        "field_release_ready": not nonapproved and not blocked,
        "release_blockers": [*(f"review:{x}" for x in nonapproved), *(f"phase0:{x}" for x in blocked)],
    }
