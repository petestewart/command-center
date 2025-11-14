"""
Claude Session Management

Manages Claude Code sessions attached to TODO items, running in tmux windows.
"""

import subprocess
import uuid
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass, field, asdict

import yaml
import libtmux

from ccc.utils import get_branch_dir, print_error, print_success, print_info
from ccc.todo import TodoList, TodoItem, list_todos, save_todos


@dataclass
class ClaudeSession:
    """Represents an active Claude Code session attached to a TODO item."""

    session_id: str  # UUID for Claude session
    todo_id: int
    branch_name: str
    tmux_window: int  # Which tmux window (0=agent by default)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "starting"  # "starting", "running", "paused", "completed", "error"
    initial_prompt: Optional[str] = None
    last_activity: Optional[datetime] = None
    last_output_snippet: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for YAML serialization."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        if self.last_activity:
            data["last_activity"] = self.last_activity.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "ClaudeSession":
        """Create from dictionary loaded from YAML."""
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if isinstance(data.get("last_activity"), str):
            data["last_activity"] = datetime.fromisoformat(data["last_activity"])
        return cls(**data)


class ClaudeSessionManager:
    """Manages Claude Code sessions for TODO items."""

    def __init__(self, branch_name: str):
        """
        Initialize session manager for a branch.

        Args:
            branch_name: Branch name (e.g., "feature/IN-413-add-api")
        """
        self.branch_name = branch_name
        self.branch_dir = get_branch_dir(branch_name)
        self.sessions_file = self.branch_dir / "claude-sessions.yaml"
        self.tmux_session_name = f"ccc-{branch_name}"

        try:
            self.tmux_server = libtmux.Server()
        except Exception as e:
            raise RuntimeError(f"Failed to connect to tmux: {e}")

    def _load_sessions(self) -> Dict[str, ClaudeSession]:
        """Load all sessions from disk."""
        if not self.sessions_file.exists():
            return {}

        try:
            with open(self.sessions_file, 'r') as f:
                data = yaml.safe_load(f) or {}

            sessions = {}
            for session_data in data.get('sessions', []):
                session = ClaudeSession.from_dict(session_data)
                sessions[session.session_id] = session

            return sessions
        except Exception as e:
            print_error(f"Failed to load sessions: {e}")
            return {}

    def _save_sessions(self, sessions: Dict[str, ClaudeSession]):
        """Save all sessions to disk."""
        try:
            self.sessions_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'branch': self.branch_name,
                'sessions': [s.to_dict() for s in sessions.values()]
            }

            with open(self.sessions_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            print_error(f"Failed to save sessions: {e}")

    def start_session_for_todo(
        self,
        todo_id: int,
        window_index: int = 0,
        custom_prompt: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Start a new Claude Code session for a TODO item.

        Args:
            todo_id: ID of the TODO item
            window_index: Tmux window index (default: 0 = agent window)
            custom_prompt: Optional custom initial prompt (auto-generated if None)

        Returns:
            Tuple of (session_id, error_message)
            - (session_id, None) on success
            - (None, error_msg) on failure
        """
        # Load TODO item
        todo_list = list_todos(self.branch_name)
        todo_item = todo_list.get_item(todo_id)

        if not todo_item:
            return None, f"TODO #{todo_id} not found"

        # Check if TODO already has an active session
        if todo_item.assigned_agent:
            return None, f"TODO #{todo_id} already assigned to {todo_item.assigned_agent}"

        # Generate session ID
        session_id = str(uuid.uuid4())

        # Build initial prompt
        if custom_prompt:
            prompt = custom_prompt
        else:
            prompt = self._build_todo_prompt(todo_item)

        # Check if tmux session exists
        if not self.tmux_server.has_session(self.tmux_session_name):
            return None, f"Tmux session '{self.tmux_session_name}' not found. Create the ticket first."

        # Get worktree path for this branch
        from ccc.ticket import TicketRegistry
        registry = TicketRegistry()
        ticket = registry.get(self.branch_name)
        if not ticket:
            return None, f"Ticket not found for branch {self.branch_name}"

        # Launch Claude in tmux window
        tmux_session = self.tmux_server.find_where({"session_name": self.tmux_session_name})
        if not tmux_session:
            return None, f"Could not find tmux session {self.tmux_session_name}"

        # Get or create window
        windows = tmux_session.list_windows()
        if window_index >= len(windows):
            # Create new window for this session
            window = tmux_session.new_window(
                window_name=f"claude-{todo_id}",
                start_directory=ticket.worktree_path,
                attach=False
            )
            window_index = window.index
        else:
            window = windows[window_index]

        # Send Claude command to window
        # Using --session-id to maintain conversation continuity
        cmd = f"claude --session-id {session_id}"

        pane = window.list_panes()[0]
        pane.send_keys(f"cd {ticket.worktree_path}", enter=True)
        pane.send_keys(cmd, enter=True)

        # Send initial prompt
        # Wait a moment for Claude to start
        import time
        time.sleep(1)
        pane.send_keys(prompt, enter=True)

        # Create session object
        session = ClaudeSession(
            session_id=session_id,
            todo_id=todo_id,
            branch_name=self.branch_name,
            tmux_window=window_index,
            status="running",
            initial_prompt=prompt,
            last_activity=datetime.now(timezone.utc)
        )

        # Save session
        sessions = self._load_sessions()
        sessions[session_id] = session
        self._save_sessions(sessions)

        # Update TODO item
        todo_item.assigned_agent = f"Claude-{session_id[:8]}"
        if todo_item.status == "not_started":
            todo_item.status = "in_progress"
        save_todos(self.branch_name, todo_list)

        print_success(f"Started Claude session {session_id[:8]} for TODO #{todo_id}")
        print_info(f"Window: {self.tmux_session_name}:{window_index}")

        return session_id, None

    def _build_todo_prompt(self, todo_item: TodoItem) -> str:
        """Build an initial prompt for a TODO item."""
        from ccc.git_status import get_git_status
        from ccc.ticket import TicketRegistry

        registry = TicketRegistry()
        ticket = registry.get(self.branch_name)

        prompt_parts = [
            f"I need help with a task on branch {self.branch_name}.",
            ""
        ]

        if ticket:
            prompt_parts.append(f"Branch Title: {ticket.title}")
            prompt_parts.append("")

        prompt_parts.append(f"Task #{todo_item.id}: {todo_item.description}")
        prompt_parts.append("")

        if todo_item.blocked_by:
            prompt_parts.append(f"Note: This task is blocked by task #{todo_item.blocked_by}")
            prompt_parts.append("")

        prompt_parts.append("Please help me complete this task. Let me know if you need any additional context or have questions.")

        return "\n".join(prompt_parts)

    def resume_session(self, session_id: str) -> Tuple[bool, Optional[str]]:
        """
        Resume an existing Claude session.

        Args:
            session_id: Session UUID to resume

        Returns:
            Tuple of (success, error_message)
        """
        sessions = self._load_sessions()
        session = sessions.get(session_id)

        if not session:
            return False, f"Session {session_id} not found"

        # Check if tmux session exists
        if not self.tmux_server.has_session(self.tmux_session_name):
            return False, f"Tmux session '{self.tmux_session_name}' not found"

        tmux_session = self.tmux_server.find_where({"session_name": self.tmux_session_name})
        if not tmux_session:
            return False, f"Could not find tmux session"

        # Get window
        windows = tmux_session.list_windows()
        if session.tmux_window >= len(windows):
            return False, f"Window {session.tmux_window} not found"

        window = windows[session.tmux_window]
        pane = window.list_panes()[0]

        # Send resume command
        cmd = f"claude --resume {session_id}"
        pane.send_keys(cmd, enter=True)

        # Update session status
        session.status = "running"
        session.last_activity = datetime.now(timezone.utc)
        self._save_sessions(sessions)

        print_success(f"Resumed session {session_id[:8]}")
        return True, None

    def monitor_session(self, session_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Monitor a session's current state by parsing tmux output.

        Args:
            session_id: Session UUID to monitor

        Returns:
            Tuple of (status_dict, error_message)
            status_dict contains: is_active, last_message, files_mentioned, has_error
        """
        sessions = self._load_sessions()
        session = sessions.get(session_id)

        if not session:
            return None, f"Session {session_id} not found"

        # Check if tmux session exists
        if not self.tmux_server.has_session(self.tmux_session_name):
            return None, f"Tmux session not found"

        tmux_session = self.tmux_server.find_where({"session_name": self.tmux_session_name})
        if not tmux_session:
            return None, f"Could not find tmux session"

        # Get window and capture output
        windows = tmux_session.list_windows()
        if session.tmux_window >= len(windows):
            return None, f"Window not found"

        window = windows[session.tmux_window]
        pane = window.list_panes()[0]

        # Capture last 100 lines
        output = pane.cmd('capture-pane', '-p', '-S', '-100').stdout

        # Parse output for indicators
        status = {
            "is_active": self._is_claude_active(output),
            "last_message": self._extract_last_message(output),
            "files_mentioned": self._extract_file_mentions(output),
            "has_error": "Error:" in output or "error" in output.lower(),
            "raw_output": output[-500:]  # Last 500 chars
        }

        # Update session
        session.last_activity = datetime.now(timezone.utc)
        session.last_output_snippet = status["last_message"]
        if status["has_error"]:
            session.status = "error"
        self._save_sessions(sessions)

        return status, None

    def _is_claude_active(self, output: str) -> bool:
        """Check if Claude appears to be active/thinking."""
        active_indicators = [
            "thinking",
            "Working",
            "Let me",
            "I'll",
            "I'm",
            ">",  # Claude Code prompt
        ]
        return any(indicator in output for indicator in active_indicators)

    def _extract_last_message(self, output: str) -> Optional[str]:
        """Extract the most recent message from Claude."""
        lines = output.strip().split('\n')
        # Look for recent non-empty lines
        for line in reversed(lines[-20:]):
            line = line.strip()
            if line and not line.startswith('$') and not line.startswith('#'):
                return line[:100]  # First 100 chars
        return None

    def _extract_file_mentions(self, output: str) -> List[str]:
        """Extract file paths mentioned in output."""
        # Simple pattern to find file paths
        pattern = r'([a-zA-Z0-9_/-]+\.[a-zA-Z]{2,4})'
        matches = re.findall(pattern, output)
        return list(set(matches))[:10]  # Dedupe and limit to 10

    def list_active_sessions(self) -> List[ClaudeSession]:
        """Get all active sessions for this branch."""
        sessions = self._load_sessions()
        active = [s for s in sessions.values() if s.status in ["starting", "running"]]
        return sorted(active, key=lambda s: s.created_at)

    def get_session_for_todo(self, todo_id: int) -> Optional[ClaudeSession]:
        """Get the active session for a TODO item."""
        sessions = self._load_sessions()
        for session in sessions.values():
            if session.todo_id == todo_id and session.status in ["starting", "running"]:
                return session
        return None

    def stop_session(self, session_id: str) -> Tuple[bool, Optional[str]]:
        """
        Mark a session as stopped/completed.

        Args:
            session_id: Session UUID to stop

        Returns:
            Tuple of (success, error_message)
        """
        sessions = self._load_sessions()
        session = sessions.get(session_id)

        if not session:
            return False, f"Session {session_id} not found"

        session.status = "completed"
        self._save_sessions(sessions)

        # Update TODO item
        todo_list = list_todos(self.branch_name)
        todo_item = todo_list.get_item(session.todo_id)
        if todo_item:
            todo_item.assigned_agent = None
            save_todos(self.branch_name, todo_list)

        print_success(f"Stopped session {session_id[:8]}")
        return True, None
