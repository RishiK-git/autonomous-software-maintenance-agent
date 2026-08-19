"""Dependency/CVE scanning via the osv-scanner CLI (github.com/google/osv-scanner).

Runs as a subprocess. If osv-scanner isn't installed, the scan skips
gracefully (warning logged, no findings) rather than failing the whole run —
this is optional tooling layered on top of the LLM-driven review, not a hard
requirement (see docs/roadmap.md Phase 1b).
"""

from __future__ import annotations

import json
import shutil
import subprocess

from ..findings import Finding, FindingSource, Severity
from ..logging_utils import logger

_SEVERITY_MAP: dict[str, Severity] = {
    "CRITICAL": Severity.critical,
    "HIGH": Severity.high,
    "MODERATE": Severity.medium,
    "MEDIUM": Severity.medium,
    "LOW": Severity.low,
}
# A known CVE with no machine-readable severity is treated as high until a
# human triages it — better to over-report than silently downgrade.
_DEFAULT_SEVERITY = Severity.high

_SCAN_TIMEOUT_SECONDS = 300


def is_available() -> bool:
    return shutil.which("osv-scanner") is not None


def run_osv_scanner(repo_path: str) -> list[Finding]:
    """Run osv-scanner against repo_path and return findings for known CVEs.

    Returns an empty list (with a logged warning) if osv-scanner isn't
    installed, times out, or its output can't be parsed. Dependency scanning
    augments the LLM review; its absence shouldn't fail the whole run.
    """
    if not is_available():
        logger.warning(
            "osv-scanner not found on PATH; skipping dependency scan. "
            "Install it (https://github.com/google/osv-scanner) to enable this."
        )
        return []

    try:
        proc = subprocess.run(
            ["osv-scanner", "scan", "source", "-r", repo_path, "--format", "json"],
            capture_output=True,
            text=True,
            timeout=_SCAN_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        logger.warning("osv-scanner timed out; skipping dependency findings for this run")
        return []
    except OSError as exc:
        logger.warning("failed to run osv-scanner: %s", exc)
        return []

    # osv-scanner exits non-zero when it FINDS vulnerabilities, not just on
    # error — so a non-zero return code alone doesn't mean failure. Parse
    # stdout as JSON regardless of return code, and only treat this as a
    # genuine failure if that parse fails.
    try:
        data = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        logger.warning(
            "could not parse osv-scanner output; skipping dependency findings. stderr: %s",
            proc.stderr.strip()[:500],
        )
        return []

    return _parse_findings(data)


def _parse_findings(data: dict) -> list[Finding]:
    findings: list[Finding] = []
    for result in data.get("results", []):
        source_path = result.get("source", {}).get("path", "")
        for pkg_entry in result.get("packages", []):
            package = pkg_entry.get("package", {})
            pkg_name = package.get("name", "unknown")
            pkg_version = package.get("version", "unknown")
            pkg_ecosystem = package.get("ecosystem", "unknown")

            for vuln in pkg_entry.get("vulnerabilities", []):
                vuln_id = vuln.get("id", "UNKNOWN")
                summary = vuln.get("summary") or vuln.get("details") or "No summary provided."
                aliases = vuln.get("aliases") or []

                findings.append(
                    Finding(
                        title=f"{vuln_id}: {pkg_name}@{pkg_version}",
                        category="vulnerable_dependency",
                        severity=_extract_severity(vuln),
                        confidence=1.0,  # matched against the OSV database, not inferred
                        file_path=source_path or f"{pkg_ecosystem}:{pkg_name}",
                        description=summary,
                        evidence=(
                            f"{pkg_ecosystem} package {pkg_name}@{pkg_version} is affected "
                            f"by {vuln_id} (aliases: {', '.join(aliases) or 'none'})."
                        ),
                        source=FindingSource.sca,
                    )
                )
    return findings


def _extract_severity(vuln: dict) -> Severity:
    db_specific_severity = vuln.get("database_specific", {}).get("severity")
    if isinstance(db_specific_severity, str):
        mapped = _SEVERITY_MAP.get(db_specific_severity.upper())
        if mapped is not None:
            return mapped
    return _DEFAULT_SEVERITY
