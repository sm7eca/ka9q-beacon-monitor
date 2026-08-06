"""Command-line entry point for the composed KA9Q Beacon Monitor service."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run KA9Q Beacon Monitor")
    parser.add_argument("--config", type=Path, required=True, help="Path to runtime JSON configuration")
    parser.add_argument("--factory", required=True, help="ASGI factory import path, for example package.module:create_app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser


def load_config(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("configuration root must be a JSON object")
    return data


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_config(args.config)
    # Concrete KA9Q wire decoder and verification backend are deployment adapters.
    # The ASGI factory is therefore supplied by the deployment package after
    # constructing BeaconRuntime with those verified adapters.
    uvicorn.run(args.factory, host=args.host, port=args.port, factory=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
