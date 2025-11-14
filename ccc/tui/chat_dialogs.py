"""
Chat Dialogs - Dialog components for chat and question management

Provides modal dialogs for:
- Replying to agent questions
- Quick chat input
- Plan review actions
"""

from typing import Optional

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Static, Input, Button, Label, TextArea
from textual.binding import Binding

from ccc.questions import QuestionManager, AgentQuestion
from ccc.utils import format_time_ago


class ReplyToQuestionDialog(ModalScreen):
    """Dialog for replying to an agent question"""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, branch_name: str, question: AgentQuestion, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_name = branch_name
        self.question = question

    def compose(self) -> ComposeResult:
        """Build dialog"""
        with Container(id="dialog-container"):
            yield Static(f"[bold]Reply to Question from {self.question.agent_id}[/bold]\n")

            # Show the question
            yield Static(f"[yellow]Question ({format_time_ago(self.question.timestamp)}):[/yellow]")
            yield Static(f"{self.question.question}\n")

            # Context if available
            if self.question.context:
                context_parts = []
                if 'file' in self.question.context:
                    context_parts.append(f"File: {self.question.context['file']}")
                if 'line' in self.question.context:
                    context_parts.append(f"Line: {self.question.context['line']}")
                if context_parts:
                    yield Static(f"[dim]{', '.join(context_parts)}[/dim]\n")

            # Answer input
            yield Label("Your answer:")
            yield TextArea(id="answer-input")

            # Buttons
            with Horizontal(id="dialog-buttons"):
                yield Button("Submit", id="submit", variant="primary")
                yield Button("Cancel", id="cancel", variant="default")

    def on_mount(self):
        """Focus answer input on mount"""
        answer_input = self.query_one("#answer-input", TextArea)
        answer_input.focus()

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press"""
        if event.button.id == "submit":
            self.submit_answer()
        elif event.button.id == "cancel":
            self.action_cancel()

    def submit_answer(self):
        """Submit the answer"""
        answer_input = self.query_one("#answer-input", TextArea)
        answer = answer_input.text.strip()

        if not answer:
            self.app.notify("Answer cannot be empty", severity="warning")
            return

        # Save answer
        manager = QuestionManager(self.branch_name)
        manager.answer_question(self.question.id, answer)

        # Close dialog
        self.dismiss({
            "success": True,
            "question_id": self.question.id,
            "answer": answer
        })

    def action_cancel(self):
        """Cancel the dialog"""
        self.dismiss(None)


class QuickChatDialog(ModalScreen):
    """Quick chat dialog for sending a single message"""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, branch_name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_name = branch_name

    def compose(self) -> ComposeResult:
        """Build dialog"""
        with Container(id="dialog-container"):
            yield Static(f"[bold]Quick Chat: {self.branch_name}[/bold]\n")
            yield Label("Your message:")
            yield TextArea(id="message-input", language="markdown")
            yield Static("", id="status")

            with Horizontal(id="dialog-buttons"):
                yield Button("Send", id="send", variant="primary")
                yield Button("Cancel", id="cancel", variant="default")

    def on_mount(self):
        """Focus message input on mount"""
        message_input = self.query_one("#message-input", TextArea)
        message_input.focus()

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press"""
        if event.button.id == "send":
            self.send_message()
        elif event.button.id == "cancel":
            self.action_cancel()

    def send_message(self):
        """Send the message to Claude"""
        message_input = self.query_one("#message-input", TextArea)
        message = message_input.text.strip()

        if not message:
            self.app.notify("Message cannot be empty", severity="warning")
            return

        # Show loading
        status = self.query_one("#status", Static)
        status.update("[cyan]Sending...[/cyan]")

        # Disable buttons
        send_btn = self.query_one("#send", Button)
        send_btn.disabled = True

        # Send in background
        import threading

        def send():
            from ccc.claude_chat import create_chat

            chat = create_chat(self.branch_name)
            response, error = chat.send_message(message)

            self.call_from_thread(self._on_response, response, error)

        thread = threading.Thread(target=send, daemon=True)
        thread.start()

    def _on_response(self, response: Optional[str], error: Optional[str]):
        """Handle response"""
        if error:
            status = self.query_one("#status", Static)
            status.update(f"[red]Error: {error}[/red]")

            # Re-enable send button
            send_btn = self.query_one("#send", Button)
            send_btn.disabled = False
        else:
            # Success - close dialog and show response
            self.dismiss({
                "success": True,
                "response": response
            })

    def action_cancel(self):
        """Cancel the dialog"""
        self.dismiss(None)


class ViewQuestionDialog(ModalScreen):
    """Dialog for viewing a single question with full details"""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("r", "reply", "Reply"),
    ]

    def __init__(self, branch_name: str, question: AgentQuestion, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.branch_name = branch_name
        self.question = question

    def compose(self) -> ComposeResult:
        """Build dialog"""
        with Container(id="dialog-container"):
            yield Static(f"[bold]Question from {self.question.agent_id}[/bold]\n")

            # Question details
            yield Static(f"[dim]Asked: {format_time_ago(self.question.timestamp)}[/dim]")
            yield Static(f"[dim]ID: {self.question.id}[/dim]\n")

            # Context if available
            if self.question.context:
                yield Static("[yellow]Context:[/yellow]")
                for key, value in self.question.context.items():
                    yield Static(f"  {key}: {value}")
                yield Static("")

            # The question
            yield Static("[yellow]Question:[/yellow]")
            yield Static(f"{self.question.question}\n")

            # Answer if available
            if self.question.answered and self.question.answer:
                yield Static("[green]Your Answer:[/green]")
                yield Static(f"{self.question.answer}")
                if self.question.answer_timestamp:
                    yield Static(f"[dim]Answered: {format_time_ago(self.question.answer_timestamp)}[/dim]\n")

            # Buttons
            with Horizontal(id="dialog-buttons"):
                if not self.question.answered:
                    yield Button("Reply", id="reply", variant="primary")
                    yield Button("Dismiss", id="dismiss", variant="default")
                yield Button("Close", id="close", variant="primary")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press"""
        if event.button.id == "reply":
            self.action_reply()
        elif event.button.id == "dismiss":
            manager = QuestionManager(self.branch_name)
            manager.dismiss_question(self.question.id)
            self.dismiss({"dismissed": True})
        elif event.button.id == "close":
            self.action_close()

    def action_reply(self):
        """Open reply dialog"""
        self.dismiss({"reply": True, "question": self.question})

    def action_close(self):
        """Close the dialog"""
        self.dismiss(None)


class PlanSuggestionDetailDialog(ModalScreen):
    """Dialog showing detailed plan suggestion"""

    BINDINGS = [
        Binding("escape", "close", "Close"),
    ]

    def __init__(self, suggestion_number: int, suggestion, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.suggestion_number = suggestion_number
        self.suggestion = suggestion

    def compose(self) -> ComposeResult:
        """Build dialog"""
        with Container(id="dialog-container"):
            yield Static(f"[bold]Suggestion #{self.suggestion_number}[/bold]\n")

            yield Static(f"[cyan]Type:[/cyan] {self.suggestion.type}")
            yield Static(f"\n[yellow]Description:[/yellow]")
            yield Static(f"{self.suggestion.description}\n")

            if self.suggestion.task_ids:
                yield Static(f"[cyan]Affects tasks:[/cyan] {', '.join(f'#{tid}' for tid in self.suggestion.task_ids)}\n")

            if self.suggestion.details:
                yield Static(f"[yellow]Details:[/yellow]")
                yield Static(f"{self.suggestion.details}\n")

            with Horizontal(id="dialog-buttons"):
                yield Button("Close", id="close", variant="primary")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle button press"""
        if event.button.id == "close":
            self.action_close()

    def action_close(self):
        """Close the dialog"""
        self.dismiss(None)
