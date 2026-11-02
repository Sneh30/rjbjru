"""Command-line entry point for ingestion.

Examples:
    python -m app.ingestion.cli fetch
    python -m app.ingestion.cli build
    python -m app.ingestion.cli run --force
    python -m app.ingestion.cli verify
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time as time_module

from app.config import get_settings
from app.domain.errors import WindLensError

from .pipeline import build_snapshot, fetch_all, verify_snapshot


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    for handler in logging.getLogger().handlers:
        if handler.formatter is not None:
            handler.formatter.converter = time_module.gmtime  # type: ignore[attr-defined]


def _print_summary(manifest: dict[str, object]) -> None:
    processed = manifest.get("processed", {})
    print(
        json.dumps(
            {
                "fingerprint": manifest.get("fingerprint"),
                "actuals_rows": processed.get("actuals", {}).get("rows"),
                "forecasts_rows": processed.get("forecasts", {}).get("rows"),
                "generated_at": manifest.get("generated_at"),
            },
            indent=2,
        )
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="python -m app.ingestion.cli",
        description="WindLens Elexon ingestion and snapshot tools",
    )
    parser.add_argument("--verbose", action="store_true", help="enable debug logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="download raw Elexon chunks")
    fetch.add_argument("--force", action="store_true", help="refetch cached chunks")

    run = subparsers.add_parser("run", help="fetch and build the snapshot")
    run.add_argument("--force", action="store_true", help="refetch cached chunks")

    subparsers.add_parser("build", help="build processed data from cached raw chunks")
    subparsers.add_parser("verify", help="re-hash the processed snapshot")
    subparsers.add_parser("report", help="print the committed quality report")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _configure_logging(bool(args.verbose))
    settings = get_settings()
    try:
        match args.command:
            case "fetch":
                manifest = fetch_all(settings, force=bool(args.force))
                print(json.dumps({"chunks": len(manifest["chunks"])}, indent=2))
            case "run":
                fetch_all(settings, force=bool(args.force))
                _print_summary(build_snapshot(settings))
            case "build":
                _print_summary(build_snapshot(settings))
            case "verify":
                print(json.dumps(verify_snapshot(settings), indent=2, default=str))
            case "report":
                report_path = settings.processed_dir / "quality_report.json"
                print(report_path.read_text(encoding="utf-8"))
            case _:  # pragma: no cover - argparse enforces the choices
                parser.error("unknown command")
    except (WindLensError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
