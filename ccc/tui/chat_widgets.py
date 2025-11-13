"""
Chat Widgets - TUI components for Claude chat interface

Provides interactive chat components for the Textual TUI, including:
- Chat history display
- Message input
- Question notifications
- Plan review interface
"""

from typing import Optional, List
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll, Horizontal, Vertical
from textual.widgets import Static, Input, Button, Label
from textual.screen import Screen
from textual.binding import Binding
from textual.reactive import reactive
from textual.message import Message
from rich.text import Text
from rich.panel import Panel
from rich.markdown import Markdown

from ccc.claude_chat import ClaudeChat, create_chat, ChatMessage
from ccc.questions import QuestionManager, AgentQuestion
from ccc.utils import format_time_ago


class ChatHistory(VerticalScroll):
    """Displays chat message history"""

    branch_name: reactive[str] = reactive("")

    def __init__(self, branch_name: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_name = branch_name
        self.chat: Optional[ClaudeChat] = None

    def on_mount(self):
        """Load messages when mounted"""
        if self.branch_name and not self.chat:
            self.chat = create_chat(self.branch_name)
            self.refresh_messages()

    def watch_branch_name(self, branch_name: str):
        """Update when branch changes"""
        if branch_name and self.is_mounted:
            self.chat = create_chat(branch_name)
            self.refresh_messages()

    def refresh_messages(self):
        """Refresh the message display"""
        if not self.chat:
            self.update(Static("No chat loaded"))
            return

        # Reload history from disk to get latest messages
        self.chat._load_history()

        # Clear existing content
        self.remove_children()

        messages = self.chat.get_history()

        if not messages:
            self.mount(Static("[dim]No messages yet. Start a conversation![/dim]"))
            return

        # Display each message
        for msg in messages:
            self.mount(ChatMessageWidget(msg))

        # Auto-scroll to bottom
        self.scroll_end(animate=False)

        # Force a refresh of the widget
        self.refresh(layout=True)


class ChatMessageWidget(Static):
    """Widget for displaying a single chat message"""

    def __init__(self, message: ChatMessage, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.message = message

    def render(self) -> Text:
        """Render the message"""
        time_str = format_time_ago(self.message.timestamp)

        if self.message.role == "user":
            role_label = f"[bold cyan]You[/bold cyan] [dim]({time_str})[/dim]"
            message_style = "white"
        else:
            role_label = f"[bold green]Claude[/bold green] [dim]({time_str})[/dim]"
            message_style = "white"

        # Format message content
        content = self.message.content

        # Build display
        text = Text()
        text.append(role_label + "\n", style="")
        text.append(content, style=message_style)
        text.append("\n")

        return text


class QuestionNotificationBanner(Static):
    """Banner notification for unanswered agent questions"""

    branch_name: reactive[str] = reactive("")
    question_count: reactive[int] = reactive(0)

    def __init__(self, branch_name: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_name = branch_name
        self.update_count()

    def watch_branch_name(self, branch_name: str):
        """Update when branch changes"""
        self.update_count()

    def update_count(self):
        """Update the question count"""
        if not self.branch_name:
            self.question_count = 0
            return

        manager = QuestionManager(self.branch_name)
        unanswered = manager.get_unanswered()
        self.question_count = len(unanswered)

    def watch_question_count(self, count: int):
        """Update display when count changes"""
        if count == 0:
            self.display = False
            self.update("")
        else:
            self.display = True
            plural = "s" if count > 1 else ""
            self.update(
                f"[yellow]⚠ {count} unanswered question{plural} - Press 'r' to reply[/yellow]"
            )


class ChatView(Screen):
    """
    Complete chat interface view.

    Displays chat history and provides input for sending messages.
    """

    CSS = """
    ChatView {
        layout: vertical;
    }

    #chat-container {
        layout: vertical;
        height: 100%;
        width: 100%;
        border: solid $primary;
        padding: 1;
    }

    #chat-history {
        height: 1fr;
        border: solid $accent;
        padding: 1;
    }

    #chat-input-container {
        height: auto;
        margin-top: 1;
    }

    #chat-input {
        width: 1fr;
    }

    #send-button {
        width: auto;
    }

    #chat-status {
        height: auto;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def __init__(self, branch_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_name = branch_name
        self.chat = create_chat(branch_name)

    def compose(self) -> ComposeResult:
        """Build chat UI"""
        with Container(id="chat-container"):
            yield Static(f"[bold]Chat: {self.branch_name}[/bold]", id="chat-header")
            yield ChatHistory(self.branch_name, id="chat-history")
            with Horizontal(id="chat-input-container"):
                yield Input(placeholder="Type your message... (Shift+Enter to send)", id="chat-input")
                yield Button("Send", id="send-button", variant="primary")
            yield Static("", id="chat-status")

    def on_mount(self):
        """Focus input on mount"""
        # Verify CLI is available
        is_available, error = self.chat.verify_cli()
        if not is_available:
            status = self.query_one("#chat-status", Static)
            status.update(f"[red]❌ {error}[/red]")
            # Disable input
            input_widget = self.query_one("#chat-input", Input)
            input_widget.disabled = True
        else:
            input_widget = self.query_one("#chat-input", Input)
            input_widget.focus()

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press"""
        if event.button.id == "send-button":
            self.send_message()

    def on_input_submitted(self, event: Input.Submitted):
        """Handle input submission (Enter key)"""
        if event.input.id == "chat-input":
            self.send_message()

    def send_message(self):
        """Send user message to Claude"""
        input_widget = self.query_one("#chat-input", Input)
        message = input_widget.value.strip()

        if not message:
            return

        # Clear input immediately
        input_widget.value = ""

        # Add user message to history immediately
        history = self.query_one("#chat-history", ChatHistory)
        from ccc.claude_chat import ChatMessage
        from datetime import datetime, timezone
        user_msg = ChatMessage(role="user", content=message, timestamp=datetime.now(timezone.utc))

        # Temporarily add to display
        if history.chat:
            history.chat.messages.append(user_msg)
            history.refresh_messages()

        # Show loading status
        status = self.query_one("#chat-status", Static)
        status.update("[cyan]🤔 Claude is thinking...[/cyan]")

        # Send in background
        self._send_message_async(message)

    def _send_message_async(self, message: str):
        """Send message in background thread"""
        import threading

        def send():
            try:
                response, error = self.chat.send_message(message)
                self.call_from_thread(self._on_response, response, error)
            except Exception as e:
                self.call_from_thread(self._on_response, None, f"Exception: {str(e)}")

        thread = threading.Thread(target=send, daemon=True)
        thread.start()

    def _on_response(self, response: Optional[str], error: Optional[str]):
        """Handle Claude's response"""
        try:
            status = self.query_one("#chat-status", Static)
            history = self.query_one("#chat-history", ChatHistory)

            if error:
                status.update(f"[red]❌ Error: {error}[/red]")
                status.refresh()
                # Keep error visible longer (10 seconds)
                self.set_timer(10, lambda: status.update(""))
            else:
                status.update("[green]✓ Response received[/green]")
                status.refresh()
                history.refresh_messages()
                # Force screen refresh
                self.refresh()
                # Clear success status after 3 seconds
                self.set_timer(3, lambda: status.update(""))
        except Exception as e:
            # Log any errors in the callback
            self.app.notify(f"Error in _on_response: {str(e)}", severity="error")

    def action_close(self):
        """Close the chat view"""
        self.app.pop_screen()


class QuestionListView(VerticalScroll):
    """View for displaying and managing agent questions"""

    def __init__(self, branch_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_name = branch_name
        self.manager = QuestionManager(branch_name)
        self.border_title = f"Questions: {branch_name}"

    def compose(self) -> ComposeResult:
        """Build question list UI"""
        unanswered = self.manager.get_unanswered()

        if not unanswered:
            yield Static("[dim]No unanswered questions[/dim]")
            return

        for question in unanswered:
            yield QuestionWidget(question, self.branch_name)

    def refresh_questions(self):
        """Refresh the question list"""
        # Reload manager
        self.manager = QuestionManager(self.branch_name)

        # Clear and rebuild
        self.remove_children()

        unanswered = self.manager.get_unanswered()

        if not unanswered:
            self.mount(Static("[dim]No unanswered questions[/dim]"))
        else:
            for question in unanswered:
                self.mount(QuestionWidget(question, self.branch_name))


class QuestionWidget(Container):
    """Widget for displaying a single agent question"""

    def __init__(self, question: AgentQuestion, branch_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question
        self.branch_name = branch_name
        self.border_title = f"Question from {question.agent_id}"

    def compose(self) -> ComposeResult:
        """Build question UI"""
        time_str = format_time_ago(self.question.timestamp)

        yield Static(f"[dim]{time_str}[/dim]")
        yield Static(f"\n{self.question.question}\n")

        # Context if available
        if self.question.context:
            context_parts = []
            if 'file' in self.question.context:
                context_parts.append(f"File: {self.question.context['file']}")
            if 'line' in self.question.context:
                context_parts.append(f"Line: {self.question.context['line']}")
            if context_parts:
                yield Static(f"[dim]{', '.join(context_parts)}[/dim]\n")

        # Action buttons
        with Horizontal():
            yield Button("Reply", id=f"reply-{self.question.id}", variant="primary")
            yield Button("Dismiss", id=f"dismiss-{self.question.id}", variant="default")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press"""
        question_id = self.question.id

        if event.button.id == f"reply-{question_id}":
            # Trigger reply dialog
            self.post_message(self.ReplyRequest(question_id))
        elif event.button.id == f"dismiss-{question_id}":
            # Dismiss the question
            manager = QuestionManager(self.branch_name)
            manager.dismiss_question(question_id)
            self.remove()
            self.app.notify(f"Question dismissed", severity="information")

    class ReplyRequest(Message):
        """Message to request reply dialog"""
        def __init__(self, question_id: str):
            super().__init__()
            self.question_id = question_id


class PlanReviewView(Screen):
    """View for displaying plan review suggestions from Claude"""

    CSS = """
    PlanReviewView {
        layout: vertical;
    }

    #review-container {
        layout: vertical;
        height: 100%;
        width: 100%;
        border: solid $primary;
        padding: 1;
    }

    #review-header {
        height: auto;
        margin-bottom: 1;
    }

    #review-status {
        height: auto;
        margin-bottom: 1;
    }

    #suggestions-container {
        height: 1fr;
        border: solid $accent;
        padding: 1;
    }

    #review-actions {
        height: auto;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def __init__(self, branch_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_name = branch_name

    def compose(self) -> ComposeResult:
        """Build review UI"""
        with Container(id="review-container"):
            yield Static(f"[bold]Plan Review: {self.branch_name}[/bold]", id="review-header")
            yield Static("[cyan]Requesting plan review from Claude...[/cyan]", id="review-status")
            yield VerticalScroll(id="suggestions-container")
            with Horizontal(id="review-actions"):
                yield Button("Refresh", id="refresh-review", variant="default")
                yield Button("Close", id="close-review", variant="primary")

    def on_mount(self):
        """Load suggestions on mount"""
        self.load_suggestions()

    def load_suggestions(self):
        """Load plan suggestions from Claude"""
        import threading

        def get_suggestions():
            from ccc.plan_reviser import get_plan_reviser

            reviser = get_plan_reviser(self.branch_name)
            suggestions, error = reviser.suggest_improvements()

            self.call_from_thread(self._on_suggestions_loaded, suggestions, error)

        thread = threading.Thread(target=get_suggestions, daemon=True)
        thread.start()

    def _on_suggestions_loaded(self, suggestions, error):
        """Handle loaded suggestions"""
        status = self.query_one("#review-status", Static)
        container = self.query_one("#suggestions-container", VerticalScroll)

        # Clear container
        container.remove_children()

        if error:
            status.update(f"[red]❌ Error: {error}[/red]")
            return

        if not suggestions:
            status.update("[yellow]No suggestions available[/yellow]")
            container.mount(Static("[dim]Claude didn't provide any suggestions.[/dim]"))
            return

        status.update(f"[green]✓ Received {len(suggestions)} suggestion(s)[/green]")

        # Display suggestions
        for i, suggestion in enumerate(suggestions, 1):
            container.mount(SuggestionWidget(i, suggestion))

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press"""
        if event.button.id == "refresh-review":
            status = self.query_one("#review-status", Static)
            status.update("[cyan]Refreshing...[/cyan]")
            self.load_suggestions()
        elif event.button.id == "close-review":
            self.action_close()

    def action_close(self):
        """Close the review view"""
        self.app.pop_screen()


class SuggestionWidget(Container):
    """Widget for displaying a single plan suggestion"""

    def __init__(self, number: int, suggestion, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.number = number
        self.suggestion = suggestion

    def compose(self) -> ComposeResult:
        """Build suggestion UI"""
        yield Static(f"[bold cyan]{self.number}.[/bold cyan] {self.suggestion.description}")

        if self.suggestion.details:
            yield Static(f"[dim]{self.suggestion.details}[/dim]")
