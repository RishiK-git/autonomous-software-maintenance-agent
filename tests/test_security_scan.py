"""Tests security_scan.run_security_scan against a mocked Agent SDK query().

No live API calls — mirrors the project's "deterministic fixtures over real
repositories/APIs" testing principle.
"""

from __future__ import annotations

import pytest
from claude_agent_sdk import AssistantMessage, ResultMessage, ToolUseBlock

from maintenance_agent.agent import security_scan
from maintenance_agent.config import Settings
from maintenance_agent.logging_utils import RunLog


def _settings() -> Settings:
    return Settings(anthropic_api_key="sk-ant-test", github_token="ghp-test")


async def _fake_query_with_finding(*, prompt, options):
    yield AssistantMessage(
        content=[ToolUseBlock(id="tu_1", name="Grep", input={"pattern": "subprocess"})],
        model="claude-sonnet-5",
    )
    yield ResultMessage(
        subtype="success",
        duration_ms=1200,
        duration_api_ms=1000,
        is_error=False,
        num_turns=1,
        session_id="sess_1",
        total_cost_usd=0.0123,
        usage={"input_tokens": 500, "output_tokens": 200, "cache_read_input_tokens": 0},
        structured_output={
            "findings": [
                {
                    "title": "Command injection via unsanitized input",
                    "category": "command_injection",
                    "severity": "high",
                    "confidence": 0.9,
                    "file_path": "app.py",
                    "line_start": 10,
                    "line_end": 12,
                    "description": "User input is passed to subprocess with shell=True.",
                    "evidence": "subprocess.run(cmd, shell=True)",
                }
            ]
        },
    )


async def _fake_query_no_findings(*, prompt, options):
    yield ResultMessage(
        subtype="success",
        duration_ms=500,
        duration_api_ms=400,
        is_error=False,
        num_turns=1,
        session_id="sess_2",
        total_cost_usd=0.004,
        usage={"input_tokens": 300, "output_tokens": 50},
        structured_output={"findings": []},
    )


@pytest.mark.asyncio
async def test_run_security_scan_parses_findings(monkeypatch):
    monkeypatch.setattr(security_scan, "query", _fake_query_with_finding)
    run_log = RunLog(model="claude-sonnet-5")

    result = await security_scan.run_security_scan(
        repo_path=".", settings=_settings(), run_log=run_log
    )

    assert len(result.findings) == 1
    finding = result.findings[0]
    assert finding.category == "command_injection"
    assert finding.severity.value == "high"
    assert finding.file_path == "app.py"

    assert run_log.findings_count == 1
    assert run_log.turns_used == 1
    assert "Grep" in run_log.tool_calls
    cost, is_estimated = run_log.cost_usd()
    assert cost == pytest.approx(0.0123)
    assert is_estimated is False


@pytest.mark.asyncio
async def test_run_security_scan_no_findings(monkeypatch):
    monkeypatch.setattr(security_scan, "query", _fake_query_no_findings)
    run_log = RunLog(model="claude-sonnet-5")

    result = await security_scan.run_security_scan(
        repo_path=".", settings=_settings(), run_log=run_log
    )

    assert result.findings == []
    assert run_log.findings_count == 0
