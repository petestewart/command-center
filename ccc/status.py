"""
Agent status file handling (Week 3 implementation)

This is a stub for now - will be fully implemented in Week 3 of Phase 1.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from ccc.utils import get_branch_dir, print_warning, print_error


@dataclass
class AgentStatus:
    """Represents the current status of an agent working on a branch."""

    branch_name: str
    status: str  # "idle", "working", "complete", "blocked", "error"
    current_task: Optional[str] = None
    current_task_id: Optional[int] = None  # Phase 4: Links to TodoItem.id
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


def get_status_file_path(branch_name: str) -> Path:
    """Get the path to the agent status file for a branch."""
    return get_branch_dir(branch_name) / "agent-status.json"


def read_agent_status(branch_name: str) -> Optional[AgentStatus]:
    """
    Read agent status from file.

    Args:
        branch_name: The branch name

    Returns:
        AgentStatus if file exists and is valid, None otherwise
    """
    status_file = get_status_file_path(branch_name)

    if not status_file.exists():
        return None

    try:
        with open(status_file, "r") as f:
            data = json.load(f)

        return AgentStatus.from_dict(data)

    except Exception as e:
        print_warning(f"Error reading status file for {branch_name}: {e}")
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
        status_file = get_status_file_path(status.branch_name)

        # Ensure directory exists
        status_file.parent.mkdir(parents=True, exist_ok=True)

        # Update timestamp
        status.last_update = datetime.now(timezone.utc)

        with open(status_file, "w") as f:
            json.dump(status.to_dict(), f, indent=2)

        return True

    except Exception as e:
        print_error(f"Error writing status file: {e}")
        return False


def init_status_file(branch_name: str) -> None:
    """
    Initialize a status file for a new branch.

    Args:
        branch_name: The branch name
    """
    status = AgentStatus(
        branch_name=branch_name,
        status="idle",
        current_task="Waiting for agent to start",
    )
    write_agent_status(status)


def update_status(
    branch_name: str,
    status: str,
    task: Optional[str] = None,
    blocked: bool = False,
    question: Optional[str] = None,
) -> bool:
    """
    Update agent status (helper function for CLI).

    Args:
        branch_name: The branch name
        status: New status value
        task: Current task description
        blocked: Whether the agent is blocked
        question: Question to add to the questions list

    Returns:
        True if successful, False otherwise
    """
    # Read existing status or create new
    agent_status = read_agent_status(branch_name)
    if agent_status is None:
        agent_status = AgentStatus(branch_name=branch_name, status=status)

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


# ============================================================================
# Phase 3: Multi-Agent Tracking Data Models
# ============================================================================


@dataclass
class AgentTodo:
    """Represents a TODO item parsed from agent output."""

    text: str
    completed: bool
    blocked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "text": self.text,
            "completed": self.completed,
            "blocked": self.blocked,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTodo":
        """Create from dictionary loaded from JSON."""
        return cls(
            text=data["text"],
            completed=data["completed"],
            blocked=data.get("blocked", False),
        )


@dataclass
class AgentSession:
    """
    Represents a Claude agent session for multi-agent tracking.

    This is used in Phase 3 to track multiple concurrent agents,
    their TODO lists, progress, and terminal references.
    """

    id: str
    todo_id: Optional[str]
    title: str
    status: str  # 'idle', 'working', 'waiting', 'completed', 'error'
    current_files: List[str] = None
    progress_percent: Optional[int] = None
    todo_list: List[AgentTodo] = None
    terminal_ref: Optional[str] = None  # Tmux pane ID
    started_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    error_message: Optional[str] = None

    def __post_init__(self):
        """Initialize default values for mutable fields."""
        if self.current_files is None:
            self.current_files = []
        if self.todo_list is None:
            self.todo_list = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "id": self.id,
            "todo_id": self.todo_id,
            "title": self.title,
            "status": self.status,
            "current_files": self.current_files,
            "progress_percent": self.progress_percent,
            "todo_list": [todo.to_dict() for todo in self.todo_list],
            "terminal_ref": self.terminal_ref,
            "error_message": self.error_message,
        }

        if self.started_at:
            data["started_at"] = self.started_at.isoformat()
        if self.last_active:
            data["last_active"] = self.last_active.isoformat()

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentSession":
        """Create from dictionary loaded from JSON."""
        # Parse datetime fields
        started_at = data.get("started_at")
        if isinstance(started_at, str):
            started_at = datetime.fromisoformat(started_at)

        last_active = data.get("last_active")
        if isinstance(last_active, str):
            last_active = datetime.fromisoformat(last_active)

        # Parse TODO list
        todo_list_data = data.get("todo_list", [])
        todo_list = [AgentTodo.from_dict(todo) for todo in todo_list_data]

        return cls(
            id=data["id"],
            todo_id=data.get("todo_id"),
            title=data["title"],
            status=data["status"],
            current_files=data.get("current_files", []),
            progress_percent=data.get("progress_percent"),
            todo_list=todo_list,
            terminal_ref=data.get("terminal_ref"),
            started_at=started_at,
            last_active=last_active,
            error_message=data.get("error_message"),
        )
