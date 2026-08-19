"""Orchestrates a full scan: LLM code review + SCA dependency scanning.

Kept out of cli.py so the CLI layer stays thin and this logic is directly
testable, per the project's "business logic separate from the entry point"
principle.
"""

from __future__ import annotations

from .agent.security_scan import run_security_scan
from .config import Settings
from .findings import ScanResult
from .logging_utils import RunLog
from .sca.osv_scanner import run_osv_scanner


async def run_full_scan(*, repo_path: str, settings: Settings, run_log: RunLog) -> ScanResult:
    """Run the LLM-driven review and the SCA dependency scan, merged into one result."""
    llm_result = await run_security_scan(repo_path=repo_path, settings=settings, run_log=run_log)
    sca_findings = run_osv_scanner(repo_path)

    combined = ScanResult(findings=[*llm_result.findings, *sca_findings])
    run_log.findings_count = len(combined.findings)
    return combined
