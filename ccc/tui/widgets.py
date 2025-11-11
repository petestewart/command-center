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
                status_str = f"[{self._get_status_color(file.status)}]{file.display_status}[/]"
                label = f"{status_str}: {file.path}"
                checkbox = Checkbox(label, value=file.staged, id=f"file-{file.path}")
                self._checkboxes[file.path] = checkbox
                if file.staged:
                    self.selected_files.add(file.path)
                yield checkbox

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
        # Extract file path from checkbox ID
        file_path = event.checkbox.id.replace("file-", "")

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
