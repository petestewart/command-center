"""
AgentCard widget for displaying individual agent session.

Shows agent status, current files, TODO list, and action buttons.
"""

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Button
from textual.message import Message
from rich.text import Text

from ccc.status import AgentSession
from ccc.utils import format_time_ago


class AgentCard(Static):
    """
    Display card for an individual agent session.

    Shows:
    - Header with emoji, title, and progress bar
    - Current files being worked on
    - TODO list with completion status
    - Action buttons (Open, Archive)
    """

    DEFAULT_CSS = """
    AgentCard {
        width: 100%;
        height: auto;
        border: solid $primary;
        padding: 1 2;
        margin: 0 0 1 0;
        background: $panel;
    }

    AgentCard:focus {
        border: solid $accent;
    }

    AgentCard.completed {
        border: solid $success;
    }

    AgentCard.error {
        border: solid $error;
    }

    AgentCard .card-header {
        height: 1;
        margin: 0 0 1 0;
    }

    AgentCard .card-files {
        height: auto;
        margin: 0 0 1 0;
        color: $text-muted;
    }

    AgentCard .card-todos {
        height: auto;
        margin: 0 0 1 0;
    }

    AgentCard .card-actions {
        height: auto;
    }

    AgentCard Button {
        margin: 0 1 0 0;
    }
    """

    class OpenRequested(Message):
        """Posted when user clicks Open button."""

        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    class ArchiveRequested(Message):
        """Posted when user clicks Archive button."""

        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    def __init__(self, session: AgentSession, **kwargs):
        """
        Initialize agent card.

        Args:
            session: AgentSession to display
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.session = session

        # Set CSS classes based on status
        if session.status == 'completed':
            self.add_class('completed')
        elif session.status == 'error':
            self.add_class('error')

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        # Header
        yield Static(
            self._render_header(),
            classes="card-header",
        )

        # Current files
        if self.session.current_files:
            yield Static(
                self._render_files(),
                classes="card-files",
            )

        # TODO list
        if self.session.todo_list:
            yield Static(
                self._render_todos(),
                classes="card-todos",
            )

        # Actions
        with Horizontal(classes="card-actions"):
            yield Button(
                "Open",
                id=f"open_{self.session.id}",
                variant="primary",
            )
            yield Button(
                "Archive",
                id=f"archive_{self.session.id}",
                variant="default",
            )

    def _render_header(self) -> Text:
        """
        Render card header with status emoji, title, and progress.

        Returns:
            Rich Text object
        """
        text = Text()

        # Status emoji
        emoji = self._get_status_emoji(self.session.status)
        text.append(f"{emoji} ", style="bold")

        # Title
        text.append(self.session.title, style="bold")

        # Progress bar (if available)
        if self.session.progress_percent is not None:
            progress_bar = self._render_progress_bar(self.session.progress_percent)
            text.append(f"  {progress_bar}")
            text.append(f" {self.session.progress_percent}%", style="dim")

        # Time info
        if self.session.last_active:
            time_ago = format_time_ago(self.session.last_active)
            text.append(f" ({time_ago})", style="dim")

        return text

    def _render_files(self) -> Text:
        """
        Render current files list.

        Returns:
            Rich Text object
        """
        text = Text()
        text.append("Files: ", style="bold")

        # Show up to 3 files
        files_to_show = self.session.current_files[:3]
        text.append(", ".join(files_to_show))

        if len(self.session.current_files) > 3:
            remaining = len(self.session.current_files) - 3
            text.append(f" (+{remaining} more)", style="dim")

        return text

    def _render_todos(self) -> Text:
        """
        Render TODO list.

        Returns:
            Rich Text object
        """
        text = Text()

        # Show up to 5 TODOs
        todos_to_show = self.session.todo_list[:5]

        for i, todo in enumerate(todos_to_show):
            if i > 0:
                text.append("\n")

            # Icon based on status
            if todo.completed:
                text.append("✓ ", style="green")
                text.append(todo.text, style="dim")
            elif todo.blocked:
                text.append("✗ ", style="red")
                text.append(todo.text, style="yellow")
            else:
                text.append("○ ", style="dim")
                text.append(todo.text)

        # Show count if more TODOs
        if len(self.session.todo_list) > 5:
            remaining = len(self.session.todo_list) - 5
            text.append(f"\n... and {remaining} more", style="dim")

        return text

    def _render_progress_bar(self, percent: int) -> str:
        """
        Render ASCII progress bar.

        Args:
            percent: Progress percentage (0-100)

        Returns:
            Progress bar string
        """
        width = 10
        filled = int((percent / 100) * width)
        empty = width - filled

        return "[" + ("█" * filled) + ("░" * empty) + "]"

    def _get_status_emoji(self, status: str) -> str:
        """
        Get emoji for agent status.

        Args:
            status: Agent status string

        Returns:
            Emoji character
        """
        emojis = {
            'idle': '⚙',
            'working': '⚙',
            'waiting': '⏸',
            'completed': '✓',
            'error': '✗',
        }
        return emojis.get(status, '○')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button clicks.

        Args:
            event: Button pressed event
        """
        button_id = event.button.id

        if button_id and button_id.startswith('open_'):
            # Open button clicked
            self.post_message(self.OpenRequested(self.session.id))
            event.stop()

        elif button_id and button_id.startswith('archive_'):
            # Archive button clicked
            self.post_message(self.ArchiveRequested(self.session.id))
            event.stop()

    def update_session(self, session: AgentSession) -> None:
        """
        Update the card with new session data.

        Args:
            session: Updated AgentSession
        """
        self.session = session

        # Update CSS classes
        self.remove_class('completed', 'error')
        if session.status == 'completed':
            self.add_class('completed')
        elif session.status == 'error':
            self.add_class('error')

        # Refresh display
        self.refresh(layout=True)
