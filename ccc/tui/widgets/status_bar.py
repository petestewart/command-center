"""
Status bar widget for Command Center TUI.
"""

from textual.widgets import Static
from textual.reactive import reactive


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
