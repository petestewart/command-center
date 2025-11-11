"""
Git operations module for Command Center.

Provides wrappers around git commands for use in the TUI,
with proper error handling and logging.
"""

import subprocess
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging


# Set up error logging
def get_error_log_path() -> Path:
    """Get the path to the git operations error log."""
    from ccc.utils import get_ccc_home
    log_dir = get_ccc_home() / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir / "git-operations.log"


# Configure logger
logger = logging.getLogger("ccc.git_operations")
logger.setLevel(logging.DEBUG)

# File handler for errors
file_handler = logging.FileHandler(get_error_log_path())
file_handler.setLevel(logging.ERROR)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)


@dataclass
class GitFile:
    """Represents a file in git status."""

    path: str
    status: str  # 'M' (modified), 'A' (added), '?' (untracked), 'D' (deleted), etc.
    staged: bool = False

    @property
    def display_status(self) -> str:
        """Get human-readable status."""
        status_map = {
            "M": "Modified",
            "A": "Added",
            "D": "Deleted",
            "R": "Renamed",
            "C": "Copied",
            "U": "Unmerged",
            "?": "Untracked",
        }
        return status_map.get(self.status, "Unknown")


@dataclass
class GitCommit:
    """Represents a git commit."""

    hash: str
    short_hash: str
    author: str
    date: str
    message: str


@dataclass
class GitOperationResult:
    """Result of a git operation."""

    success: bool
    message: str
    output: str = ""
    error: str = ""


def run_git_command(
    args: List[str], cwd: Path, capture_output: bool = True
) -> Tuple[int, str, str]:
    """
    Run a git command and return the result.

    Args:
        args: Git command arguments (excluding 'git')
        cwd: Working directory to run the command in
        capture_output: Whether to capture stdout/stderr

    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=capture_output,
            text=True,
            timeout=30,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timed out after 30 seconds"
    except Exception as e:
        return 1, "", str(e)


def get_changed_files(worktree_path: Path) -> Tuple[List[GitFile], Optional[str]]:
    """
    Get list of changed files in the worktree.

    Args:
        worktree_path: Path to the git worktree

    Returns:
        Tuple of (list of GitFile objects, error message if any)
    """
    try:
        # Get staged files
        returncode, stdout, stderr = run_git_command(
            ["diff", "--cached", "--name-status"], worktree_path
        )

        staged_files = {}
        if returncode == 0 and stdout:
            for line in stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        status, path = parts
                        staged_files[path] = GitFile(
                            path=path, status=status[0], staged=True
                        )

        # Get unstaged files
        returncode, stdout, stderr = run_git_command(
            ["diff", "--name-status"], worktree_path
        )

        files_dict = dict(staged_files)  # Start with staged files
        if returncode == 0 and stdout:
            for line in stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        status, path = parts
                        if path not in files_dict:
                            files_dict[path] = GitFile(
                                path=path, status=status[0], staged=False
                            )

        # Get untracked files
        returncode, stdout, stderr = run_git_command(
            ["ls-files", "--others", "--exclude-standard"], worktree_path
        )

        if returncode == 0 and stdout:
            for line in stdout.strip().split("\n"):
                if line and line not in files_dict:
                    files_dict[line] = GitFile(path=line, status="?", staged=False)

        return list(files_dict.values()), None

    except Exception as e:
        error_msg = f"Failed to get changed files: {e}"
        logger.error(error_msg, exc_info=True)
        return [], error_msg


def stage_and_commit(
    worktree_path: Path, files: List[str], message: str, remote: str = "origin"
) -> GitOperationResult:
    """
    Stage selected files and create a commit.

    Args:
        worktree_path: Path to the git worktree
        files: List of file paths to stage
        message: Commit message
        remote: Git remote name (for determining branch)

    Returns:
        GitOperationResult indicating success or failure
    """
    try:
        # Validate inputs
        if not files:
            return GitOperationResult(
                success=False, message="No files selected to commit"
            )

        if not message or not message.strip():
            return GitOperationResult(
                success=False, message="Commit message cannot be empty"
            )

        # Stage files
        returncode, stdout, stderr = run_git_command(
            ["add"] + files, worktree_path
        )

        if returncode != 0:
            error_msg = f"Failed to stage files: {stderr}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message=error_msg, error=stderr)

        # Create commit
        returncode, stdout, stderr = run_git_command(
            ["commit", "-m", message], worktree_path
        )

        if returncode != 0:
            error_msg = f"Failed to create commit: {stderr}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message=error_msg, error=stderr)

        return GitOperationResult(
            success=True,
            message="Commit created successfully",
            output=stdout,
        )

    except Exception as e:
        error_msg = f"Unexpected error during commit: {e}"
        logger.error(error_msg, exc_info=True)
        return GitOperationResult(success=False, message=error_msg, error=str(e))


def push_to_remote(
    worktree_path: Path, remote: str = "origin", branch: Optional[str] = None
) -> GitOperationResult:
    """
    Push commits to remote repository.

    Args:
        worktree_path: Path to the git worktree
        remote: Remote name (default: origin)
        branch: Branch name (if None, uses current branch)

    Returns:
        GitOperationResult indicating success or failure
    """
    try:
        # Get current branch if not specified
        if branch is None:
            returncode, stdout, stderr = run_git_command(
                ["branch", "--show-current"], worktree_path
            )
            if returncode != 0:
                error_msg = f"Failed to get current branch: {stderr}"
                logger.error(error_msg)
                return GitOperationResult(success=False, message=error_msg, error=stderr)
            branch = stdout.strip()

        # Push to remote
        returncode, stdout, stderr = run_git_command(
            ["push", remote, branch], worktree_path
        )

        if returncode != 0:
            error_msg = f"Failed to push to {remote}/{branch}: {stderr}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message=error_msg, error=stderr)

        return GitOperationResult(
            success=True,
            message=f"Successfully pushed to {remote}/{branch}",
            output=stdout + stderr,  # Git push writes to stderr
        )

    except Exception as e:
        error_msg = f"Unexpected error during push: {e}"
        logger.error(error_msg, exc_info=True)
        return GitOperationResult(success=False, message=error_msg, error=str(e))


def pull_from_remote(
    worktree_path: Path, remote: str = "origin", branch: Optional[str] = None
) -> GitOperationResult:
    """
    Pull changes from remote repository.

    Args:
        worktree_path: Path to the git worktree
        remote: Remote name (default: origin)
        branch: Branch name (if None, uses current branch)

    Returns:
        GitOperationResult indicating success or failure
    """
    try:
        # Get current branch if not specified
        if branch is None:
            returncode, stdout, stderr = run_git_command(
                ["branch", "--show-current"], worktree_path
            )
            if returncode != 0:
                error_msg = f"Failed to get current branch: {stderr}"
                logger.error(error_msg)
                return GitOperationResult(success=False, message=error_msg, error=stderr)
            branch = stdout.strip()

        # Pull from remote
        returncode, stdout, stderr = run_git_command(
            ["pull", remote, branch], worktree_path
        )

        if returncode != 0:
            error_msg = f"Failed to pull from {remote}/{branch}: {stderr}"
            logger.error(error_msg)
            return GitOperationResult(success=False, message=error_msg, error=stderr)

        return GitOperationResult(
            success=True,
            message=f"Successfully pulled from {remote}/{branch}",
            output=stdout + stderr,
        )

    except Exception as e:
        error_msg = f"Unexpected error during pull: {e}"
        logger.error(error_msg, exc_info=True)
        return GitOperationResult(success=False, message=error_msg, error=str(e))


def get_commit_log(
    worktree_path: Path, limit: int = 20
) -> Tuple[List[GitCommit], Optional[str]]:
    """
    Get recent commit log.

    Args:
        worktree_path: Path to the git worktree
        limit: Maximum number of commits to retrieve

    Returns:
        Tuple of (list of GitCommit objects, error message if any)
    """
    try:
        # Format: hash|author|date|message
        format_str = "%H|%h|%an|%ar|%s"
        returncode, stdout, stderr = run_git_command(
            ["log", f"--format={format_str}", f"-{limit}"], worktree_path
        )

        if returncode != 0:
            error_msg = f"Failed to get commit log: {stderr}"
            logger.error(error_msg)
            return [], error_msg

        commits = []
        for line in stdout.strip().split("\n"):
            if line:
                parts = line.split("|", 4)
                if len(parts) == 5:
                    hash_full, hash_short, author, date, message = parts
                    commits.append(
                        GitCommit(
                            hash=hash_full,
                            short_hash=hash_short,
                            author=author,
                            date=date,
                            message=message,
                        )
                    )

        return commits, None

    except Exception as e:
        error_msg = f"Failed to get commit log: {e}"
        logger.error(error_msg, exc_info=True)
        return [], error_msg


def get_current_branch(worktree_path: Path) -> Optional[str]:
    """
    Get the current branch name.

    Args:
        worktree_path: Path to the git worktree

    Returns:
        Branch name or None if failed
    """
    try:
        returncode, stdout, stderr = run_git_command(
            ["branch", "--show-current"], worktree_path
        )
        if returncode == 0:
            return stdout.strip()
        return None
    except Exception:
        return None


def has_uncommitted_changes(worktree_path: Path) -> bool:
    """
    Check if worktree has uncommitted changes.

    Args:
        worktree_path: Path to the git worktree

    Returns:
        True if there are uncommitted changes, False otherwise
    """
    try:
        files, _ = get_changed_files(worktree_path)
        return len(files) > 0
    except Exception:
        return False


def get_commits_ahead(worktree_path: Path, remote: str = "origin") -> int:
    """
    Get the number of commits ahead of remote.

    Args:
        worktree_path: Path to the git worktree
        remote: Remote name

    Returns:
        Number of commits ahead, or 0 if error
    """
    try:
        branch = get_current_branch(worktree_path)
        if not branch:
            return 0

        returncode, stdout, stderr = run_git_command(
            ["rev-list", "--count", f"{remote}/{branch}..HEAD"], worktree_path
        )

        if returncode == 0 and stdout.strip().isdigit():
            return int(stdout.strip())

        return 0
    except Exception:
        return 0
