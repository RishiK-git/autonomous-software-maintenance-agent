"""Structured output models for scan findings.

The agent never calls a "file an issue" tool directly — it returns findings
matching this schema (via ClaudeAgentOptions.output_format), and deterministic
code in github/issues.py decides what to do with them. This keeps the one
side-effecting action (filing a GitHub issue) outside LLM control.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class FindingSource(str, Enum):
    llm_review = "llm_review"
    sca = "sca"  # dependency/CVE scanner — wired in Phase 1b


class Finding(BaseModel):
    title: str = Field(description="Short, specific summary of the vulnerability.")
    category: str = Field(
        description=(
            "Vulnerability category, e.g. sql_injection, command_injection, "
            "hardcoded_secret, path_traversal, ssrf, insecure_deserialization, "
            "broken_auth."
        )
    )
    severity: Severity
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="How confident the agent is this is a real, exploitable issue.",
    )
    file_path: str = Field(description="Path to the affected file, relative to the repo root.")
    line_start: int | None = Field(default=None, description="First affected line, if known.")
    line_end: int | None = Field(default=None, description="Last affected line, if known.")
    description: str = Field(
        description="Why this is exploitable in this specific code, not just a generic risk."
    )
    evidence: str = Field(description="The relevant code excerpt or concrete reasoning.")
    source: FindingSource = FindingSource.llm_review


class ScanResult(BaseModel):
    findings: list[Finding] = Field(default_factory=list)
