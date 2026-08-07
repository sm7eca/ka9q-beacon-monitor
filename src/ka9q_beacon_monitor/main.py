"""Command-line entry point for the composed KA9Q Beacon Monitor service."""

from __future__ import annotations

import argparse
from importlib import import_module
import json
from pathlib import Path
from typing import Callable

from fastapi import FastAPI
import uvicorn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run KA9Q Beacon Monitor")
    parser.add_argument("--config", type=Path, required=True, help="Path to runtime JSON configuration")
    parser.add_argument(
        "--factory",
        required=True,
        help="ASGI deployment factory import path; callable must accept config_path=",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser


def load_config(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("configuration root must be a JSON object")
    return data


def resolve_factory(spec: str) -> Callable[..., FastAPI]:
    if ":" not in spec:
        raise ValueError("factory must use module:callable syntax")
    module_name, attr_name = spec.split(":", 1)
    if not module_name or not attr_name:
        raise ValueError("factory must use module:callable syntax")
    module = import_module(module_name)
    factory = getattr(module, attr_name)
    if not callable(factory):
        raise TypeError("factory target must be callable")
    return factory


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    load_config(args.config)
    factory = resolve_factory(args.factory)
    app = factory(config_path=args.config)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
