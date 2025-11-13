"""
API Testing TUI widgets for Command Center.

Provides interactive dialogs and panels for API testing functionality.
"""

from typing import Optional, List, Dict
from pathlib import Path
from textual.app import ComposeResult
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static, Button, Label, Input, Select, TextArea, LoadingIndicator
from textual.binding import Binding
from textual import work

from ccc.api_request import ApiRequest, ApiResponse, HttpMethod, VariableStore
from ccc.api_testing import (
    load_requests,
    add_request,
    update_request,
    execute_request,
    delete_request,
    load_history,
)


class RequestBuilderDialog(ModalScreen):
    """
    Dialog for creating/editing API requests.

    Allows users to configure all aspects of an HTTP request including
    method, URL, headers, body, and expected status code.
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Cancel", show=False),
        Binding("ctrl+s", "save", "Save", show=True),
        Binding("ctrl+t", "test", "Test Now", show=True),
    ]

    CSS = """
    RequestBuilderDialog {
        align: center middle;
    }

    RequestBuilderDialog > Container {
        width: 90;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
        layout: vertical;
    }

    RequestBuilderDialog .form-content {
        width: 100%;
        height: 1fr;
        overflow: auto;
    }

    RequestBuilderDialog .dialog-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    RequestBuilderDialog Label {
        margin-top: 1;
        margin-bottom: 0;
    }

    RequestBuilderDialog Input {
        width: 100%;
        margin-bottom: 1;
    }

    RequestBuilderDialog Select {
        width: 20;
        margin-bottom: 1;
    }

    RequestBuilderDialog TextArea {
        width: 100%;
        height: 6;
        border: solid $primary-lighten-1;
        margin-bottom: 1;
    }

    RequestBuilderDialog .dialog-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        margin-top: 1;
        border-top: solid $primary-lighten-1;
        padding-top: 1;
    }

    RequestBuilderDialog Button {
        margin: 0 1;
    }

    RequestBuilderDialog .header-row {
        layout: horizontal;
        width: 100%;
        height: auto;
        margin-bottom: 0;
    }

    RequestBuilderDialog .header-key {
        width: 1fr;
        margin-right: 1;
    }

    RequestBuilderDialog .header-value {
        width: 2fr;
    }
    """

    def __init__(
        self,
        branch_name: str,
        request: Optional[ApiRequest] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the request builder dialog.

        Args:
            branch_name: Branch name
            request: Existing request to edit (None for new request)
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(name=name, id=id, classes=classes)
        self.branch_name = branch_name
        self.request = request
        self.is_edit = request is not None

    def compose(self) -> ComposeResult:
        """Create child widgets for the dialog."""
        with Container():
            title = "Edit API Request" if self.is_edit else "New API Request"
            yield Label(title, classes="dialog-title")

            with VerticalScroll(classes="form-content"):
                yield Label("Name:")
                name_input = Input(
                    placeholder="Request name",
                    value=self.request.name if self.request else "",
                    id="name-input"
                )
                name_input.disabled = self.is_edit  # Can't rename existing requests
                yield name_input

                yield Label("Method:")
                method_options = [(m.value, m.value) for m in HttpMethod]
                initial_method = self.request.method.value if self.request else "GET"
                yield Select(
                    method_options,
                    value=initial_method,
                    id="method-select"
                )

                yield Label("URL:")
                yield Input(
                    placeholder="https://api.example.com/endpoint or {{base_url}}/api/users",
                    value=self.request.url if self.request else "",
                    id="url-input"
                )

                yield Label("Headers (one per line, format: Key: Value):")
                headers_text = ""
                if self.request and self.request.headers:
                    headers_text = "\n".join(f"{k}: {v}" for k, v in self.request.headers.items())
                headers_area = TextArea(id="headers-input")
                headers_area.text = headers_text
                headers_area.show_line_numbers = False
                yield headers_area

                yield Label("Body (JSON, text, etc.):")
                body_area = TextArea(id="body-input")
                body_area.text = self.request.body if self.request and self.request.body else ""
                body_area.show_line_numbers = False
                yield body_area

                yield Label("Expected Status (optional):")
                yield Input(
                    placeholder="200",
                    value=str(self.request.expected_status) if self.request and self.request.expected_status else "",
                    id="expected-status-input"
                )

            with Horizontal(classes="dialog-buttons"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Test Now", variant="success", id="test-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            self._do_save()
        elif event.button.id == "test-btn":
            self._do_test()
        elif event.button.id == "cancel-btn":
            self.dismiss(None)

    def action_save(self) -> None:
        """Handle Ctrl+S key press."""
        self._do_save()

    def action_test(self) -> None:
        """Handle Ctrl+T key press."""
        self._do_test()

    def action_dismiss(self) -> None:
        """Handle escape key press."""
        self.dismiss(None)

    def _do_save(self) -> None:
        """Save the request."""
        # Gather inputs
        name = self.query_one("#name-input", Input).value.strip()
        method_str = self.query_one("#method-select", Select).value
        url = self.query_one("#url-input", Input).value.strip()
        headers_text = self.query_one("#headers-input", TextArea).text
        body = self.query_one("#body-input", TextArea).text.strip()
        expected_status_str = self.query_one("#expected-status-input", Input).value.strip()

        # Validate
        if not name:
            self.app.notify("Name is required", severity="error")
            return

        if not url:
            self.app.notify("URL is required", severity="error")
            return

        # Parse headers
        headers_dict = {}
        if headers_text.strip():
            for line in headers_text.strip().split("\n"):
                if ": " in line:
                    key, value = line.split(": ", 1)
                    headers_dict[key.strip()] = value.strip()

        # Parse expected status
        expected_status = None
        if expected_status_str:
            try:
                expected_status = int(expected_status_str)
            except ValueError:
                self.app.notify("Expected status must be a number", severity="error")
                return

        # Create or update request
        request = ApiRequest(
            name=name,
            method=HttpMethod.from_string(method_str),
            url=url,
            headers=headers_dict,
            body=body if body else None,
            expected_status=expected_status,
        )

        if self.is_edit:
            if update_request(self.branch_name, request):
                self.dismiss({"success": True, "message": f"Updated request '{name}'"})
            else:
                self.app.notify("Failed to update request", severity="error")
        else:
            if add_request(self.branch_name, request):
                self.dismiss({"success": True, "message": f"Created request '{name}'"})
            else:
                self.app.notify(f"Request '{name}' already exists", severity="error")

    def _do_test(self) -> None:
        """Test the request (save first if new)."""
        # For now, just save - testing will be implemented with ResponseViewerDialog
        self._do_save()


class ResponseViewerDialog(ModalScreen):
    """
    Dialog for displaying API response.

    Shows status code, headers (collapsed by default), body (expanded by default), and assertion results.
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("r", "rerun", "Re-run", show=True),
        Binding("h", "toggle_headers", "Toggle Headers", show=True),
        Binding("b", "toggle_body", "Toggle Body", show=True),
    ]

    CSS = """
    ResponseViewerDialog {
        align: center middle;
    }

    ResponseViewerDialog > Container {
        width: 90;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $primary;
        padding: 1 2;
        layout: vertical;
    }

    ResponseViewerDialog .form-content {
        width: 100%;
        height: 1fr;
        overflow: auto;
    }

    ResponseViewerDialog .dialog-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    ResponseViewerDialog .status-line {
        width: 100%;
        text-style: bold;
        margin-bottom: 1;
    }

    ResponseViewerDialog .section-header {
        width: 100%;
        margin-top: 1;
        margin-bottom: 0;
        height: 1;
        padding: 0;
        border: none;
        background: transparent;
        text-align: left;
    }

    ResponseViewerDialog .section-header:hover {
        background: $boost;
        text-style: bold underline;
    }

    ResponseViewerDialog .section-header:focus {
        background: $accent 20%;
        border: none;
        text-style: bold;
    }

    ResponseViewerDialog .section-content {
        width: 100%;
        height: 20;
        border: solid $primary-lighten-1;
        padding: 1;
        margin-bottom: 1;
        overflow: auto;
    }

    ResponseViewerDialog .collapsed {
        display: none;
    }

    ResponseViewerDialog .dialog-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        border-top: solid $primary-lighten-1;
        padding-top: 1;
    }

    ResponseViewerDialog Button {
        margin: 0 1;
    }
    """

    def __init__(
        self,
        request_name: str,
        response: ApiResponse,
        expected_status: Optional[int] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        """
        Initialize the response viewer dialog.

        Args:
            request_name: Name of the request
            response: ApiResponse to display
            expected_status: Expected status code (for assertion display)
            name: The name of the dialog
            id: The ID of the dialog in the DOM
            classes: The CSS classes for the dialog
        """
        super().__init__(name=name, id=id, classes=classes)
        self.request_name = request_name
        self.response = response
        self.expected_status = expected_status
        self.headers_expanded = False  # Collapsed by default
        self.body_expanded = True      # Expanded by default

    def compose(self) -> ComposeResult:
        """Create child widgets for the dialog."""
        with Container():
            yield Label(f"Response: {self.request_name}", classes="dialog-title")

            with VerticalScroll(classes="form-content"):
                # Status line
                status_color = self.response.status_color()
                status_symbol = self.response.status_symbol()
                status_text = f"[{status_color}]{status_symbol} {self.response.status_code} {self.response.reason}[/]     Time: {self.response.elapsed_ms:.0f}ms"
                yield Static(status_text, classes="status-line")

                # Assertion result
                if self.expected_status is not None:
                    if self.response.matches_expected(self.expected_status):
                        yield Static(f"[green]✓ Status matches expected ({self.expected_status})[/green]")
                    else:
                        yield Static(f"[red]✗ Status does not match expected ({self.expected_status})[/red]")

                # Headers (collapsed by default)
                headers_indicator = "▼ Headers" if self.headers_expanded else "▶ Headers"
                yield Button(headers_indicator, id="headers-toggle", classes="section-header", variant="default")
                headers_scroll = VerticalScroll(id="headers-content", classes="section-content")
                if not self.headers_expanded:
                    headers_scroll.styles.display = "none"
                with headers_scroll:
                    headers_text = "\n".join(f"{k}: {v}" for k, v in self.response.headers.items())
                    # Use Static without markup by escaping [ and ] characters
                    escaped_headers = headers_text.replace("[", "\\[").replace("]", "\\]")
                    headers_widget = Static(escaped_headers)
                    yield headers_widget

                # Body (expanded by default)
                body_indicator = "▼ Body" if self.body_expanded else "▶ Body"
                yield Button(body_indicator, id="body-toggle", classes="section-header", variant="default")
                body_scroll = VerticalScroll(id="body-content", classes="section-content")
                if not self.body_expanded:
                    body_scroll.styles.display = "none"
                with body_scroll:
                    body_text = self.response.get_formatted_body()
                    # Use Static without markup by escaping [ and ] characters
                    escaped_body = body_text.replace("[", "\\[").replace("]", "\\]")
                    body_widget = Static(escaped_body)
                    yield body_widget

            with Horizontal(classes="dialog-buttons"):
                yield Button("Close", variant="default", id="close-btn")
                yield Button("Re-run", variant="primary", id="rerun-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close-btn":
            self.dismiss(None)
        elif event.button.id == "rerun-btn":
            self.dismiss({"action": "rerun"})
        elif event.button.id == "headers-toggle":
            event.stop()
            self.action_toggle_headers()
        elif event.button.id == "body-toggle":
            event.stop()
            self.action_toggle_body()

    def on_key(self, event) -> None:
        """Handle key presses for toggling sections."""
        # Allow Enter to toggle focused headers when they have focus
        if event.key == "enter":
            focused = self.focused
            if focused and hasattr(focused, 'id'):
                if focused.id == "headers-toggle":
                    event.prevent_default()
                    self.action_toggle_headers()
                    return
                elif focused.id == "body-toggle":
                    event.prevent_default()
                    self.action_toggle_body()
                    return

    def action_dismiss(self) -> None:
        """Handle enter/escape key press."""
        self.dismiss(None)

    def action_rerun(self) -> None:
        """Handle 'r' key press."""
        self.dismiss({"action": "rerun"})

    def action_toggle_headers(self) -> None:
        """Toggle headers section visibility."""
        self.headers_expanded = not self.headers_expanded
        try:
            headers_content = self.query_one("#headers-content", VerticalScroll)
            headers_toggle = self.query_one("#headers-toggle", Button)

            if self.headers_expanded:
                headers_content.styles.display = "block"
                headers_toggle.label = "▼ Headers"
            else:
                headers_content.styles.display = "none"
                headers_toggle.label = "▶ Headers"
        except Exception as e:
            # Silently fail - the dialog will still be usable
            pass

    def action_toggle_body(self) -> None:
        """Toggle body section visibility."""
        self.body_expanded = not self.body_expanded
        try:
            body_content = self.query_one("#body-content", VerticalScroll)
            body_toggle = self.query_one("#body-toggle", Button)

            if self.body_expanded:
                body_content.styles.display = "block"
                body_toggle.label = "▼ Body"
            else:
                body_content.styles.display = "none"
                body_toggle.label = "▶ Body"
        except Exception as e:
            # Silently fail - the dialog will still be usable
            pass


class ApiRequestListPanel(Static):
    """
    Panel displaying saved API requests for current branch.

    Shows request name, method, URL, last status, and last run time.
    """

    BINDINGS = [
        Binding("enter", "execute", "Execute", show=True),
        Binding("n", "new", "New", show=True),
        Binding("e", "edit", "Edit", show=True),
        Binding("d", "delete", "Delete", show=True),
        Binding("up", "move_up", "Up", show=False),
        Binding("down", "move_down", "Down", show=False),
        Binding("j", "move_down", "Down", show=False),
        Binding("k", "move_up", "Up", show=False),
    ]

    CSS = """
    ApiRequestListPanel {
        width: 100%;
        height: auto;
        max-height: 10;
        border: solid $accent;
        padding: 1;
        background: $surface;
    }

    ApiRequestListPanel .no-requests {
        color: $text-muted;
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
        Initialize the API request list panel.

        Args:
            branch_name: Branch name
            name: The name of the widget
            id: The ID of the widget in the DOM
            classes: The CSS classes for the widget
        """
        super().__init__(name=name, id=id, classes=classes)
        self.branch_name = branch_name
        self.requests: List[ApiRequest] = []
        self.variables: VariableStore = VariableStore()
        self._focused_index = 0
        self.can_focus = True
        self.border_title = "API Requests"

    def on_mount(self) -> None:
        """Handle mount event."""
        self.refresh_requests()

    def refresh_requests(self) -> None:
        """Reload requests from storage."""
        self.requests, self.variables = load_requests(self.branch_name)
        self._focused_index = min(self._focused_index, max(0, len(self.requests) - 1))
        self.refresh()

    def render(self) -> str:
        """Render the request list."""
        if not self.requests:
            return "[dim]No API requests. Press 'n' to create one.[/dim]"

        lines = []
        for idx, req in enumerate(self.requests):
            is_focused = idx == self._focused_index

            # Get last execution info from history
            history = load_history(self.branch_name, limit=50)
            last_exec = next((h for h in history if h.request_name == req.name), None)

            status_indicator = ""
            if last_exec and last_exec.response:
                color = last_exec.response.status_color()
                status_indicator = f"[{color}]{last_exec.response.status_code}[/]"
            else:
                status_indicator = "[dim]-[/dim]"

            # Format line
            method = f"[blue]{req.method.value:6s}[/]"
            name = req.name[:25]
            url = req.url[:30] + "..." if len(req.url) > 30 else req.url
            last_run = ""
            if req.last_executed:
                from ccc.utils import format_time_ago
                last_run = format_time_ago(req.last_executed)
            else:
                last_run = "Never"

            line = f"{method}  {name:25s}  {status_indicator:5s}  {last_run}"

            if is_focused:
                lines.append(f"[reverse]{line}[/reverse]")
            else:
                lines.append(line)

        # Add help text footer
        help_text = "[dim]Press Enter to execute • j/k to navigate • n to create • e to edit • d to delete[/dim]"
        lines.append("")
        lines.append(help_text)

        return "\n".join(lines)

    def action_execute(self) -> None:
        """Execute the selected request."""
        if self._focused_index < len(self.requests):
            request = self.requests[self._focused_index]
            self._execute_request(request)

    def action_new(self) -> None:
        """Open dialog to create new request."""
        self.app.push_screen(
            RequestBuilderDialog(self.branch_name),
            self._on_request_saved
        )

    def action_edit(self) -> None:
        """Edit the selected request."""
        if self._focused_index < len(self.requests):
            request = self.requests[self._focused_index]
            self.app.push_screen(
                RequestBuilderDialog(self.branch_name, request),
                self._on_request_saved
            )

    def action_delete(self) -> None:
        """Delete the selected request."""
        if self._focused_index < len(self.requests):
            request = self.requests[self._focused_index]
            from ccc.tui.dialogs import ConfirmDialog

            def on_confirm(confirmed: bool):
                if confirmed and delete_request(self.branch_name, request.name):
                    self.app.notify(f"Deleted request '{request.name}'", severity="information")
                    self.refresh_requests()

            self.app.push_screen(
                ConfirmDialog(
                    "Delete Request",
                    f"Delete API request '{request.name}'?"
                ),
                on_confirm
            )

    def action_move_up(self) -> None:
        """Move focus up."""
        if self._focused_index > 0:
            self._focused_index -= 1
            self.refresh()

    def action_move_down(self) -> None:
        """Move focus down."""
        if self._focused_index < len(self.requests) - 1:
            self._focused_index += 1
            self.refresh()

    def _execute_request(self, request: ApiRequest) -> None:
        """Execute a request and show response."""
        self.app.notify(f"Executing {request.name}...", severity="information")

        # Execute in background
        import threading

        def do_execute():
            response, error = execute_request(request, self.variables)
            self.app.call_from_thread(self._on_execute_complete, request, response, error)

        thread = threading.Thread(target=do_execute, daemon=True)
        thread.start()

    def _on_execute_complete(self, request: ApiRequest, response: Optional[ApiResponse], error: Optional[str]) -> None:
        """Handle request execution completion."""
        if error:
            from ccc.tui.dialogs import ErrorDialog
            self.app.push_screen(ErrorDialog("Request Failed", error))
        elif response:
            # Update the last_executed timestamp
            request.update_last_executed()
            update_request(self.branch_name, request)

            def on_response_action(result):
                if result and result.get("action") == "rerun":
                    self._execute_request(request)

            self.app.push_screen(
                ResponseViewerDialog(request.name, response, request.expected_status),
                on_response_action
            )
            self.refresh_requests()

    def _on_request_saved(self, result) -> None:
        """Handle request save completion."""
        if result and result.get("success"):
            self.app.notify(result.get("message", "Request saved"), severity="information")
            self.refresh_requests()
