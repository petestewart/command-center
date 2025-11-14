"""
Tests for Claude chat functionality (Phase 6)
"""

import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock

from ccc.claude_chat import (
    ClaudeChat,
    ChatMessage,
    ClaudeCLIError,
    ClaudeCLINotFoundError,
    create_chat,
)
from ccc.questions import QuestionManager, AgentQuestion
from ccc.plan_reviser import PlanReviser


class TestChatMessage:
    """Tests for ChatMessage dataclass"""

    def test_chat_message_creation(self):
        """Test creating a chat message"""
        msg = ChatMessage(role="user", content="Hello Claude")

        assert msg.role == "user"
        assert msg.content == "Hello Claude"
        assert isinstance(msg.timestamp, datetime)

    def test_chat_message_to_dict(self):
        """Test converting chat message to dict"""
        msg = ChatMessage(role="assistant", content="Hello!")
        data = msg.to_dict()

        assert data["role"] == "assistant"
        assert data["content"] == "Hello!"
        assert "timestamp" in data

    def test_chat_message_from_dict(self):
        """Test creating chat message from dict"""
        data = {
            "role": "user",
            "content": "Test message",
            "timestamp": "2025-01-01T12:00:00+00:00"
        }

        msg = ChatMessage.from_dict(data)

        assert msg.role == "user"
        assert msg.content == "Test message"
        assert isinstance(msg.timestamp, datetime)


class TestClaudeChat:
    """Tests for ClaudeChat class"""

    @pytest.fixture
    def temp_branch(self, tmp_path):
        """Create a temporary branch directory"""
        branch_name = "test-branch"
        branch_dir = tmp_path / ".ccc-control" / "test-branch"
        branch_dir.mkdir(parents=True)

        with patch("ccc.claude_chat.get_branch_dir", return_value=branch_dir):
            yield branch_name

    def test_chat_initialization(self, temp_branch):
        """Test initializing a chat instance"""
        chat = ClaudeChat(temp_branch)

        assert chat.branch_name == temp_branch
        assert chat.cli_path == "claude"
        assert chat.timeout == 30
        assert chat.messages == []

    @patch("subprocess.run")
    def test_verify_cli_success(self, mock_run, temp_branch):
        """Test CLI verification succeeds"""
        mock_run.return_value = Mock(returncode=0, stdout="claude 1.0.0", stderr="")

        chat = ClaudeChat(temp_branch)
        is_available, error = chat.verify_cli()

        assert is_available is True
        assert error is None

    @patch("subprocess.run")
    def test_verify_cli_not_found(self, mock_run, temp_branch):
        """Test CLI verification fails when CLI not found"""
        mock_run.side_effect = FileNotFoundError()

        chat = ClaudeChat(temp_branch)
        is_available, error = chat.verify_cli()

        assert is_available is False
        assert "not found" in error.lower()
        assert "npm install" in error

    @patch("subprocess.run")
    def test_verify_cli_not_authenticated(self, mock_run, temp_branch):
        """Test CLI verification fails when not authenticated"""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="not authenticated"
        )

        chat = ClaudeChat(temp_branch)
        is_available, error = chat.verify_cli()

        assert is_available is False
        assert "not authenticated" in error.lower()
        assert "claude login" in error

    def test_build_context(self, temp_branch):
        """Test building context from branch state"""
        with patch("ccc.claude_chat.TicketRegistry"), \
             patch("ccc.claude_chat.list_todos"), \
             patch("ccc.claude_chat.get_git_status"):

            chat = ClaudeChat(temp_branch)
            context = chat._build_context()

            assert isinstance(context, str)
            # Context should mention the branch
            assert temp_branch in context or "Branch:" in context


class TestQuestionManager:
    """Tests for QuestionManager class"""

    @pytest.fixture
    def temp_branch(self, tmp_path):
        """Create a temporary branch directory"""
        branch_name = "test-branch"
        branch_dir = tmp_path / ".ccc-control" / "test-branch"
        branch_dir.mkdir(parents=True)

        with patch("ccc.questions.get_branch_dir", return_value=branch_dir):
            yield branch_name

    def test_question_manager_initialization(self, temp_branch):
        """Test initializing question manager"""
        manager = QuestionManager(temp_branch)

        assert manager.branch_name == temp_branch
        assert manager.questions == []

    def test_post_question(self, temp_branch):
        """Test posting a new question"""
        manager = QuestionManager(temp_branch)

        question = manager.post_question(
            agent_id="agent-1",
            question="Should I use Zod or Joi?",
            context={"file": "src/main.py"}
        )

        assert question.agent_id == "agent-1"
        assert question.question == "Should I use Zod or Joi?"
        assert question.answered is False
        assert question.context["file"] == "src/main.py"
        assert len(manager.questions) == 1

    def test_answer_question(self, temp_branch):
        """Test answering a question"""
        manager = QuestionManager(temp_branch)

        # Post a question
        question = manager.post_question(
            agent_id="agent-1",
            question="Use Zod or Joi?"
        )

        # Answer it
        answered = manager.answer_question(question.id, "Use Zod for better types")

        assert answered is not None
        assert answered.answered is True
        assert answered.answer == "Use Zod for better types"
        assert answered.answer_timestamp is not None

    def test_get_unanswered(self, temp_branch):
        """Test getting unanswered questions"""
        manager = QuestionManager(temp_branch)

        # Post some questions
        q1 = manager.post_question("agent-1", "Question 1")
        q2 = manager.post_question("agent-1", "Question 2")
        q3 = manager.post_question("agent-1", "Question 3")

        # Answer one
        manager.answer_question(q2.id, "Answer 2")

        # Get unanswered
        unanswered = manager.get_unanswered()

        assert len(unanswered) == 2
        assert q1.id in [q.id for q in unanswered]
        assert q3.id in [q.id for q in unanswered]
        assert q2.id not in [q.id for q in unanswered]

    def test_dismiss_question(self, temp_branch):
        """Test dismissing a question"""
        manager = QuestionManager(temp_branch)

        # Post a question
        question = manager.post_question("agent-1", "Test question")

        # Dismiss it
        result = manager.dismiss_question(question.id)

        assert result is True
        assert len(manager.questions) == 0

    def test_clear_answered(self, temp_branch):
        """Test clearing answered questions"""
        manager = QuestionManager(temp_branch)

        # Post and answer some questions
        q1 = manager.post_question("agent-1", "Question 1")
        q2 = manager.post_question("agent-1", "Question 2")
        q3 = manager.post_question("agent-1", "Question 3")

        manager.answer_question(q1.id, "Answer 1")
        manager.answer_question(q2.id, "Answer 2")

        # Clear answered
        manager.clear_answered()

        # Only unanswered should remain
        assert len(manager.questions) == 1
        assert manager.questions[0].id == q3.id


class TestPlanReviser:
    """Tests for PlanReviser class"""

    @pytest.fixture
    def temp_branch(self, tmp_path):
        """Create a temporary branch directory"""
        branch_name = "test-branch"
        branch_dir = tmp_path / ".ccc-control" / "test-branch"
        branch_dir.mkdir(parents=True)

        with patch("ccc.plan_reviser.get_branch_dir", return_value=branch_dir), \
             patch("ccc.claude_chat.get_branch_dir", return_value=branch_dir):
            yield branch_name

    def test_plan_reviser_initialization(self, temp_branch):
        """Test initializing plan reviser"""
        reviser = PlanReviser(temp_branch)

        assert reviser.branch_name == temp_branch
        assert reviser.chat is not None

    @patch("ccc.claude_chat.ClaudeChat.send_message")
    @patch("ccc.plan_reviser.list_todos")
    def test_suggest_improvements(self, mock_list_todos, mock_send, temp_branch):
        """Test getting plan improvement suggestions"""
        # Mock todo list
        from ccc.todo import TodoList, TodoItem

        mock_todo_list = TodoList(temp_branch)
        mock_todo_list.items = [
            TodoItem(id=1, description="Task 1", status="not_started"),
            TodoItem(id=2, description="Task 2", status="in_progress"),
        ]
        mock_list_todos.return_value = mock_todo_list

        # Mock Claude response
        mock_send.return_value = (
            "1. Consider splitting task 2 into smaller pieces\n"
            "2. Add error handling to task 1",
            None
        )

        reviser = PlanReviser(temp_branch)
        suggestions, error = reviser.suggest_improvements()

        assert error is None
        assert len(suggestions) > 0
        assert any("split" in s.description.lower() for s in suggestions)

    @patch("ccc.claude_chat.ClaudeChat.send_message")
    def test_suggest_next_steps(self, mock_send, temp_branch):
        """Test getting next step suggestion"""
        mock_send.return_value = ("Work on task 1 first", None)

        reviser = PlanReviser(temp_branch)
        suggestion, error = reviser.suggest_next_steps()

        assert error is None
        assert "task 1" in suggestion.lower()
