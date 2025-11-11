"""
Build status tracking for tickets.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field

from ccc.utils import get_ticket_dir


@dataclass
class BuildStatus:
    """Represents the build status of a ticket."""

    ticket_id: str
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


def get_build_status_path(ticket_id: str) -> Path:
    """Get the path to the build status file for a ticket."""
    return get_ticket_dir(ticket_id) / "build-status.json"


def read_build_status(ticket_id: str) -> Optional[BuildStatus]:
    """
    Read build status from file.

    Args:
        ticket_id: The ticket ID

    Returns:
        BuildStatus if file exists and is valid, None otherwise
    """
    status_file = get_build_status_path(ticket_id)

    if not status_file.exists():
        return None

    try:
        with open(status_file, "r") as f:
            data = json.load(f)

        return BuildStatus.from_dict(data)

    except Exception as e:
        from ccc.utils import print_warning

        print_warning(f"Error reading build status for {ticket_id}: {e}")
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
        status_file = get_build_status_path(status.ticket_id)

        # Ensure directory exists
        status_file.parent.mkdir(parents=True, exist_ok=True)

        # Update timestamp if not set
        if status.last_build is None:
            status.last_build = datetime.now(timezone.utc)

        with open(status_file, "w") as f:
            json.dump(status.to_dict(), f, indent=2)

        return True

    except Exception as e:
        from ccc.utils import print_error

        print_error(f"Error writing build status: {e}")
        return False


def init_build_status(ticket_id: str) -> None:
    """
    Initialize a build status file for a new ticket.

    Args:
        ticket_id: The ticket ID
    """
    status = BuildStatus(
        ticket_id=ticket_id,
        status="unknown",
    )
    write_build_status(status)


def update_build_status(
    ticket_id: str,
    status: str,
    duration: Optional[int] = None,
    errors: Optional[List[str]] = None,
    warnings: Optional[int] = None,
) -> bool:
    """
    Update build status (helper function for CLI).

    Args:
        ticket_id: The ticket ID
        status: Build status ("passing" or "failing")
        duration: Build duration in seconds
        errors: List of error messages
        warnings: Number of warnings

    Returns:
        True if successful, False otherwise
    """
    # Read existing status or create new
    build_status = read_build_status(ticket_id)
    if build_status is None:
        build_status = BuildStatus(ticket_id=ticket_id, status=status)
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
    from ccc.utils import format_time_ago

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
