"""
Tests for todo list management
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import shutil

from ccc.todo import (
    TodoItem,
    TodoList,
    add_todo,
    list_todos,
    update_todo_status,
    delete_todo,
    move_todo,
    assign_todo,
    set_blocked_by,
    update_todo_description,
    get_todos_file_path,
    save_todos,
    load_todos,
)


@pytest.fixture
def temp_ccc_home(monkeypatch):
    """Create a temporary CCC home directory for tests."""
    temp_dir = tempfile.mkdtemp()

    # Mock get_ccc_home to return temp directory
    def mock_get_ccc_home():
        return Path(temp_dir)

    monkeypatch.setattr("ccc.todo.get_branch_dir", lambda branch: Path(temp_dir) / branch)

    yield Path(temp_dir)

    # Cleanup
    shutil.rmtree(temp_dir)


class TestTodoItem:
    """Test TodoItem data structure."""

    def test_create_todo_item(self):
        """Test creating a TodoItem."""
        item = TodoItem(
            id=1,
            description="Write tests",
            status="not_started",
        )

        assert item.id == 1
        assert item.description == "Write tests"
        assert item.status == "not_started"
        assert item.assigned_agent is None
        assert item.blocked_by is None
        assert item.completed_at is None

    def test_todo_item_to_dict(self):
        """Test converting TodoItem to dictionary."""
        item = TodoItem(
            id=1,
            description="Write tests",
            status="done",
            assigned_agent="agent-1",
            completed_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )

        data = item.to_dict()

        assert data["id"] == 1
        assert data["description"] == "Write tests"
        assert data["status"] == "done"
        assert data["assigned_agent"] == "agent-1"
        assert data["completed_at"] == "2025-01-01T12:00:00+00:00"

    def test_todo_item_from_dict(self):
        """Test creating TodoItem from dictionary."""
        data = {
            "id": 1,
            "description": "Write tests",
            "status": "done",
            "assigned_agent": "agent-1",
            "completed_at": "2025-01-01T12:00:00+00:00",
            "created_at": "2025-01-01T10:00:00+00:00",
            "estimated_minutes": 30,
            "blocked_by": None,
        }

        item = TodoItem.from_dict(data)

        assert item.id == 1
        assert item.description == "Write tests"
        assert item.status == "done"
        assert item.assigned_agent == "agent-1"
        assert isinstance(item.completed_at, datetime)
        assert isinstance(item.created_at, datetime)


class TestTodoList:
    """Test TodoList functionality."""

    def test_empty_todo_list(self):
        """Test creating an empty TodoList."""
        todo_list = TodoList(branch_name="feature/test", items=[])

        assert todo_list.branch_name == "feature/test"
        assert len(todo_list.items) == 0
        assert todo_list.progress_percentage() == 0.0

    def test_progress_percentage(self):
        """Test progress calculation."""
        items = [
            TodoItem(id=1, description="Task 1", status="done"),
            TodoItem(id=2, description="Task 2", status="done"),
            TodoItem(id=3, description="Task 3", status="in_progress"),
            TodoItem(id=4, description="Task 4", status="not_started"),
        ]

        todo_list = TodoList(branch_name="feature/test", items=items)

        # 2 out of 4 done = 50%
        assert todo_list.progress_percentage() == 50.0

    def test_progress_stats(self):
        """Test detailed progress statistics."""
        items = [
            TodoItem(id=1, description="Task 1", status="done"),
            TodoItem(id=2, description="Task 2", status="done"),
            TodoItem(id=3, description="Task 3", status="in_progress"),
            TodoItem(id=4, description="Task 4", status="not_started"),
            TodoItem(id=5, description="Task 5", status="blocked"),
        ]

        todo_list = TodoList(branch_name="feature/test", items=items)
        stats = todo_list.progress_stats()

        assert stats["total"] == 5
        assert stats["done"] == 2
        assert stats["in_progress"] == 1
        assert stats["not_started"] == 1
        assert stats["blocked"] == 1

    def test_next_task_id(self):
        """Test getting next available task ID."""
        # Empty list
        todo_list = TodoList(branch_name="feature/test", items=[])
        assert todo_list.next_task_id() == 1

        # With items
        items = [
            TodoItem(id=1, description="Task 1", status="done"),
            TodoItem(id=3, description="Task 3", status="done"),
            TodoItem(id=2, description="Task 2", status="done"),
        ]
        todo_list = TodoList(branch_name="feature/test", items=items)
        assert todo_list.next_task_id() == 4  # Max ID + 1

    def test_get_item(self):
        """Test retrieving a todo item by ID."""
        items = [
            TodoItem(id=1, description="Task 1", status="done"),
            TodoItem(id=2, description="Task 2", status="in_progress"),
        ]

        todo_list = TodoList(branch_name="feature/test", items=items)

        item = todo_list.get_item(2)
        assert item is not None
        assert item.id == 2
        assert item.description == "Task 2"

        # Non-existent item
        assert todo_list.get_item(999) is None

    def test_add_item(self):
        """Test adding a todo item."""
        todo_list = TodoList(branch_name="feature/test", items=[])

        item = TodoItem(id=1, description="Task 1", status="not_started")
        todo_list.add_item(item)

        assert len(todo_list.items) == 1
        assert todo_list.items[0].description == "Task 1"

    def test_add_item_duplicate_id(self):
        """Test that adding duplicate ID raises error."""
        items = [TodoItem(id=1, description="Task 1", status="done")]
        todo_list = TodoList(branch_name="feature/test", items=items)

        duplicate = TodoItem(id=1, description="Task 2", status="not_started")

        with pytest.raises(ValueError, match="already exists"):
            todo_list.add_item(duplicate)

    def test_delete_item(self):
        """Test deleting a todo item."""
        items = [
            TodoItem(id=1, description="Task 1", status="done"),
            TodoItem(id=2, description="Task 2", status="not_started"),
        ]

        todo_list = TodoList(branch_name="feature/test", items=items)

        assert todo_list.delete_item(1) is True
        assert len(todo_list.items) == 1
        assert todo_list.items[0].id == 2

        # Try deleting non-existent item
        assert todo_list.delete_item(999) is False

    def test_delete_item_clears_dependencies(self):
        """Test that deleting an item clears dependencies on it."""
        items = [
            TodoItem(id=1, description="Task 1", status="done"),
            TodoItem(id=2, description="Task 2", status="blocked", blocked_by=1),
        ]

        todo_list = TodoList(branch_name="feature/test", items=items)

        todo_list.delete_item(1)

        # Task 2 should no longer be blocked
        item2 = todo_list.get_item(2)
        assert item2.blocked_by is None

    def test_move_item(self):
        """Test moving a todo item to a new position."""
        items = [
            TodoItem(id=1, description="Task 1", status="not_started"),
            TodoItem(id=2, description="Task 2", status="not_started"),
            TodoItem(id=3, description="Task 3", status="not_started"),
        ]

        todo_list = TodoList(branch_name="feature/test", items=items)

        # Move task 3 to position 1
        assert todo_list.move_item(3, 1) is True

        assert todo_list.items[0].id == 3
        assert todo_list.items[1].id == 1
        assert todo_list.items[2].id == 2

    def test_move_item_invalid(self):
        """Test moving to invalid position."""
        items = [
            TodoItem(id=1, description="Task 1", status="not_started"),
            TodoItem(id=2, description="Task 2", status="not_started"),
        ]

        todo_list = TodoList(branch_name="feature/test", items=items)

        # Invalid position (out of range)
        assert todo_list.move_item(1, 0) is False
        assert todo_list.move_item(1, 10) is False

        # Non-existent task
        assert todo_list.move_item(999, 1) is False

    def test_validate_dependency(self):
        """Test dependency validation."""
        items = [
            TodoItem(id=1, description="Task 1", status="done"),
            TodoItem(id=2, description="Task 2", status="not_started"),
            TodoItem(id=3, description="Task 3", status="blocked", blocked_by=2),
        ]

        todo_list = TodoList(branch_name="feature/test", items=items)

        # Valid dependency
        assert todo_list.validate_dependency(4, 1) is True

        # Self-dependency (invalid)
        assert todo_list.validate_dependency(1, 1) is False

        # Non-existent blocker (invalid)
        assert todo_list.validate_dependency(1, 999) is False

        # Circular dependency (invalid)
        # Task 2 is already blocked by task 3 (via blocked_by)
        # So making task 2 block task 3 would create a circle
        assert todo_list.validate_dependency(2, 3) is False


class TestTodoCRUD:
    """Test CRUD operations for todos."""

    def test_add_todo(self, temp_ccc_home):
        """Test adding a todo."""
        item = add_todo(
            "feature/test",
            "Write unit tests",
            estimated_minutes=30,
        )

        assert item.id == 1
        assert item.description == "Write unit tests"
        assert item.status == "not_started"
        assert item.estimated_minutes == 30

    def test_add_multiple_todos(self, temp_ccc_home):
        """Test adding multiple todos."""
        item1 = add_todo("feature/test", "Task 1")
        item2 = add_todo("feature/test", "Task 2")
        item3 = add_todo("feature/test", "Task 3")

        assert item1.id == 1
        assert item2.id == 2
        assert item3.id == 3

    def test_add_todo_with_dependency(self, temp_ccc_home):
        """Test adding a todo with a blocking dependency."""
        item1 = add_todo("feature/test", "Task 1")
        item2 = add_todo("feature/test", "Task 2", blocked_by=1)

        assert item2.blocked_by == 1

    def test_add_todo_invalid_dependency(self, temp_ccc_home):
        """Test that invalid dependency raises error."""
        add_todo("feature/test", "Task 1")

        with pytest.raises(ValueError, match="Invalid dependency"):
            add_todo("feature/test", "Task 2", blocked_by=999)

    def test_list_todos(self, temp_ccc_home):
        """Test listing todos."""
        add_todo("feature/test", "Task 1")
        add_todo("feature/test", "Task 2")

        todo_list = list_todos("feature/test")

        assert len(todo_list.items) == 2
        assert todo_list.items[0].description == "Task 1"
        assert todo_list.items[1].description == "Task 2"

    def test_list_todos_empty(self, temp_ccc_home):
        """Test listing todos for empty branch."""
        todo_list = list_todos("feature/nonexistent")

        assert len(todo_list.items) == 0

    def test_update_todo_status(self, temp_ccc_home):
        """Test updating todo status."""
        item = add_todo("feature/test", "Task 1")

        updated = update_todo_status("feature/test", item.id, "in_progress")

        assert updated is not None
        assert updated.status == "in_progress"

    def test_update_todo_status_to_done(self, temp_ccc_home):
        """Test that marking as done sets completed_at."""
        item = add_todo("feature/test", "Task 1")

        updated = update_todo_status("feature/test", item.id, "done")

        assert updated.status == "done"
        assert updated.completed_at is not None

    def test_update_todo_status_from_done(self, temp_ccc_home):
        """Test that changing from done clears completed_at."""
        item = add_todo("feature/test", "Task 1")
        update_todo_status("feature/test", item.id, "done")

        updated = update_todo_status("feature/test", item.id, "in_progress")

        assert updated.status == "in_progress"
        assert updated.completed_at is None

    def test_update_todo_status_invalid(self, temp_ccc_home):
        """Test that invalid status raises error."""
        item = add_todo("feature/test", "Task 1")

        with pytest.raises(ValueError, match="Invalid status"):
            update_todo_status("feature/test", item.id, "invalid_status")

    def test_delete_todo(self, temp_ccc_home):
        """Test deleting a todo."""
        item1 = add_todo("feature/test", "Task 1")
        item2 = add_todo("feature/test", "Task 2")

        assert delete_todo("feature/test", item1.id) is True

        todo_list = list_todos("feature/test")
        assert len(todo_list.items) == 1
        assert todo_list.items[0].id == item2.id

    def test_delete_todo_nonexistent(self, temp_ccc_home):
        """Test deleting non-existent todo."""
        assert delete_todo("feature/test", 999) is False

    def test_move_todo(self, temp_ccc_home):
        """Test moving a todo."""
        add_todo("feature/test", "Task 1")
        add_todo("feature/test", "Task 2")
        item3 = add_todo("feature/test", "Task 3")

        assert move_todo("feature/test", item3.id, 1) is True

        todo_list = list_todos("feature/test")
        assert todo_list.items[0].id == item3.id

    def test_assign_todo(self, temp_ccc_home):
        """Test assigning a todo to an agent."""
        item = add_todo("feature/test", "Task 1")

        updated = assign_todo("feature/test", item.id, "agent-1")

        assert updated is not None
        assert updated.assigned_agent == "agent-1"

    def test_unassign_todo(self, temp_ccc_home):
        """Test unassigning a todo."""
        item = add_todo("feature/test", "Task 1", assigned_agent="agent-1")

        updated = assign_todo("feature/test", item.id, None)

        assert updated.assigned_agent is None

    def test_set_blocked_by(self, temp_ccc_home):
        """Test setting blocking dependency."""
        item1 = add_todo("feature/test", "Task 1")
        item2 = add_todo("feature/test", "Task 2")

        updated = set_blocked_by("feature/test", item2.id, item1.id)

        assert updated.blocked_by == item1.id
        assert updated.status == "blocked"

    def test_set_blocked_by_invalid(self, temp_ccc_home):
        """Test that invalid blocking dependency raises error."""
        item = add_todo("feature/test", "Task 1")

        with pytest.raises(ValueError, match="Invalid dependency"):
            set_blocked_by("feature/test", item.id, 999)

    def test_clear_blocked_by(self, temp_ccc_home):
        """Test clearing blocking dependency."""
        item1 = add_todo("feature/test", "Task 1")
        item2 = add_todo("feature/test", "Task 2", blocked_by=item1.id)

        updated = set_blocked_by("feature/test", item2.id, None)

        assert updated.blocked_by is None

    def test_update_todo_description(self, temp_ccc_home):
        """Test updating todo description."""
        item = add_todo("feature/test", "Task 1")

        updated = update_todo_description("feature/test", item.id, "Updated Task 1")

        assert updated.description == "Updated Task 1"


class TestTodoStorage:
    """Test todo storage and loading."""

    def test_save_and_load_todos(self, temp_ccc_home):
        """Test saving and loading todos."""
        # Create a todo list
        items = [
            TodoItem(id=1, description="Task 1", status="done"),
            TodoItem(id=2, description="Task 2", status="in_progress", assigned_agent="agent-1"),
        ]
        todo_list = TodoList(branch_name="feature/test", items=items)

        # Save
        save_todos(todo_list)

        # Load
        loaded = load_todos("feature/test")

        assert len(loaded.items) == 2
        assert loaded.items[0].description == "Task 1"
        assert loaded.items[0].status == "done"
        assert loaded.items[1].description == "Task 2"
        assert loaded.items[1].assigned_agent == "agent-1"

    def test_load_nonexistent_todos(self, temp_ccc_home):
        """Test loading todos from non-existent file."""
        loaded = load_todos("feature/nonexistent")

        assert len(loaded.items) == 0
        assert loaded.branch_name == "feature/nonexistent"

    def test_todos_file_path(self, temp_ccc_home):
        """Test getting todos file path."""
        path = get_todos_file_path("feature/test")

        assert path.name == "todos.yaml"
        assert "feature" in str(path) or "test" in str(path)
