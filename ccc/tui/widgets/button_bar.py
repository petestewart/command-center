"""
Button bar widget for Command Center TUI.

Provides quick-launch buttons for external tools and pane toggles.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static, Button
from textual.message import Message
from textual.reactive import reactive


class ButtonBar(Static):
    """
    Button bar widget with quick-launch buttons.

    Displays buttons for:
    - Pane toggles (Tasks, Agents)
    - External tool launchers (Plan, Git, API, Notes, Jira, Database)
    - Status actions (Server, Build, Tests)
    """

    # Reactive property to track active pane
    active_pane: reactive[str] = reactive("tasks")

    # CSS classes for styling
    DEFAULT_CSS = """
    ButtonBar {
        height: 3;
        background: $panel;
        border-top: solid $primary;
        padding: 1 2;
    }

    ButtonBar Button {
        margin: 0 1;
        min-width: 8;
    }

    ButtonBar .separator {
        color: $text-muted;
        padding: 0 1;
    }
    """

    class ButtonClicked(Message):
        """Message posted when a button is clicked."""

        def __init__(self, button_id: str) -> None:
            """
            Initialize the message.

            Args:
                button_id: ID of the clicked button
            """
            super().__init__()
            self.button_id = button_id

    def compose(self) -> ComposeResult:
        """Create button bar layout."""
        with Horizontal():
            # Pane toggles
            yield Button("Tasks", id="btn_tasks", variant="primary")
            yield Button("Agents", id="btn_agents", variant="primary")
            yield Static("│", classes="separator")

            # External launchers
            yield Button("Plan", id="btn_plan")
            yield Button("Git", id="btn_git")
            yield Button("Notes", id="btn_notes")
            yield Static("│", classes="separator")

            # URL launchers
            yield Button("API", id="btn_api")
            yield Button("Jira", id="btn_jira")
            yield Static("│", classes="separator")

            # Status actions
            yield Button("Server", id="btn_server")
            yield Button("Database", id="btn_database")
            yield Button("Build", id="btn_build")
            yield Button("Tests", id="btn_tests")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """
        Handle button press events.

        Args:
            event: Button press event
        """
        button_id = event.button.id
        if button_id:
            # Update active pane if it's a pane toggle button
            if button_id in ["btn_tasks", "btn_agents"]:
                self.active_pane = button_id.replace("btn_", "")
                self._update_button_variants()

            # Post message to parent
            self.post_message(self.ButtonClicked(button_id))

    def watch_active_pane(self, active_pane: str) -> None:
        """
        React to active pane changes.

        Args:
            active_pane: Name of the active pane
        """
        self._update_button_variants()

    def _update_button_variants(self) -> None:
        """Update button variants based on active pane."""
        # Get all buttons
        tasks_btn = self.query_one("#btn_tasks", Button)
        agents_btn = self.query_one("#btn_agents", Button)

        # Update variants
        if self.active_pane == "tasks":
            tasks_btn.variant = "primary"
            agents_btn.variant = "default"
        elif self.active_pane == "agents":
            tasks_btn.variant = "default"
            agents_btn.variant = "primary"
