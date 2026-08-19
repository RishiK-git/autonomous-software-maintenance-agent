"""Orchestrates scans: LLM code review + SCA dependency scanning (full sweep),
or an LLM review scoped to a git diff (diff scan).

Kept out of cli.py so the CLI layer stays thin and this logic is directly
testable, per the project's "business logic separate from the entry point"
principle.
"""

from __future__ import annotations

from .agent.security_scan import run_security_scan
from .config import Settings
from .diff import get_changed_files, get_diff_text
from .findings import ScanResult
from .logging_utils import RunLog, logger
from .sca.osv_scanner import run_osv_scanner

DIFF_SCAN_PROMPT_TEMPLATE = """\
Review the following diff for security vulnerabilities introduced by or \
present in the changed code. Use Read, Grep, and Glob to pull in \
surrounding context from the repository if the diff alone isn't enough to \
judge whether something is exploitable (e.g. how a changed function is \
called elsewhere).

Only report findings in or directly caused by this diff — do not perform a \
general audit of the rest of the repository.

Changed files:
{changed_files}

Diff:
```diff
{diff_text}
```
"""


async def run_full_scan(*, repo_path: str, settings: Settings, run_log: RunLog) -> ScanResult:
    """Run the LLM-driven review and the SCA dependency scan, merged into one result."""
    llm_result = await run_security_scan(repo_path=repo_path, settings=settings, run_log=run_log)
    sca_findings = run_osv_scanner(repo_path)

    combined = ScanResult(findings=[*llm_result.findings, *sca_findings])
    run_log.findings_count = len(combined.findings)
    return combined


async def run_diff_scan(
    *, repo_path: str, base: str, head: str, settings: Settings, run_log: RunLog
) -> ScanResult:
    """Run an LLM review scoped to the diff between base and head.

    No SCA scan here — dependency scanning isn't diff-scopable in a
    meaningful way and is already covered by the periodic full sweep; this
    path stays LLM-only so it's the fast, cheap trigger for every commit/PR.
    """
    changed_files = get_changed_files(repo_path, base, head)
    if not changed_files:
        logger.info("no changes between %s and %s; skipping scan", base, head)
        return ScanResult(findings=[])

    diff_text = get_diff_text(repo_path, base, head)
    scope_prompt = DIFF_SCAN_PROMPT_TEMPLATE.format(
        changed_files="\n".join(f"- {f}" for f in changed_files),
        diff_text=diff_text,
    )

    result = await run_security_scan(
        repo_path=repo_path, settings=settings, run_log=run_log, scope_prompt=scope_prompt
    )
    run_log.findings_count = len(result.findings)
    return result
