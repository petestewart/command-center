"""
Ticket data structures and persistence
"""

import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict, field

from ccc.utils import (
    get_ccc_home,
    get_tmux_session_name_from_branch,
    extract_display_id,
    print_error,
)


@dataclass
class Ticket:
    """Represents a development ticket tracked by Command Center."""

    # Git branch name - this is the primary unique identifier
    # Examples: "feature/IN-413-add-api", "bugfix/BUG-42", "main"
    branch: str

    # Human-readable title
    title: str

    # Path to git worktree
    worktree_path: str

    # Tmux session name
    tmux_session: str

    # Ticket status: "active", "complete", "blocked"
    status: str = "active"

    # When the ticket was created
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Last time the ticket was updated
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def display_id(self) -> Optional[str]:
        """
        Extract a display ID from the branch name.

        This extracts ticket-like identifiers (e.g., "IN-413" from "feature/IN-413-add-api")
        for display purposes in the UI.

        Returns:
            Extracted ticket ID if found, None otherwise
        """
        return extract_display_id(self.branch)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ticket to dictionary for YAML serialization."""
        data = asdict(self)
        # Convert datetimes to ISO format strings
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Ticket":
        """Create ticket from dictionary (loaded from YAML)."""
        # Parse datetime strings
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("updated_at"), str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])

        return cls(**data)

    def update_timestamp(self):
        """Update the updated_at timestamp to now."""
        self.updated_at = datetime.now(timezone.utc)


class TicketRegistry:
    """Manages the registry of all tickets."""

    def __init__(self):
        self.registry_path = get_ccc_home() / "tickets.yaml"

    def load(self) -> List[Ticket]:
        """Load all tickets from the registry."""
        if not self.registry_path.exists():
            return []

        try:
            with open(self.registry_path, "r") as f:
                data = yaml.safe_load(f) or {}

            tickets_data = data.get("tickets", [])
            return [Ticket.from_dict(t) for t in tickets_data]

        except Exception as e:
            print_error(f"Error loading tickets: {e}")
            return []

    def save(self, tickets: List[Ticket]) -> None:
        """Save all tickets to the registry."""
        try:
            # Ensure directory exists
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert tickets to dictionaries
            data = {"tickets": [t.to_dict() for t in tickets]}

            with open(self.registry_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        except Exception as e:
            print_error(f"Error saving tickets: {e}")
            raise

    def get(self, branch_name: str) -> Optional[Ticket]:
        """Get a specific ticket by branch name."""
        tickets = self.load()
        for ticket in tickets:
            if ticket.branch == branch_name:
                return ticket
        return None

    def exists(self, branch_name: str) -> bool:
        """Check if a ticket exists for the given branch."""
        return self.get(branch_name) is not None

    def add(self, ticket: Ticket) -> None:
        """Add a new ticket to the registry."""
        tickets = self.load()

        # Check for duplicates
        if any(t.branch == ticket.branch for t in tickets):
            raise ValueError(f"Ticket for branch '{ticket.branch}' already exists")

        tickets.append(ticket)
        self.save(tickets)

    def update(self, ticket: Ticket) -> None:
        """Update an existing ticket in the registry."""
        tickets = self.load()

        # Find and replace the ticket
        updated = False
        for i, t in enumerate(tickets):
            if t.branch == ticket.branch:
                ticket.update_timestamp()
                tickets[i] = ticket
                updated = True
                break

        if not updated:
            raise ValueError(f"Ticket for branch '{ticket.branch}' not found")

        self.save(tickets)

    def delete(self, branch_name: str) -> None:
        """Remove a ticket from the registry by branch name."""
        tickets = self.load()
        tickets = [t for t in tickets if t.branch != branch_name]
        self.save(tickets)

    def list_all(self) -> List[Ticket]:
        """Get all tickets."""
        return self.load()

    def list_active(self) -> List[Ticket]:
        """Get all active tickets."""
        return [t for t in self.load() if t.status == "active"]

    def list_by_status(self, status: str) -> List[Ticket]:
        """Get tickets by status."""
        return [t for t in self.load() if t.status == status]


def create_ticket(
    branch: str,
    title: str,
    worktree_path: str,
    tmux_session: Optional[str] = None,
) -> Ticket:
    """
    Create a new ticket instance.

    Args:
        branch: Git branch name (primary identifier)
        title: Ticket title
        worktree_path: Path to worktree
        tmux_session: Tmux session name (optional, will be generated if not provided)

    Returns:
        New Ticket instance
    """
    if tmux_session is None:
        tmux_session = get_tmux_session_name_from_branch(branch)

    return Ticket(
        branch=branch,
        title=title,
        worktree_path=str(worktree_path),
        tmux_session=tmux_session,
    )
