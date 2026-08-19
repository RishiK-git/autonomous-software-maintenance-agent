"""Tests for sca/osv_scanner.py — no real osv-scanner binary required.

Uses monkeypatch to stub shutil.which / subprocess.run so these run
deterministically regardless of whether osv-scanner is installed.
"""

from __future__ import annotations

import json
import subprocess

from maintenance_agent.findings import FindingSource, Severity
from maintenance_agent.sca import osv_scanner

_SAMPLE_OUTPUT = {
    "results": [
        {
            "source": {"path": "requirements.txt", "type": "lockfile"},
            "packages": [
                {
                    "package": {"name": "flask", "version": "0.12", "ecosystem": "PyPI"},
                    "vulnerabilities": [
                        {
                            "id": "GHSA-5wv5-4vpf-pj6m",
                            "aliases": ["CVE-2019-1010083"],
                            "summary": "Flask before 1.0 denial of service",
                            "database_specific": {"severity": "MODERATE"},
                        },
                        {
                            "id": "GHSA-unspecified-severity",
                            "aliases": [],
                            "summary": "No machine-readable severity",
                        },
                    ],
                }
            ],
        }
    ]
}


def test_is_available_reflects_which(monkeypatch):
    monkeypatch.setattr(osv_scanner.shutil, "which", lambda name: None)
    assert osv_scanner.is_available() is False

    monkeypatch.setattr(osv_scanner.shutil, "which", lambda name: "/usr/local/bin/osv-scanner")
    assert osv_scanner.is_available() is True


def test_run_osv_scanner_skips_gracefully_when_not_installed(monkeypatch):
    monkeypatch.setattr(osv_scanner, "is_available", lambda: False)
    assert osv_scanner.run_osv_scanner(".") == []


def test_run_osv_scanner_parses_findings(monkeypatch):
    monkeypatch.setattr(osv_scanner, "is_available", lambda: True)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout=json.dumps(_SAMPLE_OUTPUT), stderr=""
        )

    monkeypatch.setattr(osv_scanner.subprocess, "run", fake_run)

    findings = osv_scanner.run_osv_scanner(".")

    assert len(findings) == 2
    assert all(f.source == FindingSource.sca for f in findings)
    assert all(f.confidence == 1.0 for f in findings)

    moderate = next(f for f in findings if "GHSA-5wv5" in f.title)
    assert moderate.severity == Severity.medium
    assert "flask@0.12" in moderate.title
    assert moderate.file_path == "requirements.txt"

    unspecified = next(f for f in findings if "unspecified-severity" in f.title)
    assert unspecified.severity == Severity.high  # default when severity is unknown


def test_run_osv_scanner_handles_unparseable_output(monkeypatch):
    monkeypatch.setattr(osv_scanner, "is_available", lambda: True)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args, returncode=1, stdout="not json", stderr="boom"
        )

    monkeypatch.setattr(osv_scanner.subprocess, "run", fake_run)

    assert osv_scanner.run_osv_scanner(".") == []


def test_run_osv_scanner_handles_timeout(monkeypatch):
    monkeypatch.setattr(osv_scanner, "is_available", lambda: True)

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="osv-scanner", timeout=300)

    monkeypatch.setattr(osv_scanner.subprocess, "run", fake_run)

    assert osv_scanner.run_osv_scanner(".") == []


def test_run_osv_scanner_no_vulnerabilities_found(monkeypatch):
    monkeypatch.setattr(osv_scanner, "is_available", lambda: True)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="{}", stderr="")

    monkeypatch.setattr(osv_scanner.subprocess, "run", fake_run)

    assert osv_scanner.run_osv_scanner(".") == []
