"""Git diff extraction for diff-scoped scanning (scan-diff).

Shells out to `git` directly — no GitPython dependency for something this
simple (list changed files, unified diff text).
"""

from __future__ import annotations

import subprocess

_DIFF_TIMEOUT_SECONDS = 60
# Keeps scan-diff cheap: a huge diff should be scanned via scan-full instead
# of blowing the per-run token/cost budget on diff text alone.
_MAX_DIFF_CHARS = 60_000


class DiffError(Exception):
    """Raised when git diff extraction fails (bad refs, not a git repo, etc.)."""


def get_changed_files(repo_path: str, base: str, head: str) -> list[str]:
    """Paths of files changed between base and head (merge-base diff)."""
    output = _run_git(repo_path, ["diff", "--name-only", f"{base}...{head}"])
    return [line for line in output.splitlines() if line.strip()]


def get_diff_text(repo_path: str, base: str, head: str) -> str:
    """Unified diff text between base and head (merge-base diff)."""
    diff = _run_git(repo_path, ["diff", f"{base}...{head}"])
    if len(diff) > _MAX_DIFF_CHARS:
        diff = diff[:_MAX_DIFF_CHARS] + "\n... (diff truncated for cost control) ..."
    return diff


def _run_git(repo_path: str, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=_DIFF_TIMEOUT_SECONDS,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise DiffError(f"git {' '.join(args)} failed: {exc.stderr.strip()}") from exc
    except subprocess.TimeoutExpired as exc:
        raise DiffError(f"git {' '.join(args)} timed out") from exc
    except OSError as exc:
        raise DiffError(f"failed to run git: {exc}") from exc
    return result.stdout
