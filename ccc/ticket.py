"""
Ticket data structures and persistence
"""

import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict, field

from ccc.utils import get_cc_home, get_tmux_session_name


@dataclass
class Ticket:
    """Represents a development ticket tracked by Command Center."""

    # Unique ticket identifier (e.g., "IN-413")
    id: str

    # Human-readable title
    title: str

    # Git branch name
    branch: str

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
        self.registry_path = get_cc_home() / "tickets.yaml"

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
            from ccc.utils import print_error

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
            from ccc.utils import print_error

            print_error(f"Error saving tickets: {e}")
            raise

    def get(self, ticket_id: str) -> Optional[Ticket]:
        """Get a specific ticket by ID."""
        tickets = self.load()
        for ticket in tickets:
            if ticket.id == ticket_id:
                return ticket
        return None

    def exists(self, ticket_id: str) -> bool:
        """Check if a ticket exists."""
        return self.get(ticket_id) is not None

    def add(self, ticket: Ticket) -> None:
        """Add a new ticket to the registry."""
        tickets = self.load()

        # Check for duplicates
        if any(t.id == ticket.id for t in tickets):
            raise ValueError(f"Ticket {ticket.id} already exists")

        tickets.append(ticket)
        self.save(tickets)

    def update(self, ticket: Ticket) -> None:
        """Update an existing ticket in the registry."""
        tickets = self.load()

        # Find and replace the ticket
        updated = False
        for i, t in enumerate(tickets):
            if t.id == ticket.id:
                ticket.update_timestamp()
                tickets[i] = ticket
                updated = True
                break

        if not updated:
            raise ValueError(f"Ticket {ticket.id} not found")

        self.save(tickets)

    def delete(self, ticket_id: str) -> None:
        """Remove a ticket from the registry."""
        tickets = self.load()
        tickets = [t for t in tickets if t.id != ticket_id]
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
    ticket_id: str,
    title: str,
    branch: str,
    worktree_path: str,
    tmux_session: Optional[str] = None,
) -> Ticket:
    """
    Create a new ticket instance.

    Args:
        ticket_id: Unique ticket ID
        title: Ticket title
        branch: Git branch name
        worktree_path: Path to worktree
        tmux_session: Tmux session name (optional, will be generated if not provided)

    Returns:
        New Ticket instance
    """
    if tmux_session is None:
        tmux_session = get_tmux_session_name(ticket_id)

    return Ticket(
        id=ticket_id,
        title=title,
        branch=branch,
        worktree_path=str(worktree_path),
        tmux_session=tmux_session,
    )
