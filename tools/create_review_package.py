#!/usr/bin/env python3
"""Create deterministic AI review ZIP packages from milestone configuration."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
import zipfile

DEFAULT_CONFIG = Path("tools/review_milestones.json")

EXCLUDED_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "review_packages",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".tmp", ".bak", ".DS_Store"}


@dataclass(frozen=True)
class MilestoneConfig:
    milestone_id: str
    required: tuple[str, ...]
    optional: tuple[str, ...]
    description: str = ""


def is_excluded(path: Path) -> bool:
    return bool(EXCLUDED_PARTS.intersection(path.parts)) or path.suffix in EXCLUDED_SUFFIXES


def _safe_relative(repo_root: Path, path: Path) -> Path:
    resolved_root = repo_root.resolve()
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"Configured path escapes repository root: {path}") from exc


def load_config(config_path: Path) -> dict[str, MilestoneConfig]:
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Review milestone config not found: {config_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {config_path}: {exc}") from exc

    if raw.get("schema_version") not in {"2.0", "2.1", "2.2"}:
        raise ValueError("Unsupported review milestone config schema_version")

    result: dict[str, MilestoneConfig] = {}
    for key, value in raw.get("milestones", {}).items():
        canonical = key.upper()
        required = tuple(value.get("required", []))
        optional = tuple(value.get("optional", []))
        if not required:
            raise ValueError(f"Milestone {key} has no required inputs")
        result[canonical] = MilestoneConfig(
            milestone_id=value.get("id", key),
            required=required,
            optional=optional,
            description=value.get("description", ""),
        )
    if not result:
        raise ValueError("No milestones are defined in config")
    return result


def _expand_entry(repo_root: Path, entry: str) -> list[Path]:
    # Glob entries are supported for future milestone configuration.
    if any(char in entry for char in "*?["):
        matches = [path for path in repo_root.glob(entry) if path.is_file() and not is_excluded(path)]
        for path in matches:
            _safe_relative(repo_root, path)
        return sorted(matches)

    candidate = repo_root / entry
    _safe_relative(repo_root, candidate)
    if candidate.is_file():
        return [] if is_excluded(candidate) else [candidate]
    if candidate.is_dir():
        return sorted(
            path for path in candidate.rglob("*") if path.is_file() and not is_excluded(path)
        )
    return []


def collect_files(
    repo_root: Path,
    milestone: MilestoneConfig,
) -> tuple[list[Path], list[str], list[str]]:
    files: set[Path] = set()
    missing_required: list[str] = []
    missing_optional: list[str] = []

    for entry in milestone.required:
        matches = _expand_entry(repo_root, entry)
        if matches:
            files.update(matches)
        else:
            missing_required.append(entry)

    for entry in milestone.optional:
        matches = _expand_entry(repo_root, entry)
        if matches:
            files.update(matches)
        else:
            missing_optional.append(entry)

    ordered = sorted(files, key=lambda p: p.relative_to(repo_root).as_posix())
    return ordered, missing_required, missing_optional


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_package(
    repo_root: Path,
    milestone_key: str,
    output_dir: Path,
    strict: bool,
    config_path: Path,
) -> Path:
    repo_root = repo_root.resolve()
    configs = load_config(config_path)
    key = milestone_key.upper()
    if key not in configs:
        supported = ", ".join(sorted(configs))
        raise ValueError(f"Unsupported milestone: {milestone_key}. Configured: {supported}")

    milestone = configs[key]
    output_dir.mkdir(parents=True, exist_ok=True)
    files, missing_required, missing_optional = collect_files(repo_root, milestone)

    if strict and missing_required:
        formatted = "\n".join(f"- {entry}" for entry in missing_required)
        raise FileNotFoundError(f"Required review inputs are missing:\n{formatted}")
    if not files:
        raise FileNotFoundError("No review files were found")

    safe_name = milestone.milestone_id.replace(".", "_").replace("/", "_")
    output_path = output_dir / f"{safe_name}_AI_Review_Package.zip"

    manifest = {
        "schema_version": "2.2",
        "milestone": milestone.milestone_id,
        "description": milestone.description,
        "package_type": "AI_REVIEW",
        "repository_root_name": repo_root.name,
        "strict_mode": strict,
        "configuration_file": config_path.relative_to(repo_root).as_posix()
        if config_path.is_relative_to(repo_root)
        else str(config_path),
        "included_files": [
            {
                "path": path.relative_to(repo_root).as_posix(),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
            for path in files
        ],
        "missing_required_inputs": missing_required,
        "missing_optional_inputs": missing_optional,
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
    parser.add_argument("milestone", nargs="?", help="Configured milestone, e.g. M3, M4 or M4.1")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=Path("review_packages"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--list", action="store_true", help="List configured milestones")
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Create a package even when required inputs are missing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    repo_root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config

    try:
        configs = load_config(config_path)
        if args.list:
            for key in sorted(configs):
                description = configs[key].description
                print(f"{key}\t{description}")
            return 0
        if not args.milestone:
            print("ERROR: milestone is required unless --list is used", file=sys.stderr)
            return 2

        output = build_package(
            repo_root=repo_root,
            milestone_key=args.milestone,
            output_dir=repo_root / args.output_dir,
            strict=not args.allow_missing,
            config_path=config_path,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    files, missing_required, missing_optional = collect_files(repo_root, configs[args.milestone.upper()])
    print(f"Created: {output}")
    print(f"Included files: {len(files)}")
    if missing_optional:
        print(f"Missing optional inputs: {len(missing_optional)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
