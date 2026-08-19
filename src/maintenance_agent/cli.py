"""CLI entry point: `scan-diff` and `scan-full` subcommands.

`scan-full` runs a real scan: LLM code review + SCA dependency scanning,
merged (Phase 1a + 1b). Issue filing lands in Phase 1c.
`scan-diff` is still a Phase 0 stub; diff-scoped scanning lands in Phase 1d.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .config import ConfigError, Settings
from .findings import ScanResult
from .logging_utils import RunLog, configure_logging, logger
from .scan import run_full_scan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="maintenance-agent",
        description="Autonomous security-scanning agent (Phase 1: report-only).",
    )
    parser.add_argument("--verbose", action="store_true", help="enable debug logging")

    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_full = subparsers.add_parser(
        "scan-full", help="scan an entire repository for vulnerabilities"
    )
    scan_full.add_argument("--repo", required=True, help="path to the target repository")

    scan_diff = subparsers.add_parser(
        "scan-diff", help="scan only the diff between two refs"
    )
    scan_diff.add_argument("--repo", required=True, help="path to the target repository")
    scan_diff.add_argument("--base", required=True, help="base git ref")
    scan_diff.add_argument("--head", required=True, help="head git ref")

    return parser


def print_scan_result(scan_result: ScanResult) -> None:
    if not scan_result.findings:
        print("No findings.")
        return

    for finding in scan_result.findings:
        location = finding.file_path
        if finding.line_start is not None:
            location += f":{finding.line_start}"
            if finding.line_end is not None and finding.line_end != finding.line_start:
                location += f"-{finding.line_end}"

        print(f"[{finding.severity.value.upper()}] {finding.title} ({finding.source.value})")
        print(f"  category:   {finding.category}")
        print(f"  location:   {location}")
        print(f"  confidence: {finding.confidence:.2f}")
        print(f"  why:        {finding.description}")
        print(f"  evidence:   {finding.evidence}")
        print()


async def _run_scan_full(args: argparse.Namespace, settings: Settings) -> int:
    run_log = RunLog(model=settings.model)
    logger.info("scan-full: repo=%s model=%s", args.repo, settings.model)

    scan_result = await run_full_scan(
        repo_path=args.repo,
        settings=settings,
        run_log=run_log,
    )

    print_scan_result(scan_result)
    run_log.log_summary()
    return 0


def cmd_scan_full(args: argparse.Namespace, settings: Settings) -> int:
    return asyncio.run(_run_scan_full(args, settings))


def cmd_scan_diff(args: argparse.Namespace, settings: Settings) -> int:
    run_log = RunLog(model=settings.model)
    logger.info(
        "scan-diff: repo=%s base=%s head=%s model=%s (not yet implemented)",
        args.repo,
        args.base,
        args.head,
        settings.model,
    )
    run_log.log_summary()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose)

    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        logger.error(str(exc))
        return 1

    if args.command == "scan-full":
        return cmd_scan_full(args, settings)
    if args.command == "scan-diff":
        return cmd_scan_diff(args, settings)

    parser.error(f"unknown command: {args.command}")
    return 2  # unreachable; parser.error() exits


if __name__ == "__main__":
    sys.exit(main())
