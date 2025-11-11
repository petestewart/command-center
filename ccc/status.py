"""
Agent status file handling (Week 3 implementation)

This is a stub for now - will be fully implemented in Week 3 of Phase 1.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from ccc.utils import get_ticket_dir


@dataclass
class AgentStatus:
    """Represents the current status of an agent working on a ticket."""

    ticket_id: str
    status: str  # "idle", "working", "complete", "blocked", "error"
    current_task: Optional[str] = None
    last_update: Optional[datetime] = None
    questions: list = None
    blocked: bool = False
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.questions is None:
            self.questions = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.last_update:
            data["last_update"] = self.last_update.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentStatus":
        """Create from dictionary (loaded from JSON)."""
        if isinstance(data.get("last_update"), str):
            data["last_update"] = datetime.fromisoformat(data["last_update"])
        return cls(**data)


def get_status_file_path(ticket_id: str) -> Path:
    """Get the path to the agent status file for a ticket."""
    return get_ticket_dir(ticket_id) / "agent-status.json"


def read_agent_status(ticket_id: str) -> Optional[AgentStatus]:
    """
    Read agent status from file.

    Args:
        ticket_id: The ticket ID

    Returns:
        AgentStatus if file exists and is valid, None otherwise
    """
    status_file = get_status_file_path(ticket_id)

    if not status_file.exists():
        return None

    try:
        with open(status_file, "r") as f:
            data = json.load(f)

        return AgentStatus.from_dict(data)

    except Exception as e:
        from ccc.utils import print_warning

        print_warning(f"Error reading status file for {ticket_id}: {e}")
        return None


def write_agent_status(status: AgentStatus) -> bool:
    """
    Write agent status to file.

    Args:
        status: The status to write

    Returns:
        True if successful, False otherwise
    """
    try:
        status_file = get_status_file_path(status.ticket_id)

        # Ensure directory exists
        status_file.parent.mkdir(parents=True, exist_ok=True)

        # Update timestamp
        status.last_update = datetime.now(timezone.utc)

        with open(status_file, "w") as f:
            json.dump(status.to_dict(), f, indent=2)

        return True

    except Exception as e:
        from ccc.utils import print_error

        print_error(f"Error writing status file: {e}")
        return False


def init_status_file(ticket_id: str) -> None:
    """
    Initialize a status file for a new ticket.

    Args:
        ticket_id: The ticket ID
    """
    status = AgentStatus(
        ticket_id=ticket_id,
        status="idle",
        current_task="Waiting for agent to start",
    )
    write_agent_status(status)


def update_status(
    ticket_id: str,
    status: str,
    task: Optional[str] = None,
    blocked: bool = False,
    question: Optional[str] = None,
) -> bool:
    """
    Update agent status (helper function for CLI).

    Args:
        ticket_id: The ticket ID
        status: New status value
        task: Current task description
        blocked: Whether the agent is blocked
        question: Question to add to the questions list

    Returns:
        True if successful, False otherwise
    """
    # Read existing status or create new
    agent_status = read_agent_status(ticket_id)
    if agent_status is None:
        agent_status = AgentStatus(ticket_id=ticket_id, status=status)

    # Update fields
    agent_status.status = status
    if task is not None:
        agent_status.current_task = task
    agent_status.blocked = blocked

    if question:
        agent_status.questions.append(
            {"question": question, "asked_at": datetime.now(timezone.utc).isoformat()}
        )

    return write_agent_status(agent_status)
