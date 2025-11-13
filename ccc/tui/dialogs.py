"""
Dialog components for Command Center TUI.
"""

from typing import Callable, Optional, List
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Label, LoadingIndicator
from textual.binding import Binding
from textual import work

from ccc.git_operations import GitFile, GitCommit, get_changed_files, stage_and_commit
from ccc.tui.widgets import FileCheckboxList, MultiLineInput, LogViewer, StreamingOutput


class BaseDialog(ModalScreen):
    """
    Base class for modal dialogs.

    Provides a centered modal overlay with a title and content area.
    Automatically handles dimming the background and escape key handling.
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
    ]

    DEFAULT_CSS = """
    BaseDialog {
        align: center middle;
    }

    BaseDialog > Container {
        max-width: 80;
        max-height: 80%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
    }

    BaseDialog .dialog-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    BaseDialog .dialog-content {
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }

    BaseDialog .dialog-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
    }

    BaseDialog Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        title: str = "Dialog",
        content: Optional[str] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the base dialog.

        Args:
            title: Dialog title text
            content: Optional content text
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(name=name, id=id, classes=classes)
        self.dialog_title = title
        self.dialog_content = content

    def compose(self) -> ComposeResult:
        """Create child widgets for the dialog."""
        with Container():
            yield Label(self.dialog_title, classes="dialog-title")
            yield from self.compose_content()
            yield from self.compose_buttons()

    def compose_content(self) -> ComposeResult:
        """
        Override this method to add custom content to the dialog.

        Yields:
            Textual widgets for the dialog content
        """
        if self.dialog_content:
            yield Static(self.dialog_content, classes="dialog-content")

    def compose_buttons(self) -> ComposeResult:
        """
        Override this method to add custom buttons to the dialog.

        Yields:
            Textual widgets for the dialog buttons
        """
        yield Horizontal(classes="dialog-buttons")

    def action_dismiss(self) -> None:
        """Dismiss the dialog with no result."""
        self.dismiss(None)


class ConfirmDialog(BaseDialog):
    """
    A confirmation dialog with Yes/No buttons.

    Example:
        def on_confirm_result(result: bool) -> None:
            if result:
                # User clicked Yes
                ...

        self.push_screen(
            ConfirmDialog("Are you sure?", "This action cannot be undone"),
            on_confirm_result
        )
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel", show=False),
        Binding("y", "confirm", "Yes", show=False),
        Binding("n", "dismiss", "No", show=False),
    ]

    def __init__(
        self,
        title: str,
        message: str,
        yes_label: str = "Yes",
        no_label: str = "No",
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the confirmation dialog.

        Args:
            title: Dialog title
            message: Confirmation message to display
            yes_label: Label for the yes button
            no_label: Label for the no button
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(title=title, content=message, name=name, id=id, classes=classes)
        self.yes_label = yes_label
        self.no_label = no_label

    def compose_buttons(self) -> ComposeResult:
        """Add Yes/No buttons."""
        with Horizontal(classes="dialog-buttons"):
            yield Button(self.yes_label, variant="primary", id="yes")
            yield Button(self.no_label, variant="default", id="no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_confirm(self) -> None:
        """Handle 'y' key press."""
        self.dismiss(True)

    def action_dismiss(self) -> None:
        """Handle 'n' or 'escape' key press."""
        self.dismiss(False)


class MessageDialog(BaseDialog):
    """
    A simple message dialog with a single OK button.

    Example:
        self.push_screen(MessageDialog("Success", "Operation completed successfully!"))
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("enter", "dismiss", "OK", show=False),
    ]

    def __init__(
        self,
        title: str,
        message: str,
        ok_label: str = "OK",
        variant: str = "default",
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the message dialog.

        Args:
            title: Dialog title
            message: Message to display
            ok_label: Label for the OK button
            variant: Button variant (default, primary, success, warning, error)
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(title=title, content=message, name=name, id=id, classes=classes)
        self.ok_label = ok_label
        self.variant = variant

    def compose_buttons(self) -> ComposeResult:
        """Add OK button."""
        with Horizontal(classes="dialog-buttons"):
            yield Button(self.ok_label, variant=self.variant, id="ok")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        self.dismiss(True)

    def action_dismiss(self) -> None:
        """Handle enter or escape key press."""
        self.dismiss(True)


class ErrorDialog(MessageDialog):
    """
    An error message dialog with error styling.

    Example:
        self.push_screen(ErrorDialog("Error", "Failed to push to remote: permission denied"))
    """

    def __init__(
        self,
        title: str = "Error",
        message: str = "",
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the error dialog.

        Args:
            title: Dialog title (defaults to "Error")
            message: Error message to display
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(
            title=f"[red]{title}[/red]",
            message=f"[red]{message}[/red]",
            ok_label="Close",
            variant="error",
            name=name,
            id=id,
            classes=classes,
        )


class SuccessDialog(MessageDialog):
    """
    A success message dialog with success styling.

    Example:
        self.push_screen(SuccessDialog("Success", "Successfully pushed to remote!"))
    """

    def __init__(
        self,
        title: str = "Success",
        message: str = "",
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the success dialog.

        Args:
            title: Dialog title (defaults to "Success")
            message: Success message to display
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(
            title=f"[green]{title}[/green]",
            message=f"[green]{message}[/green]",
            ok_label="OK",
            variant="success",
            name=name,
            id=id,
            classes=classes,
        )

class CommitDialog(BaseDialog):
    """
    Dialog for creating git commits with file selection and message input.

    Example:
        def on_commit_complete(result):
            if result and result["success"]:
                # Commit was created successfully
                ...

        self.push_screen(
            CommitDialog(worktree_path, branch_name),
            on_commit_complete
        )
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel", show=False),
        Binding("ctrl+enter", "commit", "Commit", show=True),
    ]

    DEFAULT_CSS = """
    CommitDialog > Container {
        max-width: 100;
        max-height: 90%;
    }

    CommitDialog .selection-info {
        width: 100%;
        color: $text-muted;
        margin-bottom: 1;
    }

    CommitDialog Label {
        margin-bottom: 0;
    }
    """

    def __init__(
        self,
        worktree_path: Path,
        branch_name: str,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the commit dialog.

        Args:
            worktree_path: Path to the git worktree
            branch_name: Current branch name
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(
            title=f"Commit Changes: {branch_name}",
            name=name,
            id=id,
            classes=classes,
        )
        self.worktree_path = worktree_path
        self.branch_name = branch_name
        self.files: List[GitFile] = []
        self._file_list: Optional[FileCheckboxList] = None
        self._message_input: Optional[MultiLineInput] = None

    def compose_content(self) -> ComposeResult:
        """Create the dialog content."""
        # Load changed files
        self.files, error = get_changed_files(self.worktree_path)

        if error:
            yield Static(f"[red]Error loading files: {error}[/red]")
        elif not self.files:
            yield Static("[dim]No changed files to commit[/dim]")
        else:
            yield Label(f"Modified files ({len(self.files)}):", classes="section-label")
            self._file_list = FileCheckboxList(self.files, id="file-list")
            yield self._file_list

            yield Static("", classes="selection-info", id="selection-info")

            yield Label("Commit message:", classes="section-label")
            self._message_input = MultiLineInput(
                placeholder="Enter commit message (minimum 1 character)...",
                id="message-input",
            )
            yield self._message_input

    def compose_buttons(self) -> ComposeResult:
        """Add Commit/Cancel buttons."""
        with Horizontal(classes="dialog-buttons"):
            yield Button("Commit", variant="primary", id="commit")
            yield Button("Cancel", variant="default", id="cancel")

    def on_file_checkbox_list_selection_changed(
        self, event: FileCheckboxList.SelectionChanged
    ) -> None:
        """Update selection info when file selection changes."""
        selection_info = self.query_one("#selection-info", Static)
        selection_info.update(f"[dim]{event.selected_count} file(s) selected[/dim]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "commit":
            self._do_commit()
        else:
            self.dismiss(None)

    def action_commit(self) -> None:
        """Handle Ctrl+Enter key press."""
        self._do_commit()

    def action_dismiss(self) -> None:
        """Handle escape key press."""
        self.dismiss(None)

    def _do_commit(self) -> None:
        """Perform the commit operation."""
        if not self._file_list or not self._message_input:
            return

        # Validate inputs
        selected_files = self._file_list.get_selected_files()
        if not selected_files:
            self.app.push_screen(
                ErrorDialog("No Files Selected", "Please select at least one file to commit.")
            )
            return

        message = self._message_input.get_text().strip()
        validation_error = self._message_input.get_validation_error()
        if validation_error:
            self.app.push_screen(ErrorDialog("Invalid Message", validation_error))
            return

        # Perform commit in background
        self._perform_commit(selected_files, message)

    @work(thread=True)
    def _perform_commit(self, files: List[str], message: str) -> None:
        """Perform the commit operation in a background thread."""
        result = stage_and_commit(self.worktree_path, files, message)

        # Return result to caller
        self.app.call_from_thread(self._on_commit_complete, result)

    def _on_commit_complete(self, result) -> None:
        """Handle commit completion."""
        if result.success:
            self.dismiss({
                "success": True,
                "message": result.message,
                "output": result.output,
            })
        else:
            self.app.push_screen(ErrorDialog("Commit Failed", result.message))


class LogDialog(BaseDialog):
    """
    Dialog for viewing git commit log.

    Example:
        self.push_screen(LogDialog(commits, branch_name))
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("q", "dismiss", "Close", show=False),
    ]

    DEFAULT_CSS = """
    LogDialog > Container {
        max-width: 120;
        max-height: 90%;
    }

    LogDialog LogViewer {
        height: 30;
    }
    """

    def __init__(
        self,
        commits: List[GitCommit],
        branch_name: str,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the log dialog.

        Args:
            commits: List of commits to display
            branch_name: Current branch name
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(
            title=f"Commit Log: {branch_name}",
            name=name,
            id=id,
            classes=classes,
        )
        self.commits = commits

    def compose_content(self) -> ComposeResult:
        """Create the dialog content."""
        yield LogViewer(self.commits, id="log-viewer")

    def compose_buttons(self) -> ComposeResult:
        """Add Close button."""
        with Horizontal(classes="dialog-buttons"):
            yield Button("Close", variant="default", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        self.dismiss(None)

    def action_dismiss(self) -> None:
        """Handle escape/q key press."""
        self.dismiss(None)


class OutputDialog(BaseDialog):
    """
    Dialog for displaying streaming command output (build/test).

    Example:
        dialog = OutputDialog("Building", "npm run build")
        self.push_screen(dialog)
        # Later, stream output to it:
        dialog.append_output("Compiling...")
    """

    BINDINGS = [
        Binding("escape", "close", "Close", show=False),
        Binding("q", "close", "Close", show=False),
    ]

    DEFAULT_CSS = """
    OutputDialog > Container {
        max-width: 120;
        max-height: 90%;
    }

    OutputDialog .command-label {
        width: 100%;
        color: $text-muted;
        margin-bottom: 1;
    }

    OutputDialog StreamingOutput {
        height: 30;
    }

    OutputDialog .status-label {
        width: 100%;
        text-align: center;
        margin-top: 1;
        text-style: bold;
    }

    OutputDialog LoadingIndicator {
        width: auto;
        height: auto;
    }
    """

    def __init__(
        self,
        title: str,
        command: str,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the output dialog.

        Args:
            title: Dialog title (e.g., "Building", "Running Tests")
            command: Command being executed
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(title=title, name=name, id=id, classes=classes)
        self.command = command
        self._output: Optional[StreamingOutput] = None
        self._status_label: Optional[Static] = None
        self._loading: Optional[LoadingIndicator] = None
        self._is_running = True

    def compose_content(self) -> ComposeResult:
        """Create the dialog content."""
        yield Static(f"Running: [cyan]{self.command}[/cyan]", classes="command-label")

        with Horizontal():
            self._loading = LoadingIndicator()
            yield self._loading
            self._status_label = Static("In progress...", classes="status-label")
            yield self._status_label

        self._output = StreamingOutput(id="output")
        yield self._output

    def compose_buttons(self) -> ComposeResult:
        """Add Close button (initially disabled)."""
        with Horizontal(classes="dialog-buttons"):
            yield Button("Close", variant="default", id="close", disabled=True)

    def append_output(self, line: str) -> None:
        """Append a line of output."""
        if self._output:
            self._output.append_line(line)

    def set_complete(self, success: bool, message: str = "") -> None:
        """
        Mark the operation as complete.

        Args:
            success: Whether the operation succeeded
            message: Optional completion message
        """
        self._is_running = False

        # Hide loading indicator
        if self._loading:
            self._loading.display = False

        # Update status
        if self._status_label:
            if success:
                self._status_label.update(f"[green]✓ {message or 'Completed successfully'}[/green]")
            else:
                self._status_label.update(f"[red]✗ {message or 'Failed'}[/red]")

        # Enable close button
        close_button = self.query_one("#close", Button)
        close_button.disabled = False

    def action_close(self) -> None:
        """Handle close action (only if not running)."""
        if not self._is_running:
            self.dismiss({
                "success": True,
                "output": self._output.get_lines() if self._output else [],
            })

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "close" and not self._is_running:
            self.action_close()


class FileBrowserDialog(BaseDialog):
    """
    Dialog for browsing and previewing changed files with diffs.

    Shows a list of changed files and displays diffs when selected.
    Supports navigation between files and opening files in editor.

    Example:
        self.push_screen(FileBrowserDialog(worktree_path, branch_name))
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("q", "dismiss", "Close", show=False),
        Binding("j", "next_file", "Next File", show=False),
        Binding("k", "prev_file", "Prev File", show=False),
        Binding("e", "open_editor", "Edit", show=True),
        Binding("enter", "open_editor", "Edit", show=False),
    ]

    DEFAULT_CSS = """
    FileBrowserDialog > Container {
        max-width: 140;
        max-height: 95%;
    }

    FileBrowserDialog > Container > Horizontal {
        height: 1fr;
    }

    FileBrowserDialog .file-list-container {
        width: 30;
        height: 100%;
        border-right: solid $primary;
        padding: 0 1;
    }

    FileBrowserDialog .file-list-item {
        width: 100%;
        padding: 0 1;
    }

    FileBrowserDialog .file-list-item.selected {
        background: $primary;
        color: $text;
    }

    FileBrowserDialog .diff-container {
        width: 1fr;
        height: 100%;
        padding: 0 1;
    }

    FileBrowserDialog .diff-header {
        width: 100%;
        text-style: bold;
        margin-bottom: 1;
    }

    FileBrowserDialog .diff-content {
        width: 100%;
        height: 1fr;
    }

    FileBrowserDialog .no-files {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def __init__(
        self,
        worktree_path: Path,
        branch_name: str,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the file browser dialog.

        Args:
            worktree_path: Path to the git worktree
            branch_name: Current branch name
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(
            title=f"Changed Files: {branch_name}",
            name=name,
            id=id,
            classes=classes,
        )
        self.worktree_path = worktree_path
        self.branch_name = branch_name
        self.files: List[GitFile] = []
        self.selected_index = 0

    def compose_content(self) -> ComposeResult:
        """Create the dialog content."""
        from ccc.git_operations import get_changed_files

        # Load changed files
        self.files, error = get_changed_files(self.worktree_path)

        if error:
            yield Static(f"[red]Error loading files: {error}[/red]", classes="no-files")
        elif not self.files:
            yield Static("[dim]No changed files[/dim]", classes="no-files")
        else:
            with Horizontal():
                # File list on the left
                with VerticalScroll(classes="file-list-container"):
                    for idx, file in enumerate(self.files):
                        status_color = self._get_status_color(file.status)
                        classes = "file-list-item"
                        if idx == self.selected_index:
                            classes += " selected"
                        yield Static(
                            f"[{status_color}]{file.status}[/] {file.path}",
                            classes=classes,
                            id=f"file-{idx}",
                        )

                # Diff display on the right
                with Container(classes="diff-container"):
                    yield Static("", classes="diff-header", id="diff-header")
                    yield VerticalScroll(
                        Static("", classes="diff-content"),
                        classes="diff-content",
                        id="diff-scroll",
                    )

    def on_mount(self) -> None:
        """Load the diff for the first file."""
        if self.files:
            self._show_diff(0)

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

    def _show_diff(self, index: int) -> None:
        """Show diff for the file at given index."""
        if not self.files or index < 0 or index >= len(self.files):
            return

        self.selected_index = index
        file = self.files[index]

        # Update file list highlighting
        for idx in range(len(self.files)):
            file_item = self.query_one(f"#file-{idx}", Static)
            if idx == index:
                file_item.add_class("selected")
            else:
                file_item.remove_class("selected")

        # Update diff header
        diff_header = self.query_one("#diff-header", Static)
        diff_header.update(f"[bold]{file.path}[/bold] ({file.display_status})")

        # Get and display diff
        diff_content = self._get_diff(file)
        diff_scroll = self.query_one("#diff-scroll", VerticalScroll)
        diff_static = diff_scroll.query_one(Static)
        diff_static.update(diff_content)
        diff_scroll.scroll_home()

    def _get_diff(self, file: GitFile) -> str:
        """Get the diff for a file."""
        import subprocess
        from ccc.config import load_config

        config = load_config()

        try:
            # Try to use configured diff viewer
            if config.diff_viewer == "delta" and self._has_command("delta"):
                result = subprocess.run(
                    ["git", "diff", "--color=always", file.path],
                    cwd=str(self.worktree_path),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    # Delta adds ANSI colors, which Rich can render
                    return result.stdout or "[dim]No changes to display[/dim]"

            # Fall back to git diff
            result = subprocess.run(
                ["git", "diff", file.path],
                cwd=str(self.worktree_path),
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                diff_text = result.stdout
                if not diff_text:
                    # For untracked files, show the entire file
                    if file.status == "?":
                        try:
                            file_path = self.worktree_path / file.path
                            with open(file_path, "r") as f:
                                content = f.read()
                                return f"[green]+ New file content:[/green]\n{content[:1000]}"
                        except Exception:
                            return "[dim]Cannot read file[/dim]"
                    return "[dim]No changes to display[/dim]"

                # Format diff with colors
                return self._format_diff(diff_text)
            else:
                return f"[red]Error getting diff: {result.stderr}[/red]"

        except subprocess.TimeoutExpired:
            return "[red]Diff command timed out[/red]"
        except Exception as e:
            return f"[red]Error: {e}[/red]"

    def _has_command(self, command: str) -> bool:
        """Check if a command is available."""
        import subprocess
        try:
            subprocess.run(
                ["which", command],
                capture_output=True,
                timeout=1,
            )
            return True
        except Exception:
            return False

    def _format_diff(self, diff_text: str) -> str:
        """Format diff text with syntax highlighting."""
        lines = []
        for line in diff_text.split("\n"):
            if line.startswith("+"):
                lines.append(f"[green]{line}[/green]")
            elif line.startswith("-"):
                lines.append(f"[red]{line}[/red]")
            elif line.startswith("@@"):
                lines.append(f"[cyan]{line}[/cyan]")
            elif line.startswith("diff --git"):
                lines.append(f"[bold]{line}[/bold]")
            else:
                lines.append(line)
        return "\n".join(lines)

    def compose_buttons(self) -> ComposeResult:
        """Add action buttons."""
        with Horizontal(classes="dialog-buttons"):
            yield Button("Edit (e)", variant="primary", id="edit")
            yield Button("Close (q)", variant="default", id="close")

    def action_next_file(self) -> None:
        """Navigate to next file."""
        if self.files and self.selected_index < len(self.files) - 1:
            self._show_diff(self.selected_index + 1)

    def action_prev_file(self) -> None:
        """Navigate to previous file."""
        if self.files and self.selected_index > 0:
            self._show_diff(self.selected_index - 1)

    def action_open_editor(self) -> None:
        """Open the selected file in editor."""
        if not self.files:
            return

        file = self.files[self.selected_index]
        file_path = self.worktree_path / file.path

        # Dismiss dialog with file path to open
        self.dismiss({
            "action": "edit",
            "file_path": str(file_path),
        })

    def action_dismiss(self) -> None:
        """Handle escape/q key press."""
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "edit":
            self.action_open_editor()
        else:
            self.dismiss(None)


class AddTodoDialog(BaseDialog):
    """
    Dialog for adding a new todo item.

    Example:
        def on_todo_added(result: Optional[dict]) -> None:
            if result:
                # User added a new todo
                description = result["description"]
                ...

        self.push_screen(
            AddTodoDialog(branch_name),
            on_todo_added
        )
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel", show=False),
        Binding("ctrl+s", "save", "Save", show=False),
    ]

    CSS = """
    AddTodoDialog > Container {
        max-width: 80;
        width: 70;
    }

    AddTodoDialog .input-group {
        width: 100%;
        margin-bottom: 1;
    }

    AddTodoDialog .input-label {
        width: 100%;
        color: $text-muted;
        margin-bottom: 0;
    }

    AddTodoDialog Input {
        width: 100%;
        margin-bottom: 1;
    }

    AddTodoDialog TextArea {
        width: 100%;
        height: 5;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        branch_name: str,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the add todo dialog.

        Args:
            branch_name: Branch to add todo to
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(
            title="Add New Todo",
            name=name,
            id=id,
            classes=classes,
        )
        self.branch_name = branch_name

    def compose_content(self) -> ComposeResult:
        """Create the dialog content."""
        from textual.widgets import Input, TextArea

        with Vertical(classes="input-group"):
            yield Label("Description:", classes="input-label")
            yield Input(placeholder="Enter todo description...", id="description")

        with Vertical(classes="input-group"):
            yield Label("Estimated minutes (optional):", classes="input-label")
            yield Input(placeholder="e.g., 30", id="estimate", type="integer")

        with Vertical(classes="input-group"):
            yield Label("Assign to agent (optional):", classes="input-label")
            yield Input(placeholder="e.g., agent-1", id="assign")

    def compose_buttons(self) -> ComposeResult:
        """Add Create/Cancel buttons."""
        with Horizontal(classes="dialog-buttons"):
            yield Button("Create", variant="primary", id="create")
            yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "create":
            self.action_save()
        else:
            self.action_dismiss()

    def action_save(self) -> None:
        """Save the new todo."""
        from textual.widgets import Input

        description_input = self.query_one("#description", Input)
        description = description_input.value.strip()

        if not description:
            # Show error - description is required
            return

        estimate_input = self.query_one("#estimate", Input)
        assign_input = self.query_one("#assign", Input)

        try:
            estimate = int(estimate_input.value) if estimate_input.value else None
        except ValueError:
            estimate = None

        assign = assign_input.value.strip() if assign_input.value else None

        self.dismiss({
            "description": description,
            "estimate": estimate,
            "assign": assign,
        })


class EditTodoDialog(BaseDialog):
    """
    Dialog for editing an existing todo item.
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel", show=False),
        Binding("ctrl+s", "save", "Save", show=False),
    ]

    CSS = """
    EditTodoDialog > Container {
        max-width: 80;
        width: 70;
    }

    EditTodoDialog .input-group {
        width: 100%;
        margin-bottom: 1;
    }

    EditTodoDialog .input-label {
        width: 100%;
        color: $text-muted;
        margin-bottom: 0;
    }

    EditTodoDialog Input {
        width: 100%;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        branch_name: str,
        task_id: int,
        current_description: str,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the edit todo dialog.

        Args:
            branch_name: Branch name
            task_id: Task ID to edit
            current_description: Current description
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(
            title=f"Edit Todo #{task_id}",
            name=name,
            id=id,
            classes=classes,
        )
        self.branch_name = branch_name
        self.task_id = task_id
        self.current_description = current_description

    def compose_content(self) -> ComposeResult:
        """Create the dialog content."""
        from textual.widgets import Input

        with Vertical(classes="input-group"):
            yield Label("Description:", classes="input-label")
            description_input = Input(
                value=self.current_description,
                id="description"
            )
            yield description_input

    def compose_buttons(self) -> ComposeResult:
        """Add Save/Cancel buttons."""
        with Horizontal(classes="dialog-buttons"):
            yield Button("Save", variant="primary", id="save")
            yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save":
            self.action_save()
        else:
            self.action_dismiss()

    def action_save(self) -> None:
        """Save the edited todo."""
        from textual.widgets import Input

        description_input = self.query_one("#description", Input)
        description = description_input.value.strip()

        if not description:
            return

        self.dismiss({
            "task_id": self.task_id,
            "description": description,
        })


class AssignTodoDialog(BaseDialog):
    """
    Dialog for assigning a todo to an agent.
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel", show=False),
    ]

    CSS = """
    AssignTodoDialog > Container {
        max-width: 60;
        width: 50;
    }

    AssignTodoDialog .input-label {
        width: 100%;
        color: $text-muted;
        margin-bottom: 0;
    }

    AssignTodoDialog Input {
        width: 100%;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        task_id: int,
        current_agent: Optional[str] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the assign todo dialog.

        Args:
            task_id: Task ID
            current_agent: Currently assigned agent (if any)
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(
            title=f"Assign Todo #{task_id}",
            name=name,
            id=id,
            classes=classes,
        )
        self.task_id = task_id
        self.current_agent = current_agent

    def compose_content(self) -> ComposeResult:
        """Create the dialog content."""
        from textual.widgets import Input

        yield Label("Agent name:", classes="input-label")
        agent_input = Input(
            value=self.current_agent or "",
            placeholder="Enter agent name (e.g., agent-1)",
            id="agent"
        )
        yield agent_input

        if self.current_agent:
            yield Static(
                "[dim]Leave empty to unassign[/dim]",
                classes="input-label"
            )

    def compose_buttons(self) -> ComposeResult:
        """Add Assign/Cancel buttons."""
        with Horizontal(classes="dialog-buttons"):
            yield Button("Assign", variant="primary", id="assign")
            yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "assign":
            self.action_assign()
        else:
            self.action_dismiss()

    def action_assign(self) -> None:
        """Assign the todo."""
        from textual.widgets import Input

        agent_input = self.query_one("#agent", Input)
        agent = agent_input.value.strip() or None

        self.dismiss({
            "task_id": self.task_id,
            "agent": agent,
        })


class BlockTodoDialog(BaseDialog):
    """
    Dialog for setting a todo as blocked by another todo.
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel", show=False),
    ]

    CSS = """
    BlockTodoDialog > Container {
        max-width: 60;
        width: 50;
    }

    BlockTodoDialog .input-label {
        width: 100%;
        color: $text-muted;
        margin-bottom: 0;
    }

    BlockTodoDialog Input {
        width: 100%;
        margin-bottom: 1;
    }

    BlockTodoDialog .help-text {
        width: 100%;
        color: $text-muted;
        margin-top: 0;
        margin-bottom: 1;
    }
    """

    def __init__(
        self,
        task_id: int,
        current_blocked_by: Optional[int] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the block todo dialog.

        Args:
            task_id: Task ID
            current_blocked_by: Currently blocking task ID (if any)
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(
            title=f"Block Todo #{task_id}",
            name=name,
            id=id,
            classes=classes,
        )
        self.task_id = task_id
        self.current_blocked_by = current_blocked_by

    def compose_content(self) -> ComposeResult:
        """Create the dialog content."""
        from textual.widgets import Input

        yield Static(
            "This task will be blocked until another task is completed.",
            classes="help-text"
        )

        yield Label("Blocking task ID:", classes="input-label")
        blocked_input = Input(
            value=str(self.current_blocked_by) if self.current_blocked_by else "",
            placeholder="Enter task ID that blocks this task",
            id="blocked_by",
            type="integer"
        )
        yield blocked_input

        if self.current_blocked_by:
            yield Static(
                "[dim]Leave empty to unblock[/dim]",
                classes="help-text"
            )

    def compose_buttons(self) -> ComposeResult:
        """Add Block/Cancel buttons."""
        with Horizontal(classes="dialog-buttons"):
            yield Button("Set Blocking", variant="primary", id="block")
            yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "block":
            self.action_block()
        else:
            self.action_dismiss()

    def action_block(self) -> None:
        """Set the blocking dependency."""
        from textual.widgets import Input

        blocked_input = self.query_one("#blocked_by", Input)

        try:
            blocked_by = int(blocked_input.value) if blocked_input.value else None
        except ValueError:
            # Invalid input
            return

        self.dismiss({
            "task_id": self.task_id,
            "blocked_by": blocked_by,
        })
