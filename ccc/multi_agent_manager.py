"""
Multi-Agent Manager for Phase 3.

Manages multiple concurrent Claude agent sessions with TODO parsing,
progress tracking, and state persistence.

This is the most complex part of Phase 3 - TODO parsing is particularly
fragile and needs to handle multiple formats gracefully.
"""

import json
import re
import fcntl
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from ccc.status import AgentSession, AgentTodo
from ccc.utils import get_branch_dir, print_warning, print_error


class TodoParser:
    """
    Parse TODO lists from Claude agent output.

    CRITICAL: This parser must handle multiple TODO formats gracefully.
    It should NEVER crash on malformed input - always return an empty list
    instead.

    Supported formats:
    - ✓ Task or ✅ Task = completed
    - [x] Task = completed
    - * [x] Task = completed
    - - [x] Task = completed
    - - Task or ○ Task or ⚬ Task = pending
    - [ ] Task = pending
    - * [ ] Task = pending
    - - [ ] Task = pending
    - ✗ Task or ❌ Task = blocked
    """

    # TODO patterns organized by status
    # Each pattern is a tuple of (regex, status, blocked)
    TODO_PATTERNS = [
        # Completed patterns
        (r'^[✓✅]\s+(.+)$', 'completed', False),
        (r'^\[x\]\s+(.+)$', 'completed', False),
        (r'^\[X\]\s+(.+)$', 'completed', False),
        (r'^\*\s+\[x\]\s+(.+)$', 'completed', False),
        (r'^\*\s+\[X\]\s+(.+)$', 'completed', False),
        (r'^-\s+\[x\]\s+(.+)$', 'completed', False),
        (r'^-\s+\[X\]\s+(.+)$', 'completed', False),

        # Blocked patterns (checked before pending to avoid conflicts)
        (r'^[✗❌]\s+(.+)$', 'pending', True),
        (r'^\[!\]\s+(.+)$', 'pending', True),

        # Pending patterns
        (r'^[-⚬○]\s+(.+)$', 'pending', False),
        (r'^\[ \]\s+(.+)$', 'pending', False),
        (r'^\*\s+\[ \]\s+(.+)$', 'pending', False),
        (r'^-\s+\[ \]\s+(.+)$', 'pending', False),
        (r'^\*\s+(.+)$', 'pending', False),  # Fallback for plain bullets
    ]

    # Headers that indicate a TODO section
    TODO_SECTION_HEADERS = [
        r'^#+\s*TODO',
        r'^#+\s*Tasks?',
        r'^#+\s*Plan',
        r'^TODO:',
        r'^Tasks?:',
        r'^Plan:',
        r'^\*\*TODO\*\*',
        r'^\*\*Tasks?\*\*',
        r'^\*\*Plan\*\*',
    ]

    def parse_todo_list(self, text: str) -> List[AgentTodo]:
        """
        Parse TODO list from text.

        This is the main entry point. It extracts the TODO section first,
        then parses individual TODO items.

        Args:
            text: Text containing TODOs (usually agent output)

        Returns:
            List of AgentTodo objects (empty list if no TODOs or error)
        """
        if not text or not text.strip():
            return []

        try:
            # Extract TODO section first
            todo_section = self._extract_todo_section(text)
            if not todo_section:
                # No TODO section found, try parsing the entire text
                todo_section = text

            # Parse individual TODO items
            return self._parse_todo_items(todo_section)

        except Exception as e:
            # NEVER crash on parsing errors - just log and return empty
            print_warning(f"TODO parsing error: {e}")
            return []

    def _extract_todo_section(self, text: str) -> Optional[str]:
        """
        Extract the TODO section from text.

        Looks for headers like "TODO:", "Tasks:", "## TODO", etc.
        Returns text from the header until the next header or end of text.

        Args:
            text: Full text to search

        Returns:
            TODO section text or None if not found
        """
        lines = text.split('\n')
        todo_start_idx = None
        todo_end_idx = None

        # Find TODO section start
        for i, line in enumerate(lines):
            stripped = line.strip()
            for header_pattern in self.TODO_SECTION_HEADERS:
                if re.search(header_pattern, stripped, re.IGNORECASE):
                    todo_start_idx = i + 1  # Start after header
                    break
            if todo_start_idx is not None:
                break

        if todo_start_idx is None:
            return None

        # Find section end (next header or end of text)
        for i in range(todo_start_idx, len(lines)):
            line = lines[i].strip()
            # Check if it's another markdown header
            if line.startswith('#') or line.startswith('##'):
                todo_end_idx = i
                break

        if todo_end_idx is None:
            todo_end_idx = len(lines)

        # Extract section
        section_lines = lines[todo_start_idx:todo_end_idx]
        return '\n'.join(section_lines)

    def _parse_todo_items(self, text: str) -> List[AgentTodo]:
        """
        Parse individual TODO items from text.

        Tries each pattern in order until one matches.

        Args:
            text: Text containing TODO items (one per line)

        Returns:
            List of AgentTodo objects
        """
        todos = []
        lines = text.split('\n')

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Try each pattern
            for pattern, status, blocked in self.TODO_PATTERNS:
                match = re.match(pattern, stripped, re.IGNORECASE)
                if match:
                    text = match.group(1).strip()

                    # Skip if it's too short or looks like a header
                    if len(text) < 3:
                        continue

                    todos.append(AgentTodo(
                        text=text,
                        completed=(status == 'completed'),
                        blocked=blocked,
                    ))
                    break  # Stop after first match

        return todos


class MultiAgentManager:
    """
    Manage multiple concurrent Claude agent sessions.

    Handles:
    - Session registration and tracking
    - TODO parsing from agent output
    - Progress calculation
    - State persistence with atomic writes
    - Graceful error handling

    State File: ~/.ccc-control/branches/{branch}/agent-sessions.json
    """

    def __init__(self, branch_name: str):
        """
        Initialize multi-agent manager for a branch.

        Args:
            branch_name: Git branch name
        """
        self.branch_name = branch_name
        self.branch_dir = get_branch_dir(branch_name)
        self.state_file = self.branch_dir / "agent-sessions.json"
        self.todo_parser = TodoParser()

    def list_sessions(self) -> List[AgentSession]:
        """
        Get all active agent sessions.

        Returns:
            List of AgentSession objects (empty if no sessions or error)
        """
        return self._load_sessions()

    def add_session(self, session: AgentSession) -> None:
        """
        Add a new agent session.

        Args:
            session: AgentSession to add
        """
        sessions = self._load_sessions()

        # Check if session already exists
        for i, existing in enumerate(sessions):
            if existing.id == session.id:
                # Update existing session
                sessions[i] = session
                self._save_sessions(sessions)
                return

        # Add new session
        sessions.append(session)
        self._save_sessions(sessions)

    def update_session(self, session_id: str, **kwargs) -> bool:
        """
        Update an agent session.

        Args:
            session_id: Session ID to update
            **kwargs: Fields to update (status, current_files, etc.)

        Returns:
            True if session was updated, False if not found
        """
        sessions = self._load_sessions()

        for session in sessions:
            if session.id == session_id:
                # Update fields
                for key, value in kwargs.items():
                    if hasattr(session, key):
                        setattr(session, key, value)

                # Update last_active timestamp
                session.last_active = datetime.now(timezone.utc)

                self._save_sessions(sessions)
                return True

        return False

    def remove_session(self, session_id: str) -> bool:
        """
        Remove (archive) an agent session.

        Note: This is manual archival only - no automatic cleanup.

        Args:
            session_id: Session ID to remove

        Returns:
            True if session was removed, False if not found
        """
        sessions = self._load_sessions()
        initial_count = len(sessions)

        sessions = [s for s in sessions if s.id != session_id]

        if len(sessions) < initial_count:
            self._save_sessions(sessions)
            return True

        return False

    def update_todos_from_output(self, session_id: str, output: str) -> bool:
        """
        Parse TODOs from agent output and update session.

        This is called when new output is received from an agent.
        It parses TODOs and updates the session's todo_list and progress.

        Args:
            session_id: Session ID to update
            output: Latest agent output (not entire history!)

        Returns:
            True if session was updated, False if not found
        """
        # Parse TODOs from output
        todos = self.todo_parser.parse_todo_list(output)

        # Update session
        sessions = self._load_sessions()
        for session in sessions:
            if session.id == session_id:
                session.todo_list = todos
                session.progress_percent = self.calculate_progress(session)
                session.last_active = datetime.now(timezone.utc)
                self._save_sessions(sessions)
                return True

        return False

    def calculate_progress(self, session: AgentSession) -> Optional[int]:
        """
        Calculate progress percentage from TODO completion.

        Args:
            session: AgentSession to calculate progress for

        Returns:
            Progress percentage (0-100) or None if no TODOs
        """
        if not session.todo_list:
            return None

        total = len(session.todo_list)
        if total == 0:
            return None

        completed = sum(1 for todo in session.todo_list if todo.completed)
        return int((completed / total) * 100)

    def _load_sessions(self) -> List[AgentSession]:
        """
        Load sessions from state file.

        Returns:
            List of AgentSession objects (empty if no file or error)
        """
        if not self.state_file.exists():
            return []

        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)

            sessions_data = data.get('sessions', [])
            return [AgentSession.from_dict(s) for s in sessions_data]

        except Exception as e:
            # Handle corrupted state file gracefully
            print_warning(f"Failed to load agent sessions: {e}")

            # Try to backup corrupted file
            try:
                backup_path = self.state_file.with_suffix('.json.corrupted')
                self.state_file.rename(backup_path)
                print_warning(f"Corrupted file backed up to: {backup_path}")
            except:
                pass

            return []

    def _save_sessions(self, sessions: List[AgentSession]) -> None:
        """
        Save sessions to state file using atomic write with file locking.

        Args:
            sessions: List of AgentSession objects to save
        """
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Create temp file in same directory
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.state_file.parent,
                prefix=".tmp-agent-sessions-",
                suffix=".json",
            )

            try:
                # Write to temp file with lock
                with os.fdopen(temp_fd, 'w') as f:
                    fcntl.flock(f, fcntl.LOCK_EX)

                    data = {
                        'branch': self.branch_name,
                        'sessions': [s.to_dict() for s in sessions],
                        'last_updated': datetime.now(timezone.utc).isoformat(),
                    }

                    json.dump(data, f, indent=2, default=str)
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic rename
                os.rename(temp_path, self.state_file)

            finally:
                # Cleanup temp file if rename failed
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception as e:
            # Don't crash on save errors - just log
            print_error(f"Failed to save agent sessions: {e}")

    def get_session(self, session_id: str) -> Optional[AgentSession]:
        """
        Get a specific session by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            AgentSession or None if not found
        """
        sessions = self._load_sessions()
        for session in sessions:
            if session.id == session_id:
                return session
        return None
