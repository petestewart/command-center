"""
Utility functions for Command Center
"""

import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dateutil import tz
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def get_cccc_home() -> Path:
    """
    Get the Command Center home directory (~/.cccc-control).
    Creates it if it doesn't exist.
    """
    ccc_home = Path.home() / ".cccc-control"
    ccc_home.mkdir(exist_ok=True)
    return ccc_home


def get_ticket_dir(ticket_id: str) -> Path:
    """
    Get the directory for a specific ticket's metadata.
    Creates it if it doesn't exist.

    DEPRECATED: Use get_branch_dir() instead for branch-based system.
    """
    ticket_dir = get_cccc_home() / ticket_id
    ticket_dir.mkdir(exist_ok=True)
    return ticket_dir


def sanitize_branch_name(branch_name: str) -> str:
    """
    Sanitize a branch name for use as a directory or file name.

    Replaces slashes with double-underscores and removes/replaces
    characters that might be problematic in file systems.

    Examples:
        - "feature/IN-413-add-api" -> "feature__IN-413-add-api"
        - "bugfix/BUG-42/hotfix" -> "bugfix__BUG-42__hotfix"
    """
    # Replace forward slashes with double underscores
    sanitized = branch_name.replace('/', '__')
    # Replace any other problematic characters
    sanitized = re.sub(r'[<>:"|?*\\]', '_', sanitized)
    return sanitized


def get_branch_dir(branch_name: str) -> Path:
    """
    Get the directory for a specific branch's metadata.
    Creates it if it doesn't exist.

    Branch names are sanitized for filesystem compatibility.
    """
    sanitized = sanitize_branch_name(branch_name)
    branch_dir = get_cccc_home() / sanitized
    branch_dir.mkdir(exist_ok=True)
    return branch_dir


def extract_display_id(branch_name: str) -> Optional[str]:
    """
    Extract a ticket-like identifier from a branch name.

    Searches for patterns like: PREFIX-NUMBER (e.g., IN-413, PROJ-123, BUG-42)

    Examples:
        - "feature/IN-413-add-api" -> "IN-413"
        - "bugfix/BUG-42" -> "BUG-42"
        - "main" -> None
        - "feature/add-new-feature" -> None

    Returns:
        The extracted ticket ID if found, None otherwise
    """
    pattern = r'[A-Z]+-\d+'
    match = re.search(pattern, branch_name)
    return match.group(0) if match else None


def validate_ticket_id(ticket_id: str) -> bool:
    """
    Validate ticket ID format.
    Expected format: PREFIX-NUMBER (e.g., IN-413, PROJ-123)

    DEPRECATED: This validation is no longer needed for branch-based system.
    Branch names can be any valid git branch name.
    """
    pattern = r'^[A-Z]+-\d+$'
    return bool(re.match(pattern, ticket_id))


def format_time_ago(dt: datetime) -> str:
    """
    Format a datetime as a human-readable "time ago" string.

    Examples:
        - "2 minutes ago"
        - "3 hours ago"
        - "2 days ago"
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago" if minutes == 1 else f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago" if hours == 1 else f"{hours}h ago"
    else:
        days = int(seconds / 86400)
        return f"{days}d ago" if days == 1 else f"{days}d ago"


def expand_path(path: str) -> Path:
    """
    Expand a path with ~ and environment variables.
    """
    expanded = os.path.expanduser(os.path.expandvars(path))
    return Path(expanded).resolve()


def print_success(message: str):
    """Print a success message with formatting."""
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str):
    """Print an error message with formatting."""
    console.print(f"[red]✗[/red] {message}", style="bold red")


def print_warning(message: str):
    """Print a warning message with formatting."""
    console.print(f"[yellow]⚠[/yellow] {message}", style="yellow")


def print_info(message: str):
    """Print an info message with formatting."""
    console.print(f"[blue]ℹ[/blue] {message}")


def print_panel(title: str, content: str, style: str = "blue"):
    """Print content in a bordered panel."""
    console.print(Panel(content, title=title, border_style=style))


def confirm(message: str, default: bool = False) -> bool:
    """
    Prompt user for yes/no confirmation.

    Args:
        message: The confirmation message
        default: Default value if user just presses Enter

    Returns:
        True if user confirms, False otherwise
    """
    suffix = " [Y/n]: " if default else " [y/N]: "
    response = console.input(f"{message}{suffix}").strip().lower()

    if not response:
        return default

    return response in ['y', 'yes']


def get_tmux_session_name_from_branch(branch_name: str, prefix: str = "ccc-") -> str:
    """
    Generate tmux session name from a branch name.

    Sanitizes the branch name to be tmux-friendly (replaces slashes with hyphens).

    Examples:
        - "feature/IN-413-add-api" -> "ccc-feature-IN-413-add-api"
        - "bugfix/BUG-42" -> "ccc-bugfix-BUG-42"
    """
    # Replace slashes with hyphens for tmux compatibility
    sanitized = branch_name.replace('/', '-')
    # Remove any other problematic characters
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '-', sanitized)
    return f"{prefix}{sanitized}"


def get_tmux_session_name(ticket_id: str, prefix: str = "ccc-") -> str:
    """
    Generate tmux session name for a ticket.

    DEPRECATED: Use get_tmux_session_name_from_branch() for branch-based system.
    """
    return f"{prefix}{ticket_id}"


def get_branch_name(ticket_id: str, title: Optional[str] = None) -> str:
    """
    Generate git branch name from ticket ID and optional title.

    DEPRECATED: This function is no longer needed in the branch-based system.
    Users will provide the full branch name directly.

    Examples:
        - get_branch_name("IN-413", "Public API bulk uploads")
          -> "feature/IN-413-public-api-bulk-uploads"
        - get_branch_name("BUG-42", "Fix login error")
          -> "feature/BUG-42-fix-login-error"
    """
    branch_parts = ["feature", ticket_id]

    if title:
        # Convert title to lowercase, replace spaces with hyphens, remove special chars
        title_slug = re.sub(r'[^a-z0-9-]', '', title.lower().replace(' ', '-'))
        # Remove multiple consecutive hyphens
        title_slug = re.sub(r'-+', '-', title_slug)
        # Remove leading/trailing hyphens
        title_slug = title_slug.strip('-')
        if title_slug:
            branch_parts.append(title_slug)

    return "/".join(branch_parts)


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate a string to max_length, adding suffix if truncated.
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
