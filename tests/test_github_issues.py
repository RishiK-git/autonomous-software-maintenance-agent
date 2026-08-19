"""Tests for github/issues.py — mocked HTTP, no live GitHub calls."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse

import pytest

from maintenance_agent.findings import Finding, FindingSource, Severity
from maintenance_agent.github import issues as issues_module


def _finding(**overrides) -> Finding:
    defaults = dict(
        title="Command injection",
        category="command_injection",
        severity=Severity.high,
        confidence=0.9,
        file_path="app.py",
        line_start=10,
        line_end=12,
        description="shell=True with user input",
        evidence="subprocess.run(cmd, shell=True)",
        source=FindingSource.llm_review,
    )
    defaults.update(overrides)
    return Finding(**defaults)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_fingerprint_is_stable_and_deterministic():
    f1 = _finding()
    f2 = _finding()
    assert issues_module.fingerprint(f1) == issues_module.fingerprint(f2)


def test_fingerprint_differs_for_different_findings():
    f1 = _finding(file_path="app.py")
    f2 = _finding(file_path="other.py")
    assert issues_module.fingerprint(f1) != issues_module.fingerprint(f2)


def test_fingerprint_sca_keyed_by_title():
    f1 = _finding(source=FindingSource.sca, title="GHSA-xxxx: flask@0.12")
    f2 = _finding(source=FindingSource.sca, title="GHSA-xxxx: flask@0.12", file_path="different.txt")
    assert issues_module.fingerprint(f1) == issues_module.fingerprint(f2)


def test_list_open_fingerprints_parses_and_paginates(monkeypatch):
    fp = issues_module.fingerprint(_finding())
    page_1 = [
        {"body": f"...<!-- maintenance-agent-fingerprint: {fp} -->"},
        {"body": "no marker here"},
        {"pull_request": {}, "body": f"<!-- maintenance-agent-fingerprint: {'a' * 16} -->"},
    ] + [{"body": ""}] * 97  # pad to 100 to trigger a second page fetch
    page_2: list = []

    calls = []

    def fake_urlopen(req, timeout=30):
        calls.append(req.full_url)
        # Parse the actual `page` query param — a substring check like
        # "page=1" in url is a trap here, since "per_page=100" also contains
        # that substring and would match every page, looping forever.
        page_num = urllib.parse.parse_qs(urllib.parse.urlparse(req.full_url).query)["page"][0]
        if page_num == "1":
            return _FakeResponse(page_1)
        return _FakeResponse(page_2)

    monkeypatch.setattr(issues_module.urllib.request, "urlopen", fake_urlopen)

    result = issues_module.list_open_fingerprints("owner", "repo", "tok")

    assert result == {fp}
    assert len(calls) == 2  # paginated past the 100-item first page


def test_create_issue_returns_html_url(monkeypatch):
    def fake_urlopen(req, timeout=30):
        assert req.get_method() == "POST"
        assert req.get_header("Authorization") == "Bearer tok"
        body = json.loads(req.data.decode())
        assert body["title"].startswith("[Security]")
        assert issues_module.FINDING_LABEL in body["labels"]
        return _FakeResponse({"html_url": "https://github.com/owner/repo/issues/1"})

    monkeypatch.setattr(issues_module.urllib.request, "urlopen", fake_urlopen)

    url = issues_module.create_issue("owner", "repo", "tok", _finding())
    assert url == "https://github.com/owner/repo/issues/1"


def test_request_raises_github_error_on_http_error(monkeypatch):
    def fake_urlopen(req, timeout=30):
        raise urllib.error.HTTPError(
            req.full_url, 401, "Unauthorized", hdrs=None, fp=None
        )

    monkeypatch.setattr(issues_module.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(issues_module.GitHubError):
        issues_module.create_issue("owner", "repo", "bad-token", _finding())


def test_file_findings_skips_already_open_and_within_run_duplicates(monkeypatch):
    existing_finding = _finding(file_path="already_open.py")
    new_finding = _finding(file_path="new.py")
    duplicate_of_new = _finding(file_path="new.py")  # same fingerprint as new_finding

    monkeypatch.setattr(
        issues_module,
        "list_open_fingerprints",
        lambda owner, repo, token: {issues_module.fingerprint(existing_finding)},
    )

    created_urls = iter(["https://github.com/owner/repo/issues/2"])
    monkeypatch.setattr(
        issues_module, "create_issue", lambda owner, repo, token, finding: next(created_urls)
    )

    results = issues_module.file_findings(
        owner="owner",
        repo="repo",
        token="tok",
        findings=[existing_finding, new_finding, duplicate_of_new],
    )

    assert [r.is_new for r in results] == [False, True, False]
    assert results[1].issue_url == "https://github.com/owner/repo/issues/2"
    assert results[0].issue_url is None
    assert results[2].issue_url is None


def test_file_findings_handles_create_issue_failure(monkeypatch):
    finding = _finding()
    monkeypatch.setattr(issues_module, "list_open_fingerprints", lambda owner, repo, token: set())

    def failing_create(owner, repo, token, finding):
        raise issues_module.GitHubError("boom")

    monkeypatch.setattr(issues_module, "create_issue", failing_create)

    results = issues_module.file_findings(owner="owner", repo="repo", token="tok", findings=[finding])

    assert results[0].is_new is False
    assert results[0].issue_url is None
