"""
Build status tracking for tickets.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field

from ccc.utils import get_branch_dir, print_warning, print_error, format_time_ago


@dataclass
class BuildStatus:
    """Represents the build status of a branch."""

    branch_name: str
    status: str  # "passing", "failing", "unknown"
    last_build: Optional[datetime] = None
    duration_seconds: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.last_build:
            data["last_build"] = self.last_build.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BuildStatus":
        """Create from dictionary (loaded from JSON)."""
        if isinstance(data.get("last_build"), str):
            data["last_build"] = datetime.fromisoformat(data["last_build"])
        # Handle missing fields
        if "errors" not in data:
            data["errors"] = []
        if "warnings" not in data:
            data["warnings"] = 0

        return cls(**data)


def get_build_status_path(branch_name: str) -> Path:
    """Get the path to the build status file for a branch."""
    return get_branch_dir(branch_name) / "build-status.json"


def read_build_status(branch_name: str) -> Optional[BuildStatus]:
    """
    Read build status from file.

    Args:
        branch_name: The branch name

    Returns:
        BuildStatus if file exists and is valid, None otherwise
    """
    status_file = get_build_status_path(branch_name)

    if not status_file.exists():
        return None

    try:
        with open(status_file, "r") as f:
            data = json.load(f)

        return BuildStatus.from_dict(data)

    except Exception as e:
        print_warning(f"Error reading build status for {branch_name}: {e}")
        return None


def write_build_status(status: BuildStatus) -> bool:
    """
    Write build status to file.

    Args:
        status: The build status to write

    Returns:
        True if successful, False otherwise
    """
    try:
        status_file = get_build_status_path(status.branch_name)

        # Ensure directory exists
        status_file.parent.mkdir(parents=True, exist_ok=True)

        # Update timestamp if not set
        if status.last_build is None:
            status.last_build = datetime.now(timezone.utc)

        with open(status_file, "w") as f:
            json.dump(status.to_dict(), f, indent=2)

        return True

    except Exception as e:
        print_error(f"Error writing build status: {e}")
        return False


def init_build_status(branch_name: str) -> None:
    """
    Initialize a build status file for a new branch.

    Args:
        branch_name: The branch name
    """
    status = BuildStatus(
        branch_name=branch_name,
        status="unknown",
    )
    write_build_status(status)


def update_build_status(
    branch_name: str,
    status: str,
    duration: Optional[int] = None,
    errors: Optional[List[str]] = None,
    warnings: Optional[int] = None,
) -> bool:
    """
    Update build status (helper function for CLI).

    Args:
        branch_name: The branch name
        status: Build status ("passing" or "failing")
        duration: Build duration in seconds
        errors: List of error messages
        warnings: Number of warnings

    Returns:
        True if successful, False otherwise
    """
    # Read existing status or create new
    build_status = read_build_status(branch_name)
    if build_status is None:
        build_status = BuildStatus(branch_name=branch_name, status=status)
    else:
        build_status.status = status

    # Update fields
    build_status.last_build = datetime.now(timezone.utc)

    if duration is not None:
        build_status.duration_seconds = duration

    if errors is not None:
        build_status.errors = errors

    if warnings is not None:
        build_status.warnings = warnings

    return write_build_status(build_status)


def format_build_status(status: BuildStatus) -> str:
    """
    Format build status for display.

    Args:
        status: BuildStatus object

    Returns:
        Formatted string
    """
    lines = []

    # Status indicator
    if status.status == "passing":
        lines.append("Status: ✓ Passing")
    elif status.status == "failing":
        lines.append("Status: ✗ Failing")
    else:
        lines.append("Status: ? Unknown")

    # Build details
    if status.last_build:
        details = f"Last build: {status.duration_seconds}s"
        if status.warnings > 0:
            details += f", {status.warnings} warnings"
        if status.errors:
            details += f", {len(status.errors)} errors"
        lines.append(details)
        lines.append(f"Completed: {format_time_ago(status.last_build)}")

    # Errors
    if status.errors:
        lines.append("\nErrors:")
        for err in status.errors[:5]:  # Show first 5 errors
            lines.append(f"  • {err}")
        if len(status.errors) > 5:
            lines.append(f"  ... and {len(status.errors) - 5} more")

    return '\n'.join(lines)
