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
        height: 8;
        border: solid $primary-lighten-1;
        margin-bottom: 1;
    }

    RequestBuilderDialog .dialog-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        margin-top: 1;
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

    Shows status code, headers, body, and assertion results.
    """

    BINDINGS = [
        Binding("escape", "dismiss", "Close", show=False),
        Binding("enter", "dismiss", "Close", show=False),
        Binding("r", "rerun", "Re-run", show=True),
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

    ResponseViewerDialog .section-title {
        width: 100%;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 0;
    }

    ResponseViewerDialog VerticalScroll {
        width: 100%;
        height: 30;
        border: solid $primary-lighten-1;
        padding: 1;
        margin-bottom: 1;
    }

    ResponseViewerDialog .dialog-buttons {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
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

    def compose(self) -> ComposeResult:
        """Create child widgets for the dialog."""
        with Container():
            yield Label(f"Response: {self.request_name}", classes="dialog-title")

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

            # Headers
            yield Label("Headers:", classes="section-title")
            with VerticalScroll():
                headers_text = "\n".join(f"{k}: {v}" for k, v in self.response.headers.items())
                yield Static(headers_text)

            # Body
            yield Label("Body:", classes="section-title")
            with VerticalScroll():
                yield Static(self.response.get_formatted_body())

            with Horizontal(classes="dialog-buttons"):
                yield Button("Close", variant="default", id="close-btn")
                yield Button("Re-run", variant="primary", id="rerun-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "close-btn":
            self.dismiss(None)
        elif event.button.id == "rerun-btn":
            self.dismiss({"action": "rerun"})

    def action_dismiss(self) -> None:
        """Handle enter/escape key press."""
        self.dismiss(None)

    def action_rerun(self) -> None:
        """Handle 'r' key press."""
        self.dismiss({"action": "rerun"})


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
