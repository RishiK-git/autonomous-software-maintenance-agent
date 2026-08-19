"""Runs a read-only security scan against a repository via the Claude Agent SDK.

The agent explores with Read/Grep/Glob only (no write access, no Bash yet —
Bash for SCA tooling is wired in Phase 1b) and returns findings as structured
output. Filing/deduplicating GitHub issues from those findings is separate,
deterministic code (github/issues.py, Phase 1c) — the LLM never files an
issue directly.
"""

from __future__ import annotations

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    ToolUseBlock,
    query,
)

from ..config import Settings
from ..findings import ScanResult
from ..logging_utils import RunLog, logger

SYSTEM_PROMPT = """You are a security auditor scanning a software repository for \
real, exploitable vulnerabilities — not style issues or theoretical concerns.

Focus areas: injection (SQL/command/XSS), authentication/authorization flaws, \
insecure deserialization, path traversal, SSRF, hardcoded secrets/credentials, \
and other OWASP-style issues.

Use Read, Grep, and Glob to explore the repository as needed — as much or as \
little as the task requires. Do not guess: read the actual code before \
reporting a finding. For each finding, cite the exact file and line range, \
and explain in one or two sentences why it is exploitable in this specific \
code, not just why the pattern is generally risky.

Only report findings you are reasonably confident are real. If you find \
nothing, return an empty findings list rather than inventing issues."""

DEFAULT_SCAN_PROMPT = (
    "Scan this repository for security vulnerabilities. Explore as much of "
    "the codebase as necessary to find real, exploitable issues."
)


async def run_security_scan(
    *,
    repo_path: str,
    settings: Settings,
    run_log: RunLog,
    scope_prompt: str | None = None,
) -> ScanResult:
    """Run a read-only security scan and return structured findings.

    scope_prompt overrides the default "scan the whole repo" instruction —
    used by scan-diff (Phase 1d) to scope the agent to a specific diff.
    """
    options = ClaudeAgentOptions(
        cwd=repo_path,
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["Read", "Grep", "Glob"],
        permission_mode="dontAsk",  # deny anything not in allowed_tools; never prompts
        model=settings.model,
        max_turns=settings.max_turns,
        max_budget_usd=settings.max_cost_per_run_usd,
        output_format={
            "type": "json_schema",
            "schema": ScanResult.model_json_schema(),
        },
    )

    structured_output: object | None = None

    async for message in query(prompt=scope_prompt or DEFAULT_SCAN_PROMPT, options=options):
        if isinstance(message, AssistantMessage):
            run_log.record_turn()
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    run_log.record_tool_call(block.name)
        elif isinstance(message, ResultMessage):
            run_log.finalize_from_usage(
                num_turns=message.num_turns,
                usage=message.usage,
                total_cost_usd=message.total_cost_usd,
            )
            if message.is_error:
                logger.error(
                    "scan ended in error: subtype=%s terminal_reason=%s errors=%s",
                    message.subtype,
                    message.terminal_reason,
                    message.errors,
                )
            structured_output = message.structured_output

    if structured_output is None:
        logger.warning("scan produced no structured output; treating as zero findings")
        return ScanResult(findings=[])

    scan_result = ScanResult.model_validate(structured_output)
    run_log.findings_count = len(scan_result.findings)
    return scan_result
