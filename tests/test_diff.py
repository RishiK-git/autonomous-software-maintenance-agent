"""Tests for diff.py against a real throwaway git repo (no mocking — git
itself is a deterministic, always-available tool, so this is simpler and
more trustworthy than faking subprocess output)."""

from __future__ import annotations

import subprocess

import pytest

from maintenance_agent.diff import DiffError, get_changed_files, get_diff_text


def _git(repo_path, *args) -> None:
    # -c commit.gpgsign=false: this machine has commit signing configured
    # globally but no non-interactive pinentry, which hangs `git commit`
    # waiting for a passphrase prompt that never arrives. Scoped to this
    # throwaway fixture repo via -c, not a global config change.
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test")

    (repo / "a.txt").write_text("hello\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-m", "initial")
    _git(repo, "tag", "base")

    (repo / "a.txt").write_text("hello\nworld\n")
    (repo / "b.txt").write_text("new file\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "second")
    _git(repo, "tag", "head")

    return repo


def test_get_changed_files(git_repo):
    files = get_changed_files(str(git_repo), "base", "head")
    assert set(files) == {"a.txt", "b.txt"}


def test_get_diff_text_contains_changes(git_repo):
    diff = get_diff_text(str(git_repo), "base", "head")
    assert "a.txt" in diff
    assert "b.txt" in diff
    assert "+world" in diff


def test_get_changed_files_no_changes(git_repo):
    assert get_changed_files(str(git_repo), "head", "head") == []


def test_diff_error_on_bad_ref(git_repo):
    with pytest.raises(DiffError):
        get_changed_files(str(git_repo), "nonexistent-ref", "head")


def test_diff_error_on_non_git_dir(tmp_path):
    not_a_repo = tmp_path / "not_a_repo"
    not_a_repo.mkdir()
    with pytest.raises(DiffError):
        get_changed_files(str(not_a_repo), "base", "head")
