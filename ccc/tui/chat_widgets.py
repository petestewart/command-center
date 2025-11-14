"""
Question Widgets - TUI components for agent question handling

Provides interactive components for the Textual TUI, including:
- Question notifications
- Question list view
- Question response interface
"""

from typing import Optional, List

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll, Horizontal
from textual.widgets import Static, Button
from textual.reactive import reactive
from textual.message import Message

from ccc.questions import QuestionManager, AgentQuestion
from ccc.utils import format_time_ago


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
