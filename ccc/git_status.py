"""
Git status querying and caching for tickets.
"""

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass, asdict

# Simple in-memory cache
_git_status_cache = {}


@dataclass
class GitStatus:
    """Represents the current git status of a worktree."""

    modified_files: List[str]
    untracked_files: List[str]
    commits_ahead: int
    current_branch: str
    last_commit: str
    last_commit_time: Optional[datetime]

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.last_commit_time:
            data["last_commit_time"] = self.last_commit_time.isoformat()
        return data


def get_git_status(worktree_path: str, use_cache: bool = True, cache_seconds: int = 10) -> Optional[GitStatus]:
    """
    Query git for status information.

    Args:
        worktree_path: Path to the git worktree
        use_cache: Whether to use cached results
        cache_seconds: How long to cache results (default 10 seconds)

    Returns:
        GitStatus object or None if error
    """
    worktree_path = str(worktree_path)

    # Check cache
    if use_cache and worktree_path in _git_status_cache:
        cached_status, cached_time = _git_status_cache[worktree_path]
        age = (datetime.now(timezone.utc) - cached_time).total_seconds()
        if age < cache_seconds:
            return cached_status

    try:
        # Get current branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=True,
        )
        current_branch = result.stdout.strip()

        # Get modified files (both staged and unstaged)
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        modified = [f for f in result.stdout.strip().split('\n') if f]

        # Get untracked files
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        untracked = [f for f in result.stdout.strip().split('\n') if f]

        # Get commits ahead of remote
        # First check if there's a remote tracking branch
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "@{upstream}"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )

        commits_ahead = 0
        if result.returncode == 0:
            upstream = result.stdout.strip()
            # Count commits ahead
            result = subprocess.run(
                ["git", "rev-list", "--count", f"{upstream}..HEAD"],
                cwd=worktree_path,
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                commits_ahead = int(result.stdout.strip()) if result.stdout.strip() else 0

        # Get last commit info
        result = subprocess.run(
            ["git", "log", "-1", "--format=%s|||%ct"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )

        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split('|||')
            if len(parts) == 2:
                last_commit = parts[0]
                last_commit_time = datetime.fromtimestamp(int(parts[1]), tz=timezone.utc)
            else:
                last_commit = "No commits"
                last_commit_time = None
        else:
            last_commit = "No commits"
            last_commit_time = None

        status = GitStatus(
            modified_files=modified,
            untracked_files=untracked,
            commits_ahead=commits_ahead,
            current_branch=current_branch,
            last_commit=last_commit,
            last_commit_time=last_commit_time,
        )

        # Update cache
        _git_status_cache[worktree_path] = (status, datetime.now(timezone.utc))

        return status

    except subprocess.CalledProcessError as e:
        # Git command failed
        return None
    except Exception as e:
        # Other error
        return None


def clear_git_status_cache(worktree_path: Optional[str] = None):
    """
    Clear the git status cache.

    Args:
        worktree_path: Clear cache for specific path, or all if None
    """
    if worktree_path:
        _git_status_cache.pop(str(worktree_path), None)
    else:
        _git_status_cache.clear()


def format_git_status(status: GitStatus) -> str:
    """
    Format git status for display.

    Args:
        status: GitStatus object

    Returns:
        Formatted string
    """
    lines = []
    lines.append(f"Branch: {status.current_branch}")
    lines.append(f"Modified: {len(status.modified_files)} files")
    lines.append(f"Untracked: {len(status.untracked_files)} files")
    lines.append(f"Commits ahead: {status.commits_ahead}")
    lines.append(f"Last commit: \"{status.last_commit}\"")

    if status.last_commit_time:
        from ccc.utils import format_time_ago
        lines.append(f"             {format_time_ago(status.last_commit_time)}")

    return '\n'.join(lines)
