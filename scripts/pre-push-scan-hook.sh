#!/usr/bin/env bash
# Example pre-push git hook: runs a diff-scoped security scan before code
# leaves this machine. Advisory only — never blocks the push, just prints
# findings to stdout. Install with:
#
#   cp scripts/pre-push-scan-hook.sh .git/hooks/pre-push
#   chmod +x .git/hooks/pre-push
#
# Requires ANTHROPIC_API_KEY and GITHUB_TOKEN in the environment, and
# `maintenance-agent` on PATH (activate the project's venv, or
# `pip install -e .`).
#
# This hook deliberately does NOT pass --github-repo — filing issues is the
# GitHub Actions workflow's job on the actual PR (.github/workflows/
# security-scan.yml). This is just a fast, local heads-up before you push,
# scoped to whatever commits are new on the remote.

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
zero_sha="0000000000000000000000000000000000000000"

while read -r local_ref local_sha remote_ref remote_sha; do
    if [ "$local_sha" = "$zero_sha" ]; then
        continue  # branch deletion — nothing to scan
    fi

    if [ "$remote_sha" = "$zero_sha" ]; then
        # New branch with no remote counterpart yet — diff against main.
        base="main"
    else
        base="$remote_sha"
    fi

    echo "Running security scan-diff: ${base}...${local_sha}"
    maintenance-agent scan-diff --repo "$repo_root" --base "$base" --head "$local_sha" || true
done

exit 0
