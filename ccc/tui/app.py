"""
Command Center TUI - Terminal User Interface

A LazyGit-style TUI for managing tickets and monitoring status.
"""

from datetime import datetime
from typing import Optional, List
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Static, DataTable, Label
from textual.binding import Binding
from textual.reactive import reactive
from rich.text import Text

from ccc.ticket import Ticket, TicketRegistry
from ccc.status import read_agent_status
from ccc.git_status import get_git_status
from ccc.build_status import read_build_status
from ccc.test_status import read_test_status
from ccc.config import load_config
from ccc.utils import format_time_ago

# Phase 3: Import new components
from ccc.tui.dialogs import (
    CommitDialog,
    ConfirmDialog,
    ErrorDialog,
    SuccessDialog,
    LogDialog,
    OutputDialog,
    FileBrowserDialog,
)
from ccc.git_operations import (
    push_to_remote,
    pull_from_remote,
    get_commit_log,
)
from ccc.build_runner import run_build, run_tests


class StatusPanel(Static):
    """Base class for status panels."""

    def __init__(self, title: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.border_title = title

    def compose(self) -> ComposeResult:
        yield Label(self.render_content())

    def render_content(self) -> str:
        """Override in subclasses to render panel content."""
        return "No data available"


class AgentStatusPanel(Static):
    """Panel displaying agent status."""

    branch_name: reactive[Optional[str]] = reactive(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Agent Status"

    def watch_branch_name(self, branch_name: Optional[str]):
        """Update when ticket_id changes."""
        self.update_content()

    def update_content(self):
        """Update the panel content."""
        if not self.branch_name:
            self.update("No ticket selected")
            return

        agent_status = read_agent_status(self.branch_name)
        if not agent_status:
            self.update("⚙ Idle: Waiting for agent to start")
            return

        # Format status
        status_symbols = {
            'idle': '⚙',
            'working': '⚙',
            'complete': '✓',
            'blocked': '⚠',
            'error': '✗',
        }
        symbol = status_symbols.get(agent_status.status, '○')

        lines = []
        lines.append(f"{symbol} Status: {agent_status.status}")

        if agent_status.current_task:
            lines.append(f"Task: {agent_status.current_task}")

        if agent_status.last_update:
            lines.append(f"Updated: {format_time_ago(agent_status.last_update)}")

        if agent_status.blocked:
            lines.append("[yellow]⚠ Blocked[/yellow]")

        self.update("\n".join(lines))


class GitStatusPanel(Static):
    """Panel displaying git status."""

    branch_name: reactive[Optional[str]] = reactive(None)
    worktree_path: reactive[Optional[str]] = reactive(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Git Status"

    def watch_branch_name(self, branch_name: Optional[str]):
        """Update when ticket_id changes."""
        self.update_content()

    def watch_worktree_path(self, worktree_path: Optional[str]):
        """Update when worktree_path changes."""
        self.update_content()

    def update_content(self):
        """Update the panel content."""
        if not self.branch_name or not self.worktree_path:
            self.update("No ticket selected")
            return

        config = load_config()
        git_status = get_git_status(
            self.worktree_path,
            use_cache=True,
            cache_seconds=config.git_status_cache_seconds
        )

        if not git_status:
            self.update("Unable to query git status")
            return

        lines = []
        lines.append(f"Branch: {git_status.current_branch}")
        lines.append(f"Modified: {len(git_status.modified_files)} files")
        lines.append(f"Untracked: {len(git_status.untracked_files)} files")
        lines.append(f"Commits ahead: {git_status.commits_ahead}")

        if git_status.last_commit:
            lines.append(f"Last commit: \"{git_status.last_commit}\"")
            if git_status.last_commit_time:
                lines.append(f"             {format_time_ago(git_status.last_commit_time)}")

        self.update("\n".join(lines))


class BuildStatusPanel(Static):
    """Panel displaying build status."""

    branch_name: reactive[Optional[str]] = reactive(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Build Status"

    def watch_branch_name(self, branch_name: Optional[str]):
        """Update when ticket_id changes."""
        self.update_content()

    def update_content(self):
        """Update the panel content."""
        if not self.branch_name:
            self.update("No ticket selected")
            return

        build_status = read_build_status(self.branch_name)
        if not build_status:
            self.update("? Unknown - No builds recorded")
            return

        lines = []

        # Status indicator
        if build_status.status == "passing":
            lines.append("[green]✓ Passing[/green]")
        elif build_status.status == "failing":
            lines.append("[red]✗ Failing[/red]")
        else:
            lines.append("? Unknown")

        # Build details
        if build_status.last_build:
            details = f"Last build: {build_status.duration_seconds}s"
            if build_status.warnings > 0:
                details += f", {build_status.warnings} warnings"
            if build_status.errors:
                details += f", {len(build_status.errors)} errors"
            lines.append(details)
            lines.append(f"Completed: {format_time_ago(build_status.last_build)}")

        self.update("\n".join(lines))


class TestStatusPanel(Static):
    """Panel displaying test status."""

    branch_name: reactive[Optional[str]] = reactive(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.border_title = "Test Status"

    def watch_branch_name(self, branch_name: Optional[str]):
        """Update when ticket_id changes."""
        self.update_content()

    def update_content(self):
        """Update the panel content."""
        if not self.branch_name:
            self.update("No ticket selected")
            return

        test_status = read_test_status(self.branch_name)
        if not test_status:
            self.update("? Unknown - No tests recorded")
            return

        lines = []

        # Status indicator
        if test_status.status == "passing" and test_status.total > 0:
            lines.append(f"[green]✓ {test_status.passed}/{test_status.total} passing (100%)[/green]")
        elif test_status.status == "failing" and test_status.total > 0:
            percentage = (test_status.passed / test_status.total * 100) if test_status.total > 0 else 0
            lines.append(f"[yellow]⚠ {test_status.passed}/{test_status.total} passing ({percentage:.0f}%)[/yellow]")
        else:
            lines.append("? Unknown")

        # Test details
        if test_status.last_run:
            if test_status.failed > 0:
                lines.append(f"Failed: {test_status.failed} tests")
            if test_status.skipped > 0:
                lines.append(f"Skipped: {test_status.skipped} tests")
            lines.append(f"Last run: {format_time_ago(test_status.last_run)} (took {test_status.duration_seconds}s)")

        # Show first few failures
        if test_status.failures:
            lines.append("\nFailures:")
            for failure in test_status.failures[:3]:
                lines.append(f"  • {failure.name}")

        self.update("\n".join(lines))


class TicketDetailView(VerticalScroll):
    """Detailed view of a single ticket with all status panels."""

    branch_name: reactive[Optional[str]] = reactive(None)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ticket: Optional[Ticket] = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="detail-container"):
            yield Static("No ticket selected", id="ticket-header")
            yield AgentStatusPanel(id="agent-panel", classes="status-panel")
            yield GitStatusPanel(id="git-panel", classes="status-panel")
            yield BuildStatusPanel(id="build-panel", classes="status-panel")
            yield TestStatusPanel(id="test-panel", classes="status-panel")

    def watch_branch_name(self, branch_name: Optional[str]):
        """Update when branch_name changes."""
        if branch_name:
            registry = TicketRegistry()
            self.ticket = registry.get(branch_name)
            self.update_panels()
        else:
            self.ticket = None
            self.update_panels()

    def update_panels(self):
        """Update all panels with current ticket data."""
        if not self.ticket:
            header = self.query_one("#ticket-header", Static)
            header.update("No ticket selected")
            return

        # Update header with branch name and extracted ID if available
        header = self.query_one("#ticket-header", Static)
        display_id = f"[{self.ticket.display_id}] " if self.ticket.display_id else ""
        header.update(f"[bold]{display_id}{self.ticket.branch}[/bold]\n"
                     f"Title: {self.ticket.title}\n"
                     f"Worktree: {self.ticket.worktree_path}")

        # Update all status panels - use branch (which is the primary ID)
        agent_panel = self.query_one("#agent-panel", AgentStatusPanel)
        agent_panel.branch_name = self.ticket.branch

        git_panel = self.query_one("#git-panel", GitStatusPanel)
        git_panel.branch_name = self.ticket.branch
        git_panel.worktree_path = self.ticket.worktree_path

        build_panel = self.query_one("#build-panel", BuildStatusPanel)
        build_panel.branch_name = self.ticket.branch

        test_panel = self.query_one("#test-panel", TestStatusPanel)
        test_panel.branch_name = self.ticket.branch

    def refresh_status(self):
        """Manually refresh all status panels."""
        self.update_panels()


class CommandCenterTUI(App):
    """Command Center TUI Application."""

    CSS = """
    Screen {
        layout: horizontal;
    }

    #ticket-list-container {
        width: 50%;
        height: 100%;
        border: solid $primary;
    }

    #detail-container {
        width: 50%;
        height: 100%;
        border: solid $primary;
        padding: 1;
    }

    DataTable {
        height: 100%;
    }

    .status-panel {
        border: solid $accent;
        height: auto;
        margin: 1 0;
        padding: 1;
    }

    #ticket-header {
        margin-bottom: 1;
        padding: 1;
        background: $boost;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("enter", "select", "Select", show=False),
        # Phase 3 Week 1: Git & Build
        Binding("c", "commit", "Commit"),
        Binding("p", "push", "Push"),
        Binding("P", "pull", "Pull"),
        Binding("l", "log", "Log"),
        Binding("b", "build", "Build"),
        # Phase 3 Week 2: Tests & Files
        Binding("t", "test", "Test"),
        Binding("f", "files", "Files"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry = TicketRegistry()
        self.tickets: List[Ticket] = []
        self.selected_ticket_id: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Horizontal():
            with Container(id="ticket-list-container"):
                yield DataTable(id="ticket-table", cursor_type="row")

            yield TicketDetailView(id="detail-view")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app after mounting."""
        self.title = "Command Center"
        self.sub_title = "Ticket Management TUI"

        # Setup ticket table
        table = self.query_one("#ticket-table", DataTable)
        table.add_columns("ID", "Branch", "Title", "Status", "Updated")
        table.cursor_type = "row"
        table.zebra_stripes = True

        # Load tickets
        self.load_tickets()

        # Setup auto-refresh
        config = load_config()
        self.set_interval(config.status_poll_interval, self.auto_refresh)

    def load_tickets(self):
        """Load tickets from registry."""
        self.tickets = self.registry.list_all()

        table = self.query_one("#ticket-table", DataTable)
        table.clear()

        for ticket in self.tickets:
            # Extract display ID if available
            display_id = ticket.display_id or "-"

            # Get agent status for display
            agent_status = read_agent_status(ticket.branch)
            if agent_status and agent_status.current_task:
                status_text = f"{agent_status.status}: {agent_status.current_task[:20]}"
            else:
                status_text = ticket.status

            table.add_row(
                display_id,
                ticket.branch[:25],
                ticket.title[:25],
                status_text,
                format_time_ago(ticket.updated_at),
                key=ticket.branch,
            )

        # Select first ticket if available
        if self.tickets and not self.selected_ticket_id:
            self.selected_ticket_id = self.tickets[0].branch
            self.update_detail_view()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in ticket table."""
        self.selected_ticket_id = event.row_key.value
        self.update_detail_view()

    def update_detail_view(self):
        """Update the detail view with selected ticket."""
        detail_view = self.query_one("#detail-view", TicketDetailView)
        detail_view.branch_name = self.selected_ticket_id

    def action_refresh(self):
        """Manually refresh all data."""
        self.load_tickets()
        detail_view = self.query_one("#detail-view", TicketDetailView)
        detail_view.refresh_status()
        self.notify("Refreshed all data")

    def auto_refresh(self):
        """Auto-refresh data periodically."""
        # Only update detail view to avoid disrupting table navigation
        detail_view = self.query_one("#detail-view", TicketDetailView)
        detail_view.refresh_status()

    def action_cursor_down(self):
        """Move cursor down in table."""
        table = self.query_one("#ticket-table", DataTable)
        table.action_cursor_down()

    def action_cursor_up(self):
        """Move cursor up in table."""
        table = self.query_one("#ticket-table", DataTable)
        table.action_cursor_up()

    # Phase 3: New action methods

    def _get_selected_ticket(self) -> Optional[Ticket]:
        """Get the currently selected ticket."""
        if not self.selected_ticket_id:
            return None
        for ticket in self.tickets:
            if ticket.branch == self.selected_ticket_id:
                return ticket
        return None

    def action_commit(self):
        """Show commit dialog for selected ticket."""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        def on_commit_complete(result):
            """Handle commit completion."""
            if result and result.get("success"):
                self.notify(result.get("message", "Commit created successfully"), severity="information")
                # Refresh git status panel
                self.action_refresh()
            # If result is None, user cancelled

        self.push_screen(
            CommitDialog(Path(ticket.worktree_path), ticket.branch),
            on_commit_complete
        )

    def action_push(self):
        """Push to remote with confirmation."""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        config = load_config()

        def on_confirm(confirmed: bool):
            """Handle push confirmation."""
            if not confirmed:
                return

            # Perform push in background
            self.notify("Pushing to remote...", severity="information")

            # Use textual's worker to run in background
            import threading

            def do_push():
                result = push_to_remote(
                    Path(ticket.worktree_path),
                    remote=config.default_git_remote,
                    branch=ticket.branch,
                )

                # Update UI from main thread
                self.call_from_thread(self._on_push_complete, result)

            thread = threading.Thread(target=do_push, daemon=True)
            thread.start()

        self.push_screen(
            ConfirmDialog(
                "Push to Remote",
                f"Push branch '{ticket.branch}' to {config.default_git_remote}?",
            ),
            on_confirm
        )

    def _on_push_complete(self, result):
        """Handle push completion."""
        if result.success:
            self.push_screen(
                SuccessDialog("Push Successful", result.message)
            )
        else:
            self.push_screen(
                ErrorDialog("Push Failed", result.message)
            )
        # Refresh git status
        self.action_refresh()

    def action_pull(self):
        """Pull from remote with confirmation."""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        config = load_config()

        def on_confirm(confirmed: bool):
            """Handle pull confirmation."""
            if not confirmed:
                return

            # Perform pull in background
            self.notify("Pulling from remote...", severity="information")

            import threading

            def do_pull():
                result = pull_from_remote(
                    Path(ticket.worktree_path),
                    remote=config.default_git_remote,
                    branch=ticket.branch,
                )

                self.call_from_thread(self._on_pull_complete, result)

            thread = threading.Thread(target=do_pull, daemon=True)
            thread.start()

        self.push_screen(
            ConfirmDialog(
                "Pull from Remote",
                f"Pull branch '{ticket.branch}' from {config.default_git_remote}?",
            ),
            on_confirm
        )

    def _on_pull_complete(self, result):
        """Handle pull completion."""
        if result.success:
            self.push_screen(
                SuccessDialog("Pull Successful", result.message)
            )
        else:
            self.push_screen(
                ErrorDialog("Pull Failed", result.message)
            )
        # Refresh git status
        self.action_refresh()

    def action_log(self):
        """Show commit log for selected ticket."""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        # Fetch commit log
        commits, error = get_commit_log(Path(ticket.worktree_path), limit=20)

        if error:
            self.push_screen(
                ErrorDialog("Failed to Load Log", error)
            )
            return

        self.push_screen(
            LogDialog(commits, ticket.branch)
        )

    def action_build(self):
        """Trigger build for selected ticket."""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        config = load_config()
        build_command = config.get_build_command(Path(ticket.worktree_path))

        # Create output dialog
        output_dialog = OutputDialog("Building", build_command)

        # Callbacks for streaming
        def on_output(line: str):
            """Handle build output line."""
            self.call_from_thread(output_dialog.append_output, line)

        def on_complete(success: bool, message: str):
            """Handle build completion."""
            self.call_from_thread(output_dialog.set_complete, success, message)
            # Refresh build status panel
            self.call_from_thread(self.action_refresh)

        # Start the build
        run_build(
            Path(ticket.worktree_path),
            ticket.branch,
            on_output=on_output,
            on_complete=on_complete,
        )

        # Show the dialog
        self.push_screen(output_dialog)

    def action_test(self):
        """Trigger tests for selected ticket."""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        config = load_config()
        test_command = config.get_test_command(Path(ticket.worktree_path))

        # Create output dialog
        output_dialog = OutputDialog("Running Tests", test_command)

        # Callbacks for streaming
        def on_output(line: str):
            """Handle test output line."""
            self.call_from_thread(output_dialog.append_output, line)

        def on_complete(success: bool, message: str):
            """Handle test completion."""
            self.call_from_thread(output_dialog.set_complete, success, message)
            # Refresh test status panel
            self.call_from_thread(self.action_refresh)

        # Start the tests
        run_tests(
            Path(ticket.worktree_path),
            ticket.branch,
            on_output=on_output,
            on_complete=on_complete,
        )

        # Show the dialog
        self.push_screen(output_dialog)

    def action_files(self):
        """Show file browser/preview for selected ticket."""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        def on_file_action(result):
            """Handle file browser result."""
            if result and result.get("action") == "edit":
                file_path = result.get("file_path")
                if file_path:
                    self._open_in_editor(file_path)

        self.push_screen(
            FileBrowserDialog(Path(ticket.worktree_path), ticket.branch),
            on_file_action
        )

    def _open_in_editor(self, file_path: str):
        """Open the workspace folder in the configured editor with the file selected."""
        import subprocess
        import os

        config = load_config()

        # Try to get editor from config, then environment, then default to cursor
        editor = getattr(config, "editor", None) or os.environ.get("EDITOR") or "cursor"

        try:
            file_path_obj = Path(file_path)

            # Find the git worktree root by looking for .git
            worktree_root = file_path_obj.parent
            while worktree_root != worktree_root.parent:  # Stop at filesystem root
                if (worktree_root / ".git").exists():
                    break
                worktree_root = worktree_root.parent

            # Open workspace folder with the file as an argument
            # Use --goto file:line:column syntax if available, or just pass both folder and file
            subprocess.run([editor, str(worktree_root), str(file_path)], check=False)
            self.notify(f"Opened {file_path_obj.name} in {editor}", severity="information")
        except Exception as e:
            self.push_screen(
                ErrorDialog("Failed to Open Editor", f"Could not open {editor}: {e}")
            )


def run_tui():
    """Run the Command Center TUI."""
    app = CommandCenterTUI()
    app.run()
