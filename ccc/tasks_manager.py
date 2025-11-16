"""
Tasks Manager - Read and parse project task list from TASKS.md

This module provides functionality to:
- Load tasks from TASKS.md file
- Parse markdown checkbox format (- [ ] and - [x])
- Support nested tasks with 2-space indentation
- Auto-reload when file changes (poll every 3 seconds)
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from datetime import datetime


@dataclass
class Task:
    """Represents a single task from TASKS.md."""

    text: str
    completed: bool
    indent_level: int = 0


class TasksManager:
    """Manage project task list from TASKS.md.

    This class handles:
    - Loading tasks from TASKS.md
    - Parsing markdown checkbox format
    - Tracking file modification time for auto-reload
    - Handling missing or malformed files gracefully
    """

    # Regex pattern to match markdown checkboxes
    # Matches: ^(\s*)[-*]\s+\[([ xX])\]\s+(.*)$
    # Groups: (1) leading spaces, (2) checkbox state, (3) task text
    CHECKBOX_PATTERN = re.compile(r'^(\s*)[-*]\s+\[([ xX])\]\s+(.*)$')

    def __init__(self, tasks_file: str = "TASKS.md"):
        """Initialize TasksManager.

        Args:
            tasks_file: Path to the TASKS.md file (can be relative or absolute)
        """
        self.tasks_file = Path(tasks_file).resolve()
        self._last_modified: Optional[float] = None
        self._cached_tasks: List[Task] = []

    def load_tasks(self, force_reload: bool = False) -> List[Task]:
        """Load tasks from TASKS.md file.

        This method checks if the file has been modified since the last load.
        If it hasn't changed and force_reload is False, returns cached tasks.

        Args:
            force_reload: If True, reload regardless of file modification time

        Returns:
            List of Task objects
        """
        # Check if file exists
        if not self.tasks_file.exists():
            self._cached_tasks = []
            self._last_modified = None
            return []

        # Get file modification time
        try:
            current_mtime = self.tasks_file.stat().st_mtime
        except OSError:
            # File permission issues or file disappeared
            self._cached_tasks = []
            self._last_modified = None
            return []

        # Return cached tasks if file hasn't changed
        if not force_reload and self._last_modified == current_mtime:
            return self._cached_tasks

        # Load and parse file
        try:
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except OSError:
            # File permission issues
            self._cached_tasks = []
            self._last_modified = None
            return []

        # Parse tasks
        tasks = self._parse_markdown_tasks(content)

        # Update cache
        self._cached_tasks = tasks
        self._last_modified = current_mtime

        return tasks

    def _parse_markdown_tasks(self, content: str) -> List[Task]:
        """Parse markdown checkboxes from content.

        Supported formats:
        - [ ] Task not completed
        - [x] Task completed (lowercase x)
        - [X] Task completed (uppercase X)
        * [ ] Task with asterisk bullet
        * [x] Task completed with asterisk
          - [ ] Nested task (2 spaces)
            - [ ] Double nested (4 spaces)

        Args:
            content: Raw file content

        Returns:
            List of Task objects
        """
        tasks = []

        for line in content.split('\n'):
            match = self.CHECKBOX_PATTERN.match(line)
            if match:
                indent_spaces = len(match.group(1))
                checkbox_state = match.group(2)
                task_text = match.group(3).strip()

                # Calculate indent level (2 spaces = 1 level)
                indent_level = indent_spaces // 2

                # Check if completed (x or X)
                completed = checkbox_state.lower() == 'x'

                tasks.append(Task(
                    text=task_text,
                    completed=completed,
                    indent_level=indent_level
                ))

        return tasks

    def get_file_status(self) -> dict:
        """Get file status information.

        Returns:
            Dictionary with file status:
            - exists: bool
            - path: str
            - last_modified: Optional[datetime]
            - task_count: int
        """
        if not self.tasks_file.exists():
            return {
                'exists': False,
                'path': str(self.tasks_file),
                'last_modified': None,
                'task_count': 0
            }

        try:
            stat_info = self.tasks_file.stat()
            last_modified = datetime.fromtimestamp(stat_info.st_mtime)
        except OSError:
            last_modified = None

        return {
            'exists': True,
            'path': str(self.tasks_file),
            'last_modified': last_modified,
            'task_count': len(self._cached_tasks)
        }

    def get_completion_stats(self) -> dict:
        """Get task completion statistics.

        Returns:
            Dictionary with stats:
            - total: Total number of tasks
            - completed: Number of completed tasks
            - pending: Number of pending tasks
            - completion_percent: Percentage completed (0-100)
        """
        tasks = self._cached_tasks
        total = len(tasks)

        if total == 0:
            return {
                'total': 0,
                'completed': 0,
                'pending': 0,
                'completion_percent': 0
            }

        completed = sum(1 for task in tasks if task.completed)
        pending = total - completed
        completion_percent = int((completed / total) * 100)

        return {
            'total': total,
            'completed': completed,
            'pending': pending,
            'completion_percent': completion_percent
        }
