"""
Tasks Pane Widget - Display project task list from TASKS.md

This widget provides:
- Read-only display of tasks from TASKS.md
- Visual rendering of completed/pending tasks
- Support for nested task indentation
- Auto-refresh capability when file changes
"""

from typing import Optional
from textual.app import ComposeResult
from textual.widgets import Static
from textual.containers import VerticalScroll, Container
from textual.reactive import reactive
from rich.text import Text

from ccc.tasks_manager import TasksManager, Task


class TasksPane(Static):
    """
    Display project task list from TASKS.md.

    Features:
    - Displays tasks with checkbox indicators
    - Completed: ✓ (green, dim, strikethrough)
    - Pending: ○ (blue, normal)
    - Nested tasks with proper indentation
    - Auto-refreshes when TASKS.md changes
    """

    # Reactive property for tasks manager
    tasks_manager: reactive[Optional[TasksManager]] = reactive(None)

    # CSS for styling
    DEFAULT_CSS = """
    TasksPane {
        width: 100%;
        height: auto;
        border: solid $primary;
        padding: 1 2;
    }

    TasksPane #tasks_header {
        text-style: bold;
        background: $primary;
        color: $text;
        padding: 0 1;
        margin-bottom: 1;
    }

    TasksPane #tasks_list {
        width: 100%;
        height: auto;
        max-height: 20;
        padding: 0;
    }

    TasksPane .task-item {
        width: 100%;
        padding: 0;
        margin: 0;
    }

    TasksPane .no-tasks {
        color: $text-muted;
        text-style: italic;
        padding: 1;
    }

    TasksPane .task-stats {
        color: $text-muted;
        padding-top: 1;
        border-top: solid $primary-lighten-1;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        tasks_manager: TasksManager,
        *args,
        **kwargs
    ):
        """
        Initialize TasksPane.

        Args:
            tasks_manager: TasksManager instance to use for loading tasks
            *args: Additional positional arguments for Static
            **kwargs: Additional keyword arguments for Static
        """
        super().__init__(*args, **kwargs)
        self.tasks_manager = tasks_manager
        self.border_title = "Project Tasks"

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("📋 Tasks", id="tasks_header")
        yield VerticalScroll(id="tasks_list")

    def on_mount(self) -> None:
        """Called when widget is mounted."""
        self.refresh_tasks()

    def refresh_tasks(self) -> None:
        """Refresh the task list from TASKS.md."""
        if not self.tasks_manager:
            return

        # Load tasks from file
        tasks = self.tasks_manager.load_tasks()

        # Get the tasks list container
        tasks_list = self.query_one("#tasks_list", VerticalScroll)

        # Clear existing content
        tasks_list.remove_children()

        # Check if file exists
        file_status = self.tasks_manager.get_file_status()

        if not file_status['exists']:
            # File doesn't exist
            tasks_list.mount(
                Static(
                    "No TASKS.md file found.\nCreate one to track your project tasks!",
                    classes="no-tasks"
                )
            )
            return

        if not tasks:
            # File exists but is empty or has no tasks
            tasks_list.mount(
                Static(
                    "No tasks found in TASKS.md.\n\nAdd tasks using markdown checkboxes:\n"
                    "- [ ] Your task here\n"
                    "- [x] Completed task",
                    classes="no-tasks"
                )
            )
            return

        # Render each task
        for task in tasks:
            task_widget = Static(
                self._render_task(task),
                classes="task-item"
            )
            tasks_list.mount(task_widget)

        # Add completion stats
        stats = self.tasks_manager.get_completion_stats()
        stats_text = self._render_stats(stats)
        tasks_list.mount(
            Static(stats_text, classes="task-stats")
        )

    def _render_task(self, task: Task) -> Text:
        """
        Render a task as rich Text with appropriate styling.

        Args:
            task: Task object to render

        Returns:
            Rich Text object with styled task
        """
        text = Text()

        # Add indentation (2 spaces per level)
        indent = "  " * task.indent_level

        if task.completed:
            # Completed task: ✓ Task text (green, dim, strikethrough)
            text.append(indent)
            text.append("✓ ", style="green dim")
            text.append(task.text, style="green dim strike")
        else:
            # Pending task: ○ Task text (blue, normal)
            text.append(indent)
            text.append("○ ", style="blue")
            text.append(task.text, style="blue")

        return text

    def _render_stats(self, stats: dict) -> Text:
        """
        Render completion statistics.

        Args:
            stats: Dictionary with completion stats

        Returns:
            Rich Text object with formatted stats
        """
        text = Text()

        total = stats['total']
        completed = stats['completed']
        pending = stats['pending']
        percent = stats['completion_percent']

        # Format: "Progress: 5/10 tasks completed (50%)"
        text.append("Progress: ", style="dim")
        text.append(f"{completed}/{total}", style="bold")
        text.append(" tasks completed ", style="dim")
        text.append(f"({percent}%)", style="green" if percent == 100 else "yellow")

        return text

    def watch_tasks_manager(self, tasks_manager: Optional[TasksManager]) -> None:
        """React to tasks_manager changes."""
        if tasks_manager:
            self.refresh_tasks()
