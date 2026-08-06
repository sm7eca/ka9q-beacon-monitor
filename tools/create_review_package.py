#!/usr/bin/env python3
"""Create deterministic AI review ZIP packages for KA9Q Beacon Monitor milestones."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile

MILESTONES: dict[str, tuple[str, ...]] = {
    "M3": (
        "akb/data/DM-STATUS-SAMPLE.md",
        "akb/data/DM-MEASUREMENT-WINDOW.md",
        "akb/data/DM-OBSERVATION.md",
        "akb/data/DM-INTERVAL-SUMMARY.md",
        "akb/data/DM-DATABASE.md",
        "src/ka9q_beacon_monitor/model",
        "src/ka9q_beacon_monitor/repository/schema.py",
        "tests/model",
        "tests/repository",
        "reviews/M3/REVIEW_REQUEST.md",
        "pyproject.toml",
    ),
}

EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".bak"}


def is_excluded(path: Path) -> bool:
    return bool(EXCLUDED_PARTS.intersection(path.parts)) or path.suffix in EXCLUDED_SUFFIXES


def collect_files(repo_root: Path, milestone: str) -> tuple[list[Path], list[str]]:
    if milestone not in MILESTONES:
        raise ValueError(f"Unsupported milestone: {milestone}")

    files: set[Path] = set()
    missing: list[str] = []
    for relative in MILESTONES[milestone]:
        candidate = repo_root / relative
        if candidate.is_file():
            if not is_excluded(candidate):
                files.add(candidate)
        elif candidate.is_dir():
            for item in candidate.rglob("*"):
                if item.is_file() and not is_excluded(item):
                    files.add(item)
        else:
            missing.append(relative)
    return sorted(files, key=lambda p: p.relative_to(repo_root).as_posix()), missing


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_package(repo_root: Path, milestone: str, output_dir: Path, strict: bool) -> Path:
    repo_root = repo_root.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    files, missing = collect_files(repo_root, milestone)

    if strict and missing:
        formatted = "\n".join(f"- {entry}" for entry in missing)
        raise FileNotFoundError(f"Required review inputs are missing:\n{formatted}")
    if not files:
        raise FileNotFoundError("No review files were found")

    package_name = f"{milestone}_AI_Review_Package.zip"
    output_path = output_dir / package_name

    manifest = {
        "schema_version": "1.0",
        "milestone": milestone,
        "package_type": "AI_REVIEW",
        "repository_root_name": repo_root.name,
        "strict_mode": strict,
        "included_files": [
            {
                "path": path.relative_to(repo_root).as_posix(),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in files
        ],
        "missing_optional_or_required_inputs": missing,
    }

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            arcname = path.relative_to(repo_root).as_posix()
            info = zipfile.ZipInfo(arcname)
            info.date_time = (2026, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())

        manifest_info = zipfile.ZipInfo("REVIEW_PACKAGE_MANIFEST.json")
        manifest_info.date_time = (2026, 1, 1, 0, 0, 0)
        manifest_info.compress_type = zipfile.ZIP_DEFLATED
        manifest_info.external_attr = 0o100644 << 16
        archive.writestr(
            manifest_info,
            json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"),
        )

    return output_path


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("milestone", choices=sorted(MILESTONES))
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=Path("review_packages"))
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Create a package even when configured inputs are missing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        output = build_package(
            repo_root=args.repo_root,
            milestone=args.milestone,
            output_dir=(args.repo_root / args.output_dir),
            strict=not args.allow_missing,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
