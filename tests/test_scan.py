"""Tests scan.run_full_scan merges LLM and SCA findings correctly."""

from __future__ import annotations

import pytest

from maintenance_agent import scan as scan_module
from maintenance_agent.config import Settings
from maintenance_agent.findings import Finding, FindingSource, ScanResult, Severity
from maintenance_agent.logging_utils import RunLog


def _settings() -> Settings:
    return Settings(anthropic_api_key="sk-ant-test", github_token="ghp-test")


def _llm_finding() -> Finding:
    return Finding(
        title="Command injection",
        category="command_injection",
        severity=Severity.high,
        confidence=0.9,
        file_path="app.py",
        description="shell=True with user input",
        evidence="subprocess.run(cmd, shell=True)",
        source=FindingSource.llm_review,
    )


def _sca_finding() -> Finding:
    return Finding(
        title="GHSA-xxxx: flask@0.12",
        category="vulnerable_dependency",
        severity=Severity.medium,
        confidence=1.0,
        file_path="requirements.txt",
        description="Known CVE",
        evidence="flask@0.12 affected by GHSA-xxxx",
        source=FindingSource.sca,
    )


@pytest.mark.asyncio
async def test_run_full_scan_merges_llm_and_sca_findings(monkeypatch):
    async def fake_run_security_scan(*, repo_path, settings, run_log, scope_prompt=None):
        return ScanResult(findings=[_llm_finding()])

    def fake_run_osv_scanner(repo_path):
        return [_sca_finding()]

    monkeypatch.setattr(scan_module, "run_security_scan", fake_run_security_scan)
    monkeypatch.setattr(scan_module, "run_osv_scanner", fake_run_osv_scanner)

    run_log = RunLog(model="claude-sonnet-5")
    result = await scan_module.run_full_scan(repo_path=".", settings=_settings(), run_log=run_log)

    assert len(result.findings) == 2
    sources = {f.source for f in result.findings}
    assert sources == {FindingSource.llm_review, FindingSource.sca}
    assert run_log.findings_count == 2


@pytest.mark.asyncio
async def test_run_diff_scan_scopes_prompt_to_diff(monkeypatch):
    captured_prompts = []

    async def fake_run_security_scan(*, repo_path, settings, run_log, scope_prompt=None):
        captured_prompts.append(scope_prompt)
        return ScanResult(findings=[_llm_finding()])

    monkeypatch.setattr(scan_module, "run_security_scan", fake_run_security_scan)
    monkeypatch.setattr(scan_module, "get_changed_files", lambda repo, base, head: ["app.py"])
    monkeypatch.setattr(
        scan_module, "get_diff_text", lambda repo, base, head: "+ vulnerable line"
    )

    run_log = RunLog(model="claude-sonnet-5")
    result = await scan_module.run_diff_scan(
        repo_path=".", base="main", head="HEAD", settings=_settings(), run_log=run_log
    )

    assert len(result.findings) == 1
    assert run_log.findings_count == 1
    assert len(captured_prompts) == 1
    assert "app.py" in captured_prompts[0]
    assert "+ vulnerable line" in captured_prompts[0]


@pytest.mark.asyncio
async def test_run_diff_scan_skips_when_no_changes(monkeypatch):
    called = False

    async def fake_run_security_scan(*, repo_path, settings, run_log, scope_prompt=None):
        nonlocal called
        called = True
        return ScanResult(findings=[])

    monkeypatch.setattr(scan_module, "run_security_scan", fake_run_security_scan)
    monkeypatch.setattr(scan_module, "get_changed_files", lambda repo, base, head: [])

    run_log = RunLog(model="claude-sonnet-5")
    result = await scan_module.run_diff_scan(
        repo_path=".", base="main", head="HEAD", settings=_settings(), run_log=run_log
    )

    assert result.findings == []
    assert called is False  # no point calling the LLM when nothing changed
