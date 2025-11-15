"""
Custom widgets for Command Center TUI.
"""

from typing import List, Optional, Callable
from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Static, Label, Checkbox, TextArea
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive

from ccc.git_operations import GitFile, GitCommit


class FileCheckboxList(VerticalScroll):
    """
    A scrollable list of files with checkboxes for selection.

    Attributes:
        files: List of GitFile objects to display
        selected_files: Set of currently selected file paths
    """

    BINDINGS = [
        Binding("space", "toggle_selected", "Toggle", show=False),
        Binding("a", "select_all", "Select All", show=True),
        Binding("n", "select_none", "Deselect All", show=True),
    ]

    DEFAULT_CSS = """
    FileCheckboxList {
        width: 100%;
        height: auto;
        max-height: 15;
        border: solid $primary-lighten-1;
        padding: 0 1;
    }

    FileCheckboxList Checkbox {
        width: 100%;
        margin: 0;
    }

    FileCheckboxList .file-status {
        color: $text-muted;
    }
    """

    class SelectionChanged(Message):
        """Posted when file selection changes."""

        def __init__(self, selected_count: int) -> None:
            super().__init__()
            self.selected_count = selected_count

    def __init__(
        self,
        files: List[GitFile],
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the file checkbox list.

        Args:
            files: List of GitFile objects to display
            name: The name of the widget
            id: The ID of the widget in the DOM
            classes: The CSS classes for the widget
        """
        super().__init__(name=name, id=id, classes=classes)
        self.files = files
        self.selected_files: set[str] = set()
        self._checkboxes: dict[str, Checkbox] = {}

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        if not self.files:
            yield Label("[dim]No changed files[/dim]")
        else:
            for file in self.files:
                # Just show the file path without the status label
                label = file.path
                # Create a valid ID by replacing invalid characters
                safe_id = self._sanitize_id(file.path)
                checkbox = Checkbox(label, value=file.staged, id=safe_id)
                self._checkboxes[file.path] = checkbox
                if file.staged:
                    self.selected_files.add(file.path)
                yield checkbox

    def _sanitize_id(self, file_path: str) -> str:
        """
        Convert a file path to a valid Textual ID.

        Replaces invalid characters (/, ., etc.) with underscores and prefixes with 'file'.
        Valid IDs contain only letters, numbers, underscores, and hyphens, and cannot start with a number.
        """
        # Replace invalid characters with underscores
        safe_id = "".join(c if c.isalnum() or c == "-" else "_" for c in file_path)
        # Ensure it starts with a letter
        safe_id = f"file_{safe_id}"
        return safe_id

    def _get_status_color(self, status: str) -> str:
        """Get color for file status."""
        color_map = {
            "M": "yellow",
            "A": "green",
            "D": "red",
            "R": "cyan",
            "?": "blue",
        }
        return color_map.get(status, "white")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle checkbox state changes."""
        # Find the file path by matching the sanitized ID
        file_path = None
        for fp, checkbox in self._checkboxes.items():
            if checkbox.id == event.checkbox.id:
                file_path = fp
                break

        if not file_path:
            return

        if event.value:
            self.selected_files.add(file_path)
        else:
            self.selected_files.discard(file_path)

        self.post_message(self.SelectionChanged(len(self.selected_files)))

    def action_toggle_selected(self) -> None:
        """Toggle the currently focused checkbox."""
        focused = self.screen.focused
        if isinstance(focused, Checkbox):
            focused.toggle()

    def action_select_all(self) -> None:
        """Select all files."""
        for file_path, checkbox in self._checkboxes.items():
            checkbox.value = True
            self.selected_files.add(file_path)
        self.post_message(self.SelectionChanged(len(self.selected_files)))

    def action_select_none(self) -> None:
        """Deselect all files."""
        for checkbox in self._checkboxes.values():
            checkbox.value = False
        self.selected_files.clear()
        self.post_message(self.SelectionChanged(0))

    def get_selected_files(self) -> List[str]:
        """Get list of selected file paths."""
        return list(self.selected_files)


class MultiLineInput(Container):
    """
    A multi-line text input widget for commit messages.

    Uses Textual's TextArea widget with custom styling.
    """

    DEFAULT_CSS = """
    MultiLineInput {
        width: 100%;
        height: auto;
    }

    MultiLineInput TextArea {
        width: 100%;
        height: 10;
        border: solid $primary-lighten-1;
    }

    MultiLineInput .char-count {
        width: 100%;
        text-align: right;
        color: $text-muted;
        margin-top: 0;
    }
    """

    def __init__(
        self,
        placeholder: str = "Enter commit message...",
        min_length: int = 1,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the multi-line input.

        Args:
            placeholder: Placeholder text
            min_length: Minimum message length (default: 1)
            name: The name of the widget
            id: The ID of the widget in the DOM
            classes: The CSS classes for the widget
        """
        super().__init__(name=name, id=id, classes=classes)
        self.placeholder = placeholder
        self.min_length = min_length
        self._text_area: Optional[TextArea] = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        self._text_area = TextArea(id="message-input")
        self._text_area.show_line_numbers = False
        yield self._text_area
        yield Label("", classes="char-count", id="char-count")

    def on_mount(self) -> None:
        """Handle mount event."""
        if self._text_area:
            self._text_area.focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Update character count when text changes."""
        text = self.get_text()
        char_count_label = self.query_one("#char-count", Label)
        char_count_label.update(f"{len(text)} characters")

    def get_text(self) -> str:
        """Get the current text value."""
        if self._text_area:
            return self._text_area.text
        return ""

    def set_text(self, text: str) -> None:
        """Set the text value."""
        if self._text_area:
            self._text_area.text = text

    def is_valid(self) -> bool:
        """Check if the input is valid (meets minimum length)."""
        text = self.get_text().strip()
        return len(text) >= self.min_length

    def get_validation_error(self) -> Optional[str]:
        """Get validation error message if any."""
        if not self.is_valid():
            return f"Message must be at least {self.min_length} character(s)"
        return None


class LogViewer(VerticalScroll):
    """
    A scrollable viewer for git commit log.

    Displays commits with hash, author, date, and message.
    """

    BINDINGS = [
        Binding("j", "scroll_down", "Down", show=False),
        Binding("k", "scroll_up", "Up", show=False),
        Binding("g", "scroll_top", "Top", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
    ]

    DEFAULT_CSS = """
    LogViewer {
        width: 100%;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    LogViewer .commit-entry {
        width: 100%;
        margin-bottom: 1;
        padding: 1;
        background: $surface;
    }

    LogViewer .commit-hash {
        color: $accent;
        text-style: bold;
    }

    LogViewer .commit-author {
        color: $text-muted;
    }

    LogViewer .commit-date {
        color: $text-muted;
    }

    LogViewer .commit-message {
        color: $text;
        margin-top: 0;
    }

    LogViewer .no-commits {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        commits: List[GitCommit],
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the log viewer.

        Args:
            commits: List of GitCommit objects to display
            name: The name of the widget
            id: The ID of the widget in the DOM
            classes: The CSS classes for the widget
        """
        super().__init__(name=name, id=id, classes=classes)
        self.commits = commits

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        if not self.commits:
            yield Static("[dim]No commits found[/dim]", classes="no-commits")
        else:
            for commit in self.commits:
                yield self._create_commit_entry(commit)

    def _create_commit_entry(self, commit: GitCommit) -> Static:
        """Create a commit entry widget."""
        content = (
            f"[bold]{commit.short_hash}[/bold] "
            f"[dim]({commit.date})[/dim] - "
            f"[dim]{commit.author}[/dim]\n"
            f"  {commit.message}"
        )
        return Static(content, classes="commit-entry")

    def action_scroll_down(self) -> None:
        """Scroll down."""
        self.scroll_relative(y=3)

    def action_scroll_up(self) -> None:
        """Scroll up."""
        self.scroll_relative(y=-3)

    def action_scroll_top(self) -> None:
        """Scroll to top."""
        self.scroll_home()

    def action_scroll_bottom(self) -> None:
        """Scroll to bottom."""
        self.scroll_end()


class StreamingOutput(VerticalScroll):
    """
    A widget for displaying streaming command output.

    Used for build and test output display.
    """

    DEFAULT_CSS = """
    StreamingOutput {
        width: 100%;
        height: 100%;
        border: solid $primary;
        padding: 0 1;
        background: $surface;
    }

    StreamingOutput .output-line {
        width: 100%;
    }

    StreamingOutput .output-error {
        color: $error;
    }

    StreamingOutput .output-success {
        color: $success;
    }

    StreamingOutput .output-warning {
        color: $warning;
    }
    """

    def __init__(
        self,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the streaming output widget.

        Args:
            name: The name of the widget
            id: The ID of the widget in the DOM
            classes: The CSS classes for the widget
        """
        super().__init__(name=name, id=id, classes=classes)
        self._lines: List[str] = []
        self._auto_scroll = True

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static("", id="output-content")

    def append_line(self, line: str) -> None:
        """
        Append a line to the output.

        Args:
            line: Line of text to append
        """
        self._lines.append(line)
        self._update_content()

        # Auto-scroll to bottom
        if self._auto_scroll:
            self.scroll_end(animate=False)

    def append_lines(self, lines: List[str]) -> None:
        """
        Append multiple lines to the output.

        Args:
            lines: List of lines to append
        """
        self._lines.extend(lines)
        self._update_content()

        if self._auto_scroll:
            self.scroll_end(animate=False)

    def clear(self) -> None:
        """Clear all output."""
        self._lines.clear()
        self._update_content()

    def _update_content(self) -> None:
        """Update the displayed content."""
        content_widget = self.query_one("#output-content", Static)

        # Apply syntax highlighting for common patterns
        formatted_lines = []
        for line in self._lines:
            line_lower = line.lower()
            if "error" in line_lower or "failed" in line_lower:
                formatted_lines.append(f"[red]{line}[/red]")
            elif "warning" in line_lower:
                formatted_lines.append(f"[yellow]{line}[/yellow]")
            elif "success" in line_lower or "passed" in line_lower or "✓" in line:
                formatted_lines.append(f"[green]{line}[/green]")
            else:
                formatted_lines.append(line)

        content_widget.update("\n".join(formatted_lines))

    def get_lines(self) -> List[str]:
        """Get all output lines."""
        return self._lines.copy()

    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable or disable auto-scrolling."""
        self._auto_scroll = enabled


class ProgressBarWidget(Static):
    """
    A compact progress bar widget for displaying todo completion progress.

    Shows a visual progress bar with percentage and can be used in
    both the branch list view and todo detail view.
    """

    CSS = """
    ProgressBarWidget {
        width: 100%;
        height: auto;
        padding: 0;
    }

    ProgressBarWidget .progress-container {
        width: 100%;
        height: 1;
    }
    """

    def __init__(
        self,
        total: int,
        done: int,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the progress bar.

        Args:
            total: Total number of items
            done: Number of completed items
            name: The name of the widget
            id: The ID of the widget in the DOM
            classes: The CSS classes for the widget
        """
        super().__init__(name=name, id=id, classes=classes)
        self.total = total
        self.done = done

    def render(self) -> str:
        """Render the progress bar."""
        if self.total == 0:
            return "[dim]No todos[/dim]"

        percentage = (self.done / self.total) * 100
        bar_width = 10
        filled = int((self.done / self.total) * bar_width)
        empty = bar_width - filled

        # Color code based on percentage
        if percentage >= 70:
            bar_color = "green"
        elif percentage >= 30:
            bar_color = "yellow"
        else:
            bar_color = "red"

        bar = f"[{bar_color}]{'█' * filled}[/][dim]{'░' * empty}[/dim]"

        return f"{bar} {percentage:.0f}%"

    def update_progress(self, total: int, done: int) -> None:
        """Update the progress values and re-render."""
        self.total = total
        self.done = done
        self.refresh()


class TodoListWidget(VerticalScroll):
    """
    A scrollable list widget for displaying and managing todos.

    Displays todos with status indicators, allows keyboard navigation,
    and supports inline actions.
    """

    BINDINGS = [
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
        Binding("space", "toggle_status", "Toggle", show=False),
        Binding("n", "add_todo", "New", show=True),
        Binding("e", "edit_todo", "Edit", show=True),
        Binding("d", "delete_todo", "Delete", show=True),
        Binding("a", "assign_todo", "Assign", show=True),
        Binding("b", "block_todo", "Block", show=True),
        Binding("m", "move_todo", "Move", show=True),
    ]

    CSS = """
    TodoListWidget {
        width: 100%;
        height: 100%;
        border: solid $primary;
        padding: 1;
        background: $surface;
    }

    TodoListWidget .todo-item {
        width: 100%;
        padding: 0 1;
        margin-bottom: 0;
        border: none;
    }

    TodoListWidget .todo-done {
        color: $success;
    }

    TodoListWidget .todo-in-progress {
        color: $accent;
    }

    TodoListWidget .todo-blocked {
        color: $warning;
    }

    TodoListWidget .todo-not-started {
        color: $text;
    }

    TodoListWidget .todo-item-focused {
        background: $boost;
        color: $text;
        text-style: bold;
    }

    TodoListWidget .todo-item-focused.todo-done {
        color: $success;
    }

    TodoListWidget .todo-item-focused.todo-in-progress {
        color: $accent;
    }

    TodoListWidget .todo-item-focused.todo-blocked {
        color: $warning;
    }

    TodoListWidget .todo-item-focused.todo-not-started {
        color: $text;
    }

    TodoListWidget .no-todos {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    TodoListWidget .progress-stats {
        width: 100%;
        padding: 1;
        margin-top: 1;
        border-top: solid $primary-lighten-1;
        color: $text-muted;
    }
    """

    class TodoAction(Message):
        """Posted when a todo action is requested."""

        def __init__(self, action: str, task_id: Optional[int] = None) -> None:
            super().__init__()
            self.action = action
            self.task_id = task_id

    def __init__(
        self,
        branch_name: str,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the todo list widget.

        Args:
            branch_name: The branch name to load todos for
            name: The name of the widget
            id: The ID of the widget in the DOM
            classes: The CSS classes for the widget
        """
        super().__init__(name=name, id=id, classes=classes)
        self.border_title = "Tasks"
        self.branch_name = branch_name
        self.todos = []
        self._focused_index = 0
        self.can_focus = True

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        self.load_todos()

        if not self.todos:
            yield Static("[dim]No todos. Press 'n' to create one.[/dim]", classes="no-todos")
        else:
            for idx, todo in enumerate(self.todos):
                yield self._create_todo_item(todo, idx)

            # Add progress stats at the bottom
            yield self._create_progress_stats()

    def load_todos(self) -> None:
        """Load todos for the current branch."""
        from ccc.todo import list_todos
        from ccc.config import load_config

        config = load_config()
        todo_list = list_todos(self.branch_name)

        # Filter out completed if configured
        if not config.todos_show_completed:
            self.todos = [t for t in todo_list.items if t.status != "done"]
        else:
            self.todos = todo_list.items

    def _create_todo_item(self, todo, idx: int) -> Static:
        """Create a todo item widget."""
        # Status symbols
        symbols = {
            "done": "✓",
            "in_progress": "⚙",
            "not_started": "☐",
            "blocked": "⏸",
        }
        symbol = symbols.get(todo.status, "○")

        # Build status info
        info_parts = []
        if todo.assigned_agent:
            info_parts.append(f"[{todo.assigned_agent}]")
        if todo.blocked_by:
            info_parts.append(f"(blocked by #{todo.blocked_by})")
        if todo.estimated_minutes:
            info_parts.append(f"~{todo.estimated_minutes}m")

        info_str = " ".join(info_parts) if info_parts else ""

        # Create content with proper styling
        status_class = f"todo-{todo.status.replace('_', '-')}"
        is_focused = idx == self._focused_index
        focused_class = " todo-item-focused" if is_focused else ""

        # Add visual cursor indicator for focused item
        cursor = "▶ " if is_focused else "  "
        # Use sequential display number (idx + 1) instead of database ID
        display_num = idx + 1
        content = f"{cursor}{symbol} {display_num}. {todo.description} {info_str}"

        return Static(
            content,
            classes=f"todo-item {status_class}{focused_class}",
        )

    def _create_progress_stats(self) -> Static:
        """Create progress statistics widget."""
        from ccc.todo import list_todos

        todo_list = list_todos(self.branch_name)
        stats = todo_list.progress_stats()
        percentage = todo_list.progress_percentage()

        content = (
            f"[bold]Progress:[/bold] {stats['done']}/{stats['total']} complete ({percentage:.0f}%)\n"
            f"  {stats['in_progress']} in progress, "
            f"{stats['not_started']} not started, "
            f"{stats['blocked']} blocked"
        )

        return Static(content, classes="progress-stats")

    def action_move_up(self) -> None:
        """Move focus up."""
        if self._focused_index > 0:
            self._focused_index -= 1
            self.refresh_content()

    def action_move_down(self) -> None:
        """Move focus down."""
        if self._focused_index < len(self.todos) - 1:
            self._focused_index += 1
            self.refresh_content()

    def action_toggle_status(self) -> None:
        """Toggle status of focused todo."""
        if self.todos and self._focused_index < len(self.todos):
            todo = self.todos[self._focused_index]

            # Toggle between not_started and done
            from ccc.todo import update_todo_status

            new_status = "done" if todo.status == "not_started" else "not_started"
            update_todo_status(self.branch_name, todo.id, new_status)

            self.refresh_content()

    def action_add_todo(self) -> None:
        """Request add todo action."""
        self.post_message(self.TodoAction("add"))

    def action_edit_todo(self) -> None:
        """Request edit todo action."""
        if self.todos and self._focused_index < len(self.todos):
            task_id = self.todos[self._focused_index].id
            self.post_message(self.TodoAction("edit", task_id))

    def action_delete_todo(self) -> None:
        """Request delete todo action."""
        if self.todos and self._focused_index < len(self.todos):
            task_id = self.todos[self._focused_index].id
            self.post_message(self.TodoAction("delete", task_id))

    def action_assign_todo(self) -> None:
        """Request assign todo action."""
        if self.todos and self._focused_index < len(self.todos):
            task_id = self.todos[self._focused_index].id
            self.post_message(self.TodoAction("assign", task_id))

    def action_block_todo(self) -> None:
        """Request block todo action."""
        if self.todos and self._focused_index < len(self.todos):
            task_id = self.todos[self._focused_index].id
            self.post_message(self.TodoAction("block", task_id))

    def action_move_todo(self) -> None:
        """Request move todo action."""
        if self.todos and self._focused_index < len(self.todos):
            task_id = self.todos[self._focused_index].id
            self.post_message(self.TodoAction("move", task_id))

    def refresh_content(self) -> None:
        """Refresh the todo list display."""
        self.load_todos()

        # Clear all existing children completely
        for child in list(self.children):
            child.remove()

        # Remount all children
        if not self.todos:
            self.mount(Static("[dim]No todos. Press 'n' to create one.[/dim]", classes="no-todos"))
        else:
            for idx, todo in enumerate(self.todos):
                self.mount(self._create_todo_item(todo, idx))

            self.mount(self._create_progress_stats())

    def get_focused_todo_id(self) -> Optional[int]:
        """Get the ID of the currently focused todo."""
        if self.todos and self._focused_index < len(self.todos):
            return self.todos[self._focused_index].id
        return None


class StatusBar(Static):
    """
    Status bar widget showing real-time status of server, database, build, and tests.

    Displays colored status indicators with icons for quick visual feedback.
    """

    # Reactive property for status updates
    status: reactive[dict] = reactive({})

    # CSS classes for styling
    DEFAULT_CSS = """
    StatusBar {
        height: 3;
        background: $panel;
        border-top: solid $primary;
        padding: 0 2;
    }

    StatusBar:focus {
        border-top: solid $accent;
    }
    """

    def __init__(self, *args, **kwargs):
        """Initialize status bar."""
        super().__init__(*args, **kwargs)
        self.border_title = "Status"

    def watch_status(self, status: dict) -> None:
        """
        React to status changes.

        Args:
            status: Updated status dictionary
        """
        from rich.text import Text
        self.update(self._render_status(status))

    def _render_status(self, status: dict):
        """
        Render status bar content with colors and icons.

        Args:
            status: Status dictionary containing server, database, build, tests

        Returns:
            Rich Text object with formatted status
        """
        from rich.text import Text
        from ccc.utils import format_time_ago
        from datetime import datetime

        text = Text()

        # Server status
        server = status.get("server", {})
        if server:
            self._render_server_status(text, server)
            text.append("  ")  # Spacing

        # Database status
        database = status.get("database", {})
        if database:
            self._render_database_status(text, database)
            text.append("  ")  # Spacing

        # Tests status
        tests = status.get("tests", {})
        if tests:
            self._render_tests_status(text, tests)
            text.append("  ")  # Spacing

        # Build status
        build = status.get("build", {})
        if build:
            self._render_build_status(text, build)

        return text

    def _render_server_status(self, text, server: dict) -> None:
        """Render server status."""
        state = server.get("state", "stopped")
        url = server.get("url") or "stopped"
        error_msg = server.get("error_message")

        icon = self._get_status_icon(state)
        style = self._get_status_style(state)

        text.append("SERVER: ", style="bold")
        text.append(f"{icon} ", style=style)

        if state == "error" and error_msg:
            text.append(error_msg[:50], style=style)
        else:
            text.append(url, style=style)

    def _render_database_status(self, text, database: dict) -> None:
        """Render database status."""
        state = database.get("state", "stopped")
        error_msg = database.get("error_message")

        icon = self._get_status_icon(state)
        style = self._get_status_style(state)

        text.append("DATABASE: ", style="bold")
        text.append(f"{icon} ", style=style)

        if state == "error" and error_msg:
            text.append(error_msg[:30], style=style)
        elif state == "connected":
            conn_str = database.get("connection_string") or ""
            if ":5432" in conn_str:
                text.append(":5432", style=style)
            else:
                text.append("connected", style=style)
        else:
            text.append("disconnected", style=style)

    def _render_tests_status(self, text, tests: dict) -> None:
        """Render tests status."""
        last_run = tests.get("last_run")
        if not last_run:
            text.append("TESTS: ", style="bold")
            text.append("? not run", style="dim")
            return

        passed = tests.get("passed", 0)
        total = tests.get("total", 0)

        if total > 0:
            if passed == total:
                state = "healthy"
                icon = "✓"
            else:
                state = "error"
                icon = "✗"
        else:
            state = "stopped"
            icon = "?"

        style = self._get_status_style(state)

        text.append("TESTS: ", style="bold")
        text.append(f"{icon} ", style=style)
        text.append(f"{passed}/{total} passed", style=style)

    def _render_build_status(self, text, build: dict) -> None:
        """Render build status."""
        from ccc.utils import format_time_ago
        from datetime import datetime

        last_build = build.get("last_build")
        if not last_build:
            text.append("BUILD: ", style="bold")
            text.append("? not run", style="dim")
            return

        success = build.get("success", False)
        state = "healthy" if success else "error"
        icon = self._get_status_icon(state)
        style = self._get_status_style(state)

        text.append("BUILD: ", style="bold")
        text.append(f"{icon} ", style=style)

        if isinstance(last_build, str):
            try:
                last_build_dt = datetime.fromisoformat(last_build.replace("Z", "+00:00"))
                time_ago = format_time_ago(last_build_dt)
                text.append(f"({time_ago})", style=style)
            except:
                text.append("(unknown)", style="dim")
        elif isinstance(last_build, datetime):
            time_ago = format_time_ago(last_build)
            text.append(f"({time_ago})", style=style)

    def _get_status_icon(self, state: str) -> str:
        """Get status icon for state."""
        icons = {
            "healthy": "●",
            "connected": "●",
            "starting": "◐",
            "unhealthy": "◐",
            "error": "✗",
            "stopped": "○",
            "unknown": "?",
        }
        return icons.get(state, "?")

    def _get_status_style(self, state: str) -> str:
        """Get Rich style for state."""
        styles = {
            "healthy": "green",
            "connected": "green",
            "starting": "yellow",
            "unhealthy": "yellow",
            "error": "red",
            "stopped": "dim",
            "unknown": "dim",
        }
        return styles.get(state, "white")

    def on_click(self, event) -> None:
        """Handle click on status bar (future enhancement)."""
        pass
