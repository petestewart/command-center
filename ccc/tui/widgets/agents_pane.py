"""
AgentsPane widget for managing multiple agent sessions.

Container that displays all active agent sessions with scrolling support,
handles refresh updates, and routes button actions to the main app.
"""

from typing import Optional, List
from textual.app import ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import Static, Button
from textual.message import Message

from ccc.multi_agent_manager import MultiAgentManager
from ccc.tui.widgets.agent_card import AgentCard
from ccc.status import AgentSession


class AgentsPane(Static):
    """
    Container for displaying multiple agent cards.

    Features:
    - Scrollable list of agent cards
    - Auto-refresh from MultiAgentManager
    - New agent button
    - Routes Open/Archive actions to main app
    """

    DEFAULT_CSS = """
    AgentsPane {
        width: 100%;
        height: 100%;
        border: solid $primary;
        padding: 0;
    }

    AgentsPane .agents-header {
        height: 3;
        background: $panel;
        padding: 1 2;
        border-bottom: solid $primary;
    }

    AgentsPane .agents-scroll {
        width: 100%;
        height: 1fr;
        padding: 1 2;
    }

    AgentsPane .no-agents {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }
    """

    class NewAgentRequested(Message):
        """Posted when user clicks New Agent button."""
        pass

    class OpenAgentRequested(Message):
        """Posted when user wants to open an agent's terminal."""

        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    class ArchiveAgentRequested(Message):
        """Posted when user wants to archive an agent session."""

        def __init__(self, session_id: str) -> None:
            super().__init__()
            self.session_id = session_id

    def __init__(
        self,
        agent_manager: Optional[MultiAgentManager] = None,
        **kwargs
    ):
        """
        Initialize agents pane.

        Args:
            agent_manager: MultiAgentManager instance (optional)
            **kwargs: Additional widget arguments
        """
        super().__init__(**kwargs)
        self.agent_manager = agent_manager
        self.border_title = "Active Agents"

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        # Header with New Agent button
        with Vertical(classes="agents-header"):
            yield Button(
                "+ New Agent",
                id="new_agent_btn",
                variant="success",
            )

        # Scrollable container for agent cards
        yield VerticalScroll(id="agents_scroll", classes="agents-scroll")

    def on_mount(self) -> None:
        """Called when widget is mounted."""
        # Initial refresh
        self.refresh_agents()

    def refresh_agents(self) -> None:
        """
        Refresh agent cards from MultiAgentManager.

        This is called periodically by the app's polling mechanism.
        It updates the display to match the current state.
        """
        if not self.agent_manager:
            self._show_no_manager()
            return

        # Get current sessions
        sessions = self.agent_manager.list_sessions()

        # Get scroll container
        try:
            scroll_container = self.query_one("#agents_scroll", VerticalScroll)
        except:
            # Container not mounted yet
            return

        # Clear existing cards
        scroll_container.remove_children()

        if not sessions:
            # Show empty state
            scroll_container.mount(
                Static(
                    "No active agents\n\nClick '+ New Agent' to start a session",
                    classes="no-agents",
                )
            )
        else:
            # Create card for each session
            for session in sessions:
                card = AgentCard(session)
                scroll_container.mount(card)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button clicks.

        Args:
            event: Button pressed event
        """
        if event.button.id == "new_agent_btn":
            # New Agent button clicked
            self.post_message(self.NewAgentRequested())
            event.stop()

    def on_agent_card_open_requested(self, event: AgentCard.OpenRequested) -> None:
        """
        Handle Open button from agent card.

        Args:
            event: Open requested event from AgentCard
        """
        # Re-post as our own message for the app to handle
        self.post_message(self.OpenAgentRequested(event.session_id))

    def on_agent_card_archive_requested(self, event: AgentCard.ArchiveRequested) -> None:
        """
        Handle Archive button from agent card.

        Args:
            event: Archive requested event from AgentCard
        """
        # Re-post as our own message for the app to handle
        self.post_message(self.ArchiveAgentRequested(event.session_id))

        # Refresh after archive
        self.refresh_agents()

    def _show_no_manager(self) -> None:
        """Show message when no agent manager is available."""
        try:
            scroll_container = self.query_one("#agents_scroll", VerticalScroll)
            scroll_container.remove_children()
            scroll_container.mount(
                Static(
                    "No ticket selected\n\nSelect a ticket to view agents",
                    classes="no-agents",
                )
            )
        except:
            pass

    def set_agent_manager(self, agent_manager: Optional[MultiAgentManager]) -> None:
        """
        Set or update the agent manager.

        Args:
            agent_manager: MultiAgentManager instance or None
        """
        self.agent_manager = agent_manager
        self.refresh_agents()

    def get_session_count(self) -> int:
        """
        Get the number of active sessions.

        Returns:
            Number of active agent sessions
        """
        if not self.agent_manager:
            return 0
        return len(self.agent_manager.list_sessions())
