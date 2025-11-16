"""
Comprehensive tests for Multi-Agent Manager and TODO parsing.

Tests all supported TODO formats and edge cases to ensure reliability.
"""

import pytest
from ccc.multi_agent_manager import TodoParser, MultiAgentManager
from ccc.status import AgentSession, AgentTodo


class TestTodoParser:
    """Test suite for TodoParser with all supported formats."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = TodoParser()

    # ========================================================================
    # Test Completed Formats
    # ========================================================================

    def test_checkmark_completed(self):
        """Test ✓ Task format for completed items."""
        text = "✓ Task completed"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task completed"
        assert todos[0].completed is True
        assert todos[0].blocked is False

    def test_green_checkmark_completed(self):
        """Test ✅ Task format for completed items."""
        text = "✅ Task completed"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task completed"
        assert todos[0].completed is True

    def test_bracket_x_completed(self):
        """Test [x] Task format for completed items."""
        text = "[x] Task completed"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task completed"
        assert todos[0].completed is True

    def test_bracket_X_uppercase_completed(self):
        """Test [X] Task format (uppercase) for completed items."""
        text = "[X] Task completed"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task completed"
        assert todos[0].completed is True

    def test_asterisk_bracket_x_completed(self):
        """Test * [x] Task format for completed items."""
        text = "* [x] Task completed"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task completed"
        assert todos[0].completed is True

    def test_dash_bracket_x_completed(self):
        """Test - [x] Task format for completed items."""
        text = "- [x] Task completed"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task completed"
        assert todos[0].completed is True

    # ========================================================================
    # Test Pending Formats
    # ========================================================================

    def test_dash_pending(self):
        """Test - Task format for pending items."""
        text = "- Task pending"
        todos = self.parser.parse_todo_list(text)
        # Note: This might match the fallback pattern
        assert len(todos) >= 1
        if len(todos) > 0:
            assert todos[0].text == "Task pending"
            assert todos[0].completed is False

    def test_circle_pending(self):
        """Test ○ Task format for pending items."""
        text = "○ Task pending"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task pending"
        assert todos[0].completed is False

    def test_dotted_circle_pending(self):
        """Test ⚬ Task format for pending items."""
        text = "⚬ Task pending"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task pending"
        assert todos[0].completed is False

    def test_bracket_space_pending(self):
        """Test [ ] Task format for pending items."""
        text = "[ ] Task pending"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task pending"
        assert todos[0].completed is False

    def test_asterisk_bracket_space_pending(self):
        """Test * [ ] Task format for pending items."""
        text = "* [ ] Task pending"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task pending"
        assert todos[0].completed is False

    def test_dash_bracket_space_pending(self):
        """Test - [ ] Task format for pending items."""
        text = "- [ ] Task pending"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task pending"
        assert todos[0].completed is False

    def test_plain_asterisk_pending(self):
        """Test * Task format for pending items."""
        text = "* Task pending"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) >= 1
        # Might match fallback pattern
        if len(todos) > 0:
            assert "Task pending" in todos[0].text or todos[0].text == "Task pending"

    # ========================================================================
    # Test Blocked Formats
    # ========================================================================

    def test_x_mark_blocked(self):
        """Test ✗ Task format for blocked items."""
        text = "✗ Task blocked"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task blocked"
        assert todos[0].completed is False
        assert todos[0].blocked is True

    def test_red_x_blocked(self):
        """Test ❌ Task format for blocked items."""
        text = "❌ Task blocked"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == "Task blocked"
        assert todos[0].completed is False
        assert todos[0].blocked is True

    # ========================================================================
    # Test Multiple TODOs
    # ========================================================================

    def test_multiple_todos_mixed_formats(self):
        """Test parsing multiple TODOs with mixed formats."""
        text = """
✓ Completed task
[ ] Pending task
✗ Blocked task
[x] Another completed
○ Another pending
"""
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 5

        # Check first completed
        assert todos[0].completed is True
        assert todos[0].text == "Completed task"

        # Check pending
        assert todos[1].completed is False
        assert todos[1].text == "Pending task"

        # Check blocked
        assert todos[2].blocked is True
        assert todos[2].text == "Blocked task"

    # ========================================================================
    # Test Edge Cases
    # ========================================================================

    def test_empty_string(self):
        """Test parsing empty string returns empty list."""
        todos = self.parser.parse_todo_list("")
        assert todos == []

    def test_none_string(self):
        """Test parsing None returns empty list."""
        todos = self.parser.parse_todo_list(None)
        assert todos == []

    def test_whitespace_only(self):
        """Test parsing whitespace-only string returns empty list."""
        text = "   \n\n   \t   "
        todos = self.parser.parse_todo_list(text)
        assert todos == []

    def test_no_todos(self):
        """Test text with no TODOs returns empty list."""
        text = """
This is just some regular text.
No TODOs here.
Just documentation.
"""
        todos = self.parser.parse_todo_list(text)
        assert todos == []

    def test_malformed_checkboxes(self):
        """Test malformed checkbox formats are handled gracefully."""
        text = """
[  ] Too many spaces
[]No space
[ x] Space before x
[x ] Space after x
"""
        # Should not crash, might not match any patterns
        todos = self.parser.parse_todo_list(text)
        # No assertion on count - just ensure no crash

    def test_very_short_text(self):
        """Test very short text is filtered out."""
        text = "✓ AB"  # Only 2 characters
        todos = self.parser.parse_todo_list(text)
        # Should be filtered out for being too short
        assert len(todos) == 0

    def test_long_todo_text(self):
        """Test long TODO text is preserved."""
        long_text = "This is a very long TODO item that contains many words and should be preserved completely without truncation"
        text = f"✓ {long_text}"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert todos[0].text == long_text

    # ========================================================================
    # Test TODO Section Extraction
    # ========================================================================

    def test_todo_section_with_header(self):
        """Test extraction of TODO section with header."""
        text = """
Some introduction text here.

## TODO

✓ First task
[ ] Second task

## Next Section

Some other content.
"""
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 2
        assert todos[0].text == "First task"
        assert todos[1].text == "Second task"

    def test_tasks_header(self):
        """Test extraction with 'Tasks' header."""
        text = """
Introduction.

### Tasks

✓ Task 1
[ ] Task 2
"""
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 2

    def test_plan_header(self):
        """Test extraction with 'Plan' header."""
        text = """
Introduction.

Plan:
✓ Step 1
[ ] Step 2
"""
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 2

    def test_no_section_header(self):
        """Test parsing when no TODO header present."""
        text = """
✓ Task 1
[ ] Task 2
"""
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 2

    # ========================================================================
    # Test Special Characters
    # ========================================================================

    def test_special_characters_in_text(self):
        """Test TODOs with special characters."""
        text = "✓ Task with #hashtag and @mention and $variable"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert "#hashtag" in todos[0].text

    def test_unicode_in_text(self):
        """Test TODOs with unicode characters."""
        text = "✓ Task with émojis 🎉 and spëcial çharacters"
        todos = self.parser.parse_todo_list(text)
        assert len(todos) == 1
        assert "émojis" in todos[0].text


class TestMultiAgentManager:
    """Test suite for MultiAgentManager."""

    def test_calculate_progress_empty(self):
        """Test progress calculation with no TODOs."""
        from ccc.status import AgentSession

        session = AgentSession(
            id="test",
            todo_id=None,
            title="Test",
            status="working",
            todo_list=[],
        )

        manager = MultiAgentManager("test-branch")
        progress = manager.calculate_progress(session)
        assert progress is None

    def test_calculate_progress_all_pending(self):
        """Test progress calculation with all pending TODOs."""
        from ccc.status import AgentSession, AgentTodo

        session = AgentSession(
            id="test",
            todo_id=None,
            title="Test",
            status="working",
            todo_list=[
                AgentTodo(text="Task 1", completed=False),
                AgentTodo(text="Task 2", completed=False),
                AgentTodo(text="Task 3", completed=False),
            ],
        )

        manager = MultiAgentManager("test-branch")
        progress = manager.calculate_progress(session)
        assert progress == 0

    def test_calculate_progress_all_completed(self):
        """Test progress calculation with all completed TODOs."""
        from ccc.status import AgentSession, AgentTodo

        session = AgentSession(
            id="test",
            todo_id=None,
            title="Test",
            status="working",
            todo_list=[
                AgentTodo(text="Task 1", completed=True),
                AgentTodo(text="Task 2", completed=True),
                AgentTodo(text="Task 3", completed=True),
            ],
        )

        manager = MultiAgentManager("test-branch")
        progress = manager.calculate_progress(session)
        assert progress == 100

    def test_calculate_progress_partial(self):
        """Test progress calculation with partial completion."""
        from ccc.status import AgentSession, AgentTodo

        session = AgentSession(
            id="test",
            todo_id=None,
            title="Test",
            status="working",
            todo_list=[
                AgentTodo(text="Task 1", completed=True),
                AgentTodo(text="Task 2", completed=False),
                AgentTodo(text="Task 3", completed=True),
                AgentTodo(text="Task 4", completed=False),
            ],
        )

        manager = MultiAgentManager("test-branch")
        progress = manager.calculate_progress(session)
        assert progress == 50  # 2 out of 4 completed
