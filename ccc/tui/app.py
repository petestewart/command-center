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
from ccc.tui.widgets import StatusBar
from ccc.status_monitor import StatusMonitor
from ccc.tasks_manager import TasksManager
from ccc.tui.widgets.tasks_pane import TasksPane

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
            # Phase 6: Question notification banner
            from ccc.tui.chat_widgets import QuestionNotificationBanner
            yield QuestionNotificationBanner("", id="question-banner")
            yield AgentStatusPanel(id="agent-panel", classes="status-panel")
            yield GitStatusPanel(id="git-panel", classes="status-panel")
            yield BuildStatusPanel(id="build-panel", classes="status-panel")
            yield TestStatusPanel(id="test-panel", classes="status-panel")
            # Phase 4: Add todo panel
            from ccc.tui.widgets import TodoListWidget
            yield TodoListWidget("", id="todo-panel", classes="status-panel")
            # Phase 7: Add API request panel
            from ccc.tui.api_widgets import ApiRequestListPanel
            yield ApiRequestListPanel(branch_name="", id="api-panel", classes="status-panel")

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

        # Phase 6: Update question notification banner
        from ccc.tui.chat_widgets import QuestionNotificationBanner
        question_banner = self.query_one("#question-banner", QuestionNotificationBanner)
        question_banner.branch_name = self.ticket.branch

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

        # Phase 4: Update todo panel
        from ccc.tui.widgets import TodoListWidget
        todo_panel = self.query_one("#todo-panel", TodoListWidget)
        todo_panel.branch_name = self.ticket.branch
        todo_panel.refresh_content()

        # Phase 7: Update API panel
        from ccc.tui.api_widgets import ApiRequestListPanel
        api_panel = self.query_one("#api-panel", ApiRequestListPanel)
        api_panel.branch_name = self.ticket.branch
        api_panel.refresh_requests()

    def refresh_status(self):
        """Manually refresh all status panels."""
        # Call update_panels but don't pass focus_on_load flag
        # This is called by auto_refresh timer, so we don't want to steal focus
        if not self.ticket:
            self.update_panels()
            return

        # Update status panels without forcing focus
        from ccc.tui.widgets import TodoListWidget
        from ccc.tui.chat_widgets import QuestionNotificationBanner

        # Phase 6: Refresh question notification banner
        question_banner = self.query_one("#question-banner", QuestionNotificationBanner)
        question_banner.update_count()

        # Update all status panels
        agent_panel = self.query_one("#agent-panel", AgentStatusPanel)
        agent_panel.branch_name = self.ticket.branch

        git_panel = self.query_one("#git-panel", GitStatusPanel)
        git_panel.branch_name = self.ticket.branch
        git_panel.worktree_path = self.ticket.worktree_path

        build_panel = self.query_one("#build-panel", BuildStatusPanel)
        build_panel.branch_name = self.ticket.branch

        test_panel = self.query_one("#test-panel", TestStatusPanel)
        test_panel.branch_name = self.ticket.branch

        # Refresh todo panel content only, don't refocus
        todo_panel = self.query_one("#todo-panel", TodoListWidget)
        todo_panel.refresh_content()

        # Phase 7: Refresh API panel
        from ccc.tui.api_widgets import ApiRequestListPanel
        api_panel = self.query_one("#api-panel", ApiRequestListPanel)
        api_panel.refresh_requests()


class CommandCenterTUI(App):
    """Command Center TUI Application."""

    CSS = """
    Screen {
        layout: vertical;
    }

    Horizontal {
        height: 1fr;
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
        overflow: auto;
    }

    DataTable {
        height: 100%;
    }

    .status-panel {
        border: solid $accent;
        height: auto;
        max-height: 12;
        margin: 1 0;
        padding: 1;
        overflow: auto;
    }

    .status-panel:focus {
        border: solid $primary;
        background: $boost;
    }

    #ticket-header {
        margin-bottom: 1;
        padding: 1;
        background: $boost;
        height: auto;
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
        # Phase 4: Tasks Pane (Note: Key binding will be finalized in Phase 5)
        Binding("T", "toggle_tasks", "Toggle Tasks"),
        # Phase 6: Questions & Sessions
        Binding("R", "reply_question", "Reply"),
        Binding("s", "start_session", "Start Session"),
        Binding("S", "resume_session", "Resume Session"),
        Binding("v", "view_session", "View Session"),
        # Phase 7: API Testing
        Binding("a", "api_request", "API"),
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registry = TicketRegistry()
        self.tickets: List[Ticket] = []
        self.selected_ticket_id: Optional[str] = None
        self.config = load_config()
        self.status_monitor: Optional[StatusMonitor] = None
        self.tasks_manager: Optional[TasksManager] = None
        self.tasks_pane_visible: bool = True  # Tasks pane visible by default

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Horizontal():
            with Container(id="ticket-list-container"):
                yield DataTable(id="ticket-table", cursor_type="row")

            yield TicketDetailView(id="detail-view")

        # Phase 1: Status bar showing server, database, build, and test status
        yield StatusBar(id="status-bar")

        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app after mounting."""
        self.title = "Command Center"
        self.sub_title = "Ticket Management TUI"

        # Setup ticket table
        table = self.query_one("#ticket-table", DataTable)
        table.add_columns("ID", "Branch", "Title", "Progress", "Status", "Updated")
        table.cursor_type = "row"
        table.zebra_stripes = True

        # Load tickets
        self.load_tickets()

        # Phase 4: Initialize TasksManager
        config = load_config()
        self.tasks_manager = TasksManager(tasks_file=config.tasks_file)

        # Setup auto-refresh
        self.set_interval(config.status_poll_interval, self.auto_refresh)

        # Phase 4: Setup tasks refresh (every 3 seconds for file change detection)
        self.set_interval(3.0, self.refresh_tasks)

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

            # Phase 4: Get todo progress
            from ccc.todo import list_todos
            todo_list = list_todos(ticket.branch)
            if todo_list.items:
                stats = todo_list.progress_stats()
                percentage = todo_list.progress_percentage()
                progress_text = f"{stats['done']}/{stats['total']} ({percentage:.0f}%)"
            else:
                progress_text = "-"

            table.add_row(
                display_id,
                ticket.branch[:25],
                ticket.title[:25],
                progress_text,
                status_text,
                format_time_ago(ticket.updated_at),
                key=ticket.branch,
            )

        # Select first ticket if available
        if self.tickets and not self.selected_ticket_id:
            self.selected_ticket_id = self.tickets[0].branch
            self.update_detail_view()
            self.update_status_bar()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in ticket table."""
        self.selected_ticket_id = event.row_key.value
        self.update_detail_view()
        self.update_status_bar()

    def update_detail_view(self):
        """Update the detail view with selected ticket."""
        detail_view = self.query_one("#detail-view", TicketDetailView)
        detail_view.branch_name = self.selected_ticket_id

    def update_status_bar(self):
        """Update the status bar with current branch status."""
        if not self.selected_ticket_id:
            return

        # Initialize or update status monitor for this branch
        if not self.status_monitor or self.status_monitor.branch_name != self.selected_ticket_id:
            self.status_monitor = StatusMonitor(
                branch_name=self.selected_ticket_id,
                config=self.config.to_dict(),
                on_status_change=self._on_status_change,
            )

        # Load current status and update the status bar widget
        status = self.status_monitor.load_status()
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.status = status.to_dict()

    def _on_status_change(self, status):
        """Callback when status changes in StatusMonitor."""
        # Update status bar widget with new status
        try:
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.status = status.to_dict()
        except Exception:
            # Status bar might not be mounted yet
            pass

    def action_refresh(self):
        """Manually refresh all data."""
        self.load_tickets()
        detail_view = self.query_one("#detail-view", TicketDetailView)
        detail_view.refresh_status()
        self.update_status_bar()
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
            try:
                self.call_from_thread(output_dialog.set_complete, success, message)
                # Refresh build status panel
                self.call_from_thread(self.action_refresh)
            except Exception as e:
                # Ensure dialog is marked complete even if there's an error
                try:
                    self.call_from_thread(output_dialog.set_complete, False, f"Error: {e}")
                except Exception:
                    pass  # Last resort - dialog can still be closed with escape

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
            try:
                self.call_from_thread(output_dialog.set_complete, success, message)
                # Refresh test status panel
                self.call_from_thread(self.action_refresh)
            except Exception as e:
                # Ensure dialog is marked complete even if there's an error
                try:
                    self.call_from_thread(output_dialog.set_complete, False, f"Error: {e}")
                except Exception:
                    pass  # Last resort - dialog can still be closed with escape

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
                line = result.get("line")
                worktree_root = result.get("worktree_root")
                if file_path:
                    self._open_in_editor(file_path, line=line, worktree_root=worktree_root)

        self.push_screen(
            FileBrowserDialog(Path(ticket.worktree_path), ticket.branch),
            on_file_action
        )

    def _open_in_editor(
        self,
        file_path: str,
        line: Optional[int] = None,
        worktree_root: Optional[str] = None
    ):
        """
        Open a file in the configured editor.

        Args:
            file_path: Path to the file to open
            line: Optional line number to jump to
            worktree_root: Optional worktree root directory
        """
        from ccc.editor_manager import open_in_editor

        config = load_config()

        # Get editor from config
        config_editor = getattr(config, "editor", None)

        # Convert paths
        file_path_obj = Path(file_path)
        worktree_root_obj = Path(worktree_root) if worktree_root else None

        # If no worktree root provided, try to find it
        if not worktree_root_obj:
            worktree_root_obj = file_path_obj.parent
            while worktree_root_obj != worktree_root_obj.parent:
                if (worktree_root_obj / ".git").exists():
                    break
                worktree_root_obj = worktree_root_obj.parent

        # Open file using editor manager
        success, message = open_in_editor(
            file_path_obj,
            line=line,
            worktree_root=worktree_root_obj,
            config_editor=config_editor
        )

        if success:
            self.notify(message, severity="information")
        else:
            self.push_screen(
                ErrorDialog("Failed to Open Editor", message)
            )

    def action_api_request(self):
        """Show API request builder for selected ticket."""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        from ccc.tui.api_widgets import RequestBuilderDialog

        def on_request_saved(result):
            """Handle request save completion."""
            if result and result.get("success"):
                self.notify(result.get("message", "Request saved"), severity="information")
                # Refresh the API panel
                self.action_refresh()

        self.push_screen(
            RequestBuilderDialog(ticket.branch),
            on_request_saved
        )

    # Phase 4: Todo management actions

    def on_todo_list_widget_todo_action(self, message):
        """Handle todo actions from TodoListWidget."""
        from ccc.tui.widgets import TodoListWidget

        action = message.action
        task_id = message.task_id

        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        if action == "add":
            self._handle_add_todo(ticket)
        elif action == "edit":
            self._handle_edit_todo(ticket, task_id)
        elif action == "delete":
            self._handle_delete_todo(ticket, task_id)
        elif action == "assign":
            self._handle_assign_todo(ticket, task_id)
        elif action == "block":
            self._handle_block_todo(ticket, task_id)
        elif action == "move":
            self._handle_move_todo(ticket, task_id)

    def _handle_add_todo(self, ticket: Ticket):
        """Handle adding a new todo."""
        from ccc.tui.dialogs import AddTodoDialog

        def on_result(result):
            if result:
                from ccc.todo import add_todo

                try:
                    item = add_todo(
                        ticket.branch,
                        result["description"],
                        estimated_minutes=result.get("estimate"),
                        assigned_agent=result.get("assign"),
                    )
                    self.notify(f"Added todo #{item.id}", severity="information")
                    self.action_refresh()
                except Exception as e:
                    self.notify(f"Error adding todo: {e}", severity="error")

        self.push_screen(AddTodoDialog(ticket.branch), on_result)

    def _handle_edit_todo(self, ticket: Ticket, task_id: int):
        """Handle editing a todo."""
        from ccc.tui.dialogs import EditTodoDialog
        from ccc.todo import list_todos, update_todo_description

        # Get current description
        todo_list = list_todos(ticket.branch)
        item = todo_list.get_item(task_id)
        if not item:
            self.notify(f"Todo #{task_id} not found", severity="warning")
            return

        def on_result(result):
            if result:
                try:
                    update_todo_description(
                        ticket.branch,
                        result["task_id"],
                        result["description"],
                    )
                    self.notify(f"Updated todo #{task_id}", severity="information")
                    self.action_refresh()
                except Exception as e:
                    self.notify(f"Error updating todo: {e}", severity="error")

        self.push_screen(
            EditTodoDialog(ticket.branch, task_id, item.description),
            on_result
        )

    def _handle_delete_todo(self, ticket: Ticket, task_id: int):
        """Handle deleting a todo."""
        from ccc.tui.dialogs import ConfirmDialog
        from ccc.todo import delete_todo

        def on_confirm(confirmed: bool):
            if confirmed:
                try:
                    if delete_todo(ticket.branch, task_id):
                        self.notify(f"Deleted todo #{task_id}", severity="information")
                        self.action_refresh()
                    else:
                        self.notify(f"Todo #{task_id} not found", severity="warning")
                except Exception as e:
                    self.notify(f"Error deleting todo: {e}", severity="error")

        self.push_screen(
            ConfirmDialog(
                "Delete Todo",
                f"Are you sure you want to delete todo #{task_id}?",
            ),
            on_confirm
        )

    def _handle_assign_todo(self, ticket: Ticket, task_id: int):
        """Handle assigning a todo."""
        from ccc.tui.dialogs import AssignTodoDialog
        from ccc.todo import list_todos, assign_todo

        # Get current assignment
        todo_list = list_todos(ticket.branch)
        item = todo_list.get_item(task_id)
        if not item:
            self.notify(f"Todo #{task_id} not found", severity="warning")
            return

        def on_result(result):
            if result:
                try:
                    assign_todo(
                        ticket.branch,
                        result["task_id"],
                        result["agent"],
                    )
                    if result["agent"]:
                        self.notify(
                            f"Assigned todo #{task_id} to {result['agent']}",
                            severity="information"
                        )
                    else:
                        self.notify(f"Unassigned todo #{task_id}", severity="information")
                    self.action_refresh()
                except Exception as e:
                    self.notify(f"Error assigning todo: {e}", severity="error")

        self.push_screen(
            AssignTodoDialog(task_id, item.assigned_agent),
            on_result
        )

    def _handle_block_todo(self, ticket: Ticket, task_id: int):
        """Handle setting a todo as blocked."""
        from ccc.tui.dialogs import BlockTodoDialog
        from ccc.todo import list_todos, set_blocked_by

        # Get current blocking status
        todo_list = list_todos(ticket.branch)
        item = todo_list.get_item(task_id)
        if not item:
            self.notify(f"Todo #{task_id} not found", severity="warning")
            return

        def on_result(result):
            if result:
                try:
                    set_blocked_by(
                        ticket.branch,
                        result["task_id"],
                        result["blocked_by"],
                    )
                    if result["blocked_by"]:
                        self.notify(
                            f"Todo #{task_id} blocked by #{result['blocked_by']}",
                            severity="information"
                        )
                    else:
                        self.notify(f"Unblocked todo #{task_id}", severity="information")
                    self.action_refresh()
                except ValueError as e:
                    self.notify(f"Error: {e}", severity="error")
                except Exception as e:
                    self.notify(f"Error blocking todo: {e}", severity="error")

        self.push_screen(
            BlockTodoDialog(task_id, item.blocked_by),
            on_result
        )

    def _handle_move_todo(self, ticket: Ticket, task_id: int):
        """Handle moving a todo to a new position."""
        from ccc.todo import list_todos, move_todo

        # For now, just show a notification that move is not yet implemented
        # In a full implementation, you'd show a dialog to get the new position
        self.notify("Move todo: Use CLI 'ccc todo move' for now", severity="information")

    # Phase 6: Question actions

    def action_reply_question(self):
        """Reply to the first unanswered question"""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        from ccc.questions import QuestionManager

        manager = QuestionManager(ticket.branch)
        unanswered = manager.get_unanswered()

        if not unanswered:
            self.notify("No unanswered questions", severity="information")
            return

        # Show first unanswered question
        question = unanswered[0]

        from ccc.tui.chat_dialogs import ReplyToQuestionDialog

        def on_reply_complete(result):
            if result and result.get("success"):
                self.notify(
                    f"Answered question from {question.agent_id}",
                    severity="information"
                )
                # Refresh to update question notification
                self.action_refresh()

        self.push_screen(
            ReplyToQuestionDialog(ticket.branch, question),
            on_reply_complete
        )

    # Session Management Actions

    def action_start_session(self):
        """Start a Claude session for the selected TODO item"""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        # Get the TodoListWidget from the detail view
        try:
            from ccc.tui.widgets import TodoListWidget
            todo_widget = self.query_one("#todo-panel", TodoListWidget)
        except Exception as e:
            self.notify(f"Could not find TODO panel: {str(e)}", severity="error")
            return

        # Get selected TODO from the widget
        if not todo_widget.todos:
            self.notify("No TODOs available. Create one first.", severity="information")
            return

        focused_idx = todo_widget._focused_index
        if focused_idx < 0 or focused_idx >= len(todo_widget.todos):
            self.notify("No TODO selected", severity="warning")
            return

        todo_item = todo_widget.todos[focused_idx]

        if todo_item.assigned_agent:
            self.notify(f"TODO already assigned to {todo_item.assigned_agent}", severity="warning")
            return

        # Start session
        from ccc.claude_session import ClaudeSessionManager

        try:
            manager = ClaudeSessionManager(ticket.branch)
            session_id, error = manager.start_session_for_todo(todo_item.id)

            if error:
                self.notify(f"Failed to start session: {error}", severity="error")
            else:
                self.notify(f"Started Claude session {session_id[:8]} for TODO #{todo_item.id}", severity="success")
                todo_widget.refresh_content()  # Refresh to show updated assignment
        except Exception as e:
            self.notify(f"Error starting session: {str(e)}", severity="error")

    def action_resume_session(self):
        """Resume a Claude session"""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        # Get active sessions
        from ccc.claude_session import ClaudeSessionManager

        try:
            manager = ClaudeSessionManager(ticket.branch)
            sessions = manager.list_active_sessions()

            if not sessions:
                self.notify("No active sessions to resume", severity="information")
                return

            # For now, resume the most recent session
            # In the future, could show a dialog to select which session
            session = sessions[-1]
            success, error = manager.resume_session(session.session_id)

            if error:
                self.notify(f"Failed to resume session: {error}", severity="error")
            else:
                self.notify(f"Resumed session {session.session_id[:8]}", severity="success")
        except Exception as e:
            self.notify(f"Error resuming session: {str(e)}", severity="error")

    def action_view_session(self):
        """Switch to the tmux window for the active session"""
        ticket = self._get_selected_ticket()
        if not ticket:
            self.notify("No ticket selected", severity="warning")
            return

        # Get the TodoListWidget from the detail view
        try:
            from ccc.tui.widgets import TodoListWidget
            todo_widget = self.query_one("#todo-panel", TodoListWidget)
        except Exception as e:
            self.notify(f"Could not find TODO panel: {str(e)}", severity="error")
            return

        # Get selected TODO from the widget
        if not todo_widget.todos:
            self.notify("No TODOs available", severity="information")
            return

        focused_idx = todo_widget._focused_index
        if focused_idx < 0 or focused_idx >= len(todo_widget.todos):
            self.notify("No TODO selected", severity="warning")
            return

        todo_item = todo_widget.todos[focused_idx]

        # Get session for this TODO
        from ccc.claude_session import ClaudeSessionManager

        try:
            manager = ClaudeSessionManager(ticket.branch)
            session = manager.get_session_for_todo(todo_item.id)

            if not session:
                self.notify(f"No active session found for TODO #{todo_item.id}", severity="warning")
                return

            # Open Claude session in a new terminal window (keeps TUI open)
            import os
            import subprocess

            # Build the command to create a grouped session and attach to specific window
            # Multiple clients attached to the same session all see the same window
            # Solution: Create a new grouped session (-t) that shares windows but has independent view
            import random
            import string
            # Generate a random session suffix to avoid conflicts
            suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            grouped_session = f"{ticket.tmux_session}-view-{suffix}"

            # Command: create grouped session, then select the specific window
            # Note: Use regular semicolons for AppleScript, not \; (those are for direct shell execution)
            # Quote the window name to handle special characters like #
            import shlex
            quoted_window = shlex.quote(session.tmux_window_name)
            tmux_cmd = f"tmux new-session -d -t {ticket.tmux_session} -s {grouped_session} && tmux select-window -t {grouped_session}:={quoted_window} && tmux attach-session -t {grouped_session}"

            # Detect terminal and open new window
            # Check if iTerm2 is running
            try:
                result = subprocess.run(
                    ["osascript", "-e", 'tell application "System Events" to get name of processes'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                processes = result.stdout.lower()

                if "iterm2" in processes or "iterm" in processes:
                    # Use iTerm2 to open new window
                    applescript = f'''
                        tell application "iTerm"
                            create window with default profile
                            tell current session of current window
                                write text "{tmux_cmd}"
                            end tell
                        end tell
                    '''
                    subprocess.Popen(["osascript", "-e", applescript])
                    self.notify(f"Opened Claude session in new iTerm2 window", severity="success")
                else:
                    # Use Terminal.app
                    applescript = f'''
                        tell application "Terminal"
                            do script "{tmux_cmd}"
                            activate
                        end tell
                    '''
                    subprocess.Popen(["osascript", "-e", applescript])
                    self.notify(f"Opened Claude session in new Terminal window", severity="success")

            except Exception as e:
                # Fallback: just show the user the command
                self.notify(f"Run this in a new terminal: {tmux_cmd}", severity="information", timeout=10)

        except Exception as e:
            self.notify(f"Error viewing session: {str(e)}", severity="error")

    def refresh_tasks(self):
        """Refresh tasks from TASKS.md file (called every 3 seconds)."""
        if not self.tasks_manager:
            return

        # Load tasks to update cache if file has changed
        # The TasksManager internally checks modification time
        self.tasks_manager.load_tasks()

    def action_toggle_tasks(self):
        """Toggle tasks pane visibility.

        Note: Full toggle behavior will be implemented in Phase 5 (Layout Refactoring).
        For now, this action is registered but doesn't change layout.
        """
        self.tasks_pane_visible = not self.tasks_pane_visible
        # Phase 5 will implement the actual layout change
        # For now, just notify the user
        if self.tasks_pane_visible:
            self.notify("Tasks pane enabled (layout toggle in Phase 5)", severity="information")
        else:
            self.notify("Tasks pane disabled (layout toggle in Phase 5)", severity="information")


def run_tui():
    """Run the Command Center TUI."""
    app = CommandCenterTUI()
    app.run()
