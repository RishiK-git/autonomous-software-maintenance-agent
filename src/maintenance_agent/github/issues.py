"""GitHub issue filing for scan findings, with dedup via a fingerprint embedded
in each issue's body.

Uses urllib.request (stdlib) rather than adding an HTTP client dependency —
this is a handful of simple REST calls, not enough surface to justify one.
The LLM never calls this directly; findings are structured output, and this
module is plain deterministic code that decides what to do with them.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass

from ..findings import Finding, FindingSource
from ..logging_utils import logger

API_BASE = "https://api.github.com"
API_VERSION = "2022-11-28"
FINDING_LABEL = "maintenance-agent"
_FINGERPRINT_RE = re.compile(r"<!-- maintenance-agent-fingerprint: ([0-9a-f]{16}) -->")


class GitHubError(Exception):
    """Raised when the GitHub API returns an unexpected response."""


@dataclass
class FiledIssue:
    finding: Finding
    fingerprint: str
    issue_url: str | None  # None if skipped as a duplicate or filing failed
    is_new: bool


def fingerprint(finding: Finding) -> str:
    """A stable identifier for a finding, used to avoid re-filing the same issue.

    SCA findings are keyed by vulnerability ID + package (already unique and
    stable across runs). LLM findings are keyed by category + location, since
    the same real vulnerability should scan to the same file/line each run.
    """
    if finding.source == FindingSource.sca:
        key = f"sca:{finding.title}"
    else:
        key = f"llm:{finding.category}:{finding.file_path}:{finding.line_start}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _request(method: str, path: str, token: str, body: dict | None = None) -> dict | list:
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", API_VERSION)
    if data is not None:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise GitHubError(
            f"GitHub API {method} {path} failed: {exc.code} {detail[:500]}"
        ) from exc
    except urllib.error.URLError as exc:
        raise GitHubError(f"GitHub API {method} {path} unreachable: {exc.reason}") from exc


def list_open_fingerprints(owner: str, repo: str, token: str) -> set[str]:
    """Fingerprints of currently-open findings already filed as issues."""
    fingerprints: set[str] = set()
    page = 1
    while True:
        path = (
            f"/repos/{owner}/{repo}/issues"
            f"?state=open&labels={FINDING_LABEL}&per_page=100&page={page}"
        )
        issues = _request("GET", path, token)
        if not issues:
            break
        for issue in issues:
            if "pull_request" in issue:
                continue  # the issues endpoint also returns PRs; skip them
            match = _FINGERPRINT_RE.search(issue.get("body") or "")
            if match:
                fingerprints.add(match.group(1))
        if len(issues) < 100:
            break
        page += 1
    return fingerprints


def _build_issue_body(finding: Finding, fp: str) -> str:
    location = finding.file_path
    if finding.line_start is not None:
        location += f":{finding.line_start}"
        if finding.line_end is not None and finding.line_end != finding.line_start:
            location += f"-{finding.line_end}"

    return (
        f"**Severity:** {finding.severity.value}\n"
        f"**Category:** {finding.category}\n"
        f"**Confidence:** {finding.confidence:.2f}\n"
        f"**Location:** `{location}`\n"
        f"**Source:** {finding.source.value}\n\n"
        f"### Why this is a problem\n{finding.description}\n\n"
        f"### Evidence\n```\n{finding.evidence}\n```\n\n"
        f"_Filed automatically by the security-scanning agent._\n"
        f"<!-- maintenance-agent-fingerprint: {fp} -->"
    )


def create_issue(owner: str, repo: str, token: str, finding: Finding) -> str:
    """Create a GitHub issue for a finding. Returns the issue's HTML URL."""
    fp = fingerprint(finding)
    body = _build_issue_body(finding, fp)
    severity_label = f"severity:{finding.severity.value}"

    result = _request(
        "POST",
        f"/repos/{owner}/{repo}/issues",
        token,
        body={
            "title": f"[Security] {finding.title}",
            "body": body,
            "labels": [FINDING_LABEL, severity_label],
        },
    )
    return result["html_url"]


def file_findings(
    *, owner: str, repo: str, token: str, findings: list[Finding]
) -> list[FiledIssue]:
    """File a GitHub issue for each finding not already open, deduped by fingerprint."""
    existing = list_open_fingerprints(owner, repo, token)
    seen_this_run: set[str] = set()
    results: list[FiledIssue] = []

    for finding in findings:
        fp = fingerprint(finding)
        if fp in existing or fp in seen_this_run:
            logger.info(
                "skipping duplicate finding (fingerprint %s already open): %s",
                fp,
                finding.title,
            )
            results.append(
                FiledIssue(finding=finding, fingerprint=fp, issue_url=None, is_new=False)
            )
            continue

        try:
            url = create_issue(owner, repo, token, finding)
        except GitHubError as exc:
            logger.error("failed to file issue for %r: %s", finding.title, exc)
            results.append(
                FiledIssue(finding=finding, fingerprint=fp, issue_url=None, is_new=False)
            )
            continue

        seen_this_run.add(fp)
        logger.info("filed issue for %r: %s", finding.title, url)
        results.append(FiledIssue(finding=finding, fingerprint=fp, issue_url=url, is_new=True))

    return results
