"""
Unit tests for git_status module.
"""

import pytest
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from ccc.git_status import (
    GitStatus,
    get_git_status,
    clear_git_status_cache,
    format_git_status,
    _git_status_cache,
)


class TestGitStatus:
    """Tests for GitStatus dataclass."""

    def test_git_status_creation(self):
        """Test creating a GitStatus instance."""
        now = datetime.now(timezone.utc)
        status = GitStatus(
            modified_files=["file1.py", "file2.py"],
            untracked_files=["file3.py"],
            commits_ahead=2,
            current_branch="feature/test",
            last_commit="Initial commit",
            last_commit_time=now,
        )

        assert len(status.modified_files) == 2
        assert len(status.untracked_files) == 1
        assert status.commits_ahead == 2
        assert status.current_branch == "feature/test"
        assert status.last_commit == "Initial commit"
        assert status.last_commit_time == now

    def test_git_status_to_dict(self):
        """Test converting GitStatus to dictionary."""
        now = datetime.now(timezone.utc)
        status = GitStatus(
            modified_files=["file1.py"],
            untracked_files=[],
            commits_ahead=1,
            current_branch="main",
            last_commit="Test commit",
            last_commit_time=now,
        )

        data = status.to_dict()

        assert data["modified_files"] == ["file1.py"]
        assert data["untracked_files"] == []
        assert data["commits_ahead"] == 1
        assert data["current_branch"] == "main"
        assert data["last_commit"] == "Test commit"
        assert data["last_commit_time"] == now.isoformat()

    def test_git_status_to_dict_no_timestamp(self):
        """Test converting GitStatus to dict without timestamp."""
        status = GitStatus(
            modified_files=[],
            untracked_files=[],
            commits_ahead=0,
            current_branch="main",
            last_commit="No commits",
            last_commit_time=None,
        )

        data = status.to_dict()

        assert data["last_commit_time"] is None


class TestGetGitStatus:
    """Tests for get_git_status function."""

    @patch("subprocess.run")
    def test_get_git_status_success(self, mock_run):
        """Test successfully getting git status."""
        # Mock subprocess responses
        mock_run.side_effect = [
            # git rev-parse --abbrev-ref HEAD (current branch)
            MagicMock(stdout="feature/test\n", returncode=0),
            # git diff --name-only HEAD (modified files)
            MagicMock(stdout="file1.py\nfile2.py\n", returncode=0),
            # git ls-files --others --exclude-standard (untracked)
            MagicMock(stdout="file3.py\n", returncode=0),
            # git rev-parse --abbrev-ref @{upstream} (upstream branch)
            MagicMock(stdout="origin/feature/test\n", returncode=0),
            # git rev-list --count (commits ahead)
            MagicMock(stdout="2\n", returncode=0),
            # git log -1 --format=%s|||%ct (last commit)
            MagicMock(stdout="Test commit|||1699000000\n", returncode=0),
        ]

        status = get_git_status("/tmp/worktree", use_cache=False)

        assert status is not None
        assert status.current_branch == "feature/test"
        assert status.modified_files == ["file1.py", "file2.py"]
        assert status.untracked_files == ["file3.py"]
        assert status.commits_ahead == 2
        assert status.last_commit == "Test commit"
        assert status.last_commit_time is not None

    @patch("subprocess.run")
    def test_get_git_status_no_upstream(self, mock_run):
        """Test getting git status without upstream branch."""
        mock_run.side_effect = [
            MagicMock(stdout="main\n", returncode=0),
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout="", returncode=0),
            # No upstream branch
            MagicMock(stdout="", returncode=1),
            MagicMock(stdout="Initial commit|||1699000000\n", returncode=0),
        ]

        status = get_git_status("/tmp/worktree", use_cache=False)

        assert status is not None
        assert status.commits_ahead == 0

    @patch("subprocess.run")
    def test_get_git_status_no_commits(self, mock_run):
        """Test getting git status with no commits."""
        mock_run.side_effect = [
            MagicMock(stdout="main\n", returncode=0),
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout="file1.py\n", returncode=0),
            MagicMock(stdout="", returncode=1),
            # No commits
            MagicMock(stdout="", returncode=1),
        ]

        status = get_git_status("/tmp/worktree", use_cache=False)

        assert status is not None
        assert status.last_commit == "No commits"
        assert status.last_commit_time is None

    @patch("subprocess.run")
    def test_get_git_status_git_error(self, mock_run):
        """Test getting git status with git command error."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "git")

        status = get_git_status("/tmp/worktree", use_cache=False)

        assert status is None

    @patch("subprocess.run")
    def test_get_git_status_exception(self, mock_run):
        """Test getting git status with exception."""
        mock_run.side_effect = Exception("Unexpected error")

        status = get_git_status("/tmp/worktree", use_cache=False)

        assert status is None

    @patch("subprocess.run")
    def test_get_git_status_empty_lists(self, mock_run):
        """Test getting git status with no changes."""
        mock_run.side_effect = [
            MagicMock(stdout="main\n", returncode=0),
            MagicMock(stdout="\n", returncode=0),  # Empty modified
            MagicMock(stdout="\n", returncode=0),  # Empty untracked
            MagicMock(stdout="origin/main\n", returncode=0),
            MagicMock(stdout="0\n", returncode=0),
            MagicMock(stdout="Clean commit|||1699000000\n", returncode=0),
        ]

        status = get_git_status("/tmp/worktree", use_cache=False)

        assert status is not None
        assert status.modified_files == []
        assert status.untracked_files == []
        assert status.commits_ahead == 0


class TestGitStatusCache:
    """Tests for git status caching."""

    def setup_method(self):
        """Clear cache before each test."""
        _git_status_cache.clear()

    def teardown_method(self):
        """Clear cache after each test."""
        _git_status_cache.clear()

    @patch("subprocess.run")
    def test_get_git_status_with_cache(self, mock_run):
        """Test that caching works."""
        mock_run.side_effect = [
            MagicMock(stdout="main\n", returncode=0),
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout="", returncode=1),
            MagicMock(stdout="Test|||1699000000\n", returncode=0),
        ]

        # First call - should hit subprocess
        status1 = get_git_status("/tmp/worktree", use_cache=True, cache_seconds=10)
        assert status1 is not None

        # Second call - should use cache
        status2 = get_git_status("/tmp/worktree", use_cache=True, cache_seconds=10)
        assert status2 is not None

        # Should only call subprocess once (for first call)
        assert mock_run.call_count == 5  # 5 git commands in first call

    @patch("subprocess.run")
    def test_get_git_status_cache_expiry(self, mock_run):
        """Test that cache expires with 0 second cache."""
        mock_run.side_effect = [
            # First call
            MagicMock(stdout="main\n", returncode=0),
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout="", returncode=1),
            MagicMock(stdout="Test|||1699000000\n", returncode=0),
            # Second call
            MagicMock(stdout="main\n", returncode=0),
            MagicMock(stdout="file.py\n", returncode=0),
            MagicMock(stdout="", returncode=0),
            MagicMock(stdout="", returncode=1),
            MagicMock(stdout="Test2|||1699000001\n", returncode=0),
        ]

        # First call with 0 second cache
        status1 = get_git_status("/tmp/worktree", use_cache=True, cache_seconds=0)
        assert status1 is not None

        # Second call should re-fetch due to 0 second cache
        status2 = get_git_status("/tmp/worktree", use_cache=True, cache_seconds=0)
        assert status2 is not None

        # Should have called subprocess for both
        assert mock_run.call_count == 10

    def test_clear_git_status_cache_specific(self):
        """Test clearing cache for specific worktree."""
        _git_status_cache["/tmp/wt1"] = ("status1", datetime.now(timezone.utc))
        _git_status_cache["/tmp/wt2"] = ("status2", datetime.now(timezone.utc))

        clear_git_status_cache("/tmp/wt1")

        assert "/tmp/wt1" not in _git_status_cache
        assert "/tmp/wt2" in _git_status_cache

    def test_clear_git_status_cache_all(self):
        """Test clearing all cache."""
        _git_status_cache["/tmp/wt1"] = ("status1", datetime.now(timezone.utc))
        _git_status_cache["/tmp/wt2"] = ("status2", datetime.now(timezone.utc))

        clear_git_status_cache()

        assert len(_git_status_cache) == 0


class TestFormatGitStatus:
    """Tests for formatting git status."""

    def test_format_git_status_basic(self):
        """Test formatting basic git status."""
        now = datetime.now(timezone.utc)
        status = GitStatus(
            modified_files=["file1.py", "file2.py"],
            untracked_files=["file3.py"],
            commits_ahead=2,
            current_branch="feature/test",
            last_commit="Test commit",
            last_commit_time=now,
        )

        formatted = format_git_status(status)

        assert "Branch: feature/test" in formatted
        assert "Modified: 2 files" in formatted
        assert "Untracked: 1 files" in formatted
        assert "Commits ahead: 2" in formatted
        assert "Test commit" in formatted

    def test_format_git_status_no_changes(self):
        """Test formatting git status with no changes."""
        now = datetime.now(timezone.utc)
        status = GitStatus(
            modified_files=[],
            untracked_files=[],
            commits_ahead=0,
            current_branch="main",
            last_commit="Clean commit",
            last_commit_time=now,
        )

        formatted = format_git_status(status)

        assert "Branch: main" in formatted
        assert "Modified: 0 files" in formatted
        assert "Untracked: 0 files" in formatted
        assert "Commits ahead: 0" in formatted

    def test_format_git_status_no_timestamp(self):
        """Test formatting git status without timestamp."""
        status = GitStatus(
            modified_files=["file.py"],
            untracked_files=[],
            commits_ahead=0,
            current_branch="main",
            last_commit="No commits",
            last_commit_time=None,
        )

        formatted = format_git_status(status)

        assert "Branch: main" in formatted
        assert "No commits" in formatted
