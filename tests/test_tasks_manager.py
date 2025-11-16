"""
Tests for TasksManager - TASKS.md parsing and management
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import time

from ccc.tasks_manager import TasksManager, Task


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def tasks_file(temp_dir):
    """Create a test TASKS.md file."""
    file_path = temp_dir / "TASKS.md"
    return file_path


class TestTask:
    """Test Task dataclass."""

    def test_create_task(self):
        """Test creating a Task."""
        task = Task(
            text="Write tests",
            completed=False,
            indent_level=0
        )

        assert task.text == "Write tests"
        assert task.completed is False
        assert task.indent_level == 0

    def test_create_nested_task(self):
        """Test creating a nested Task."""
        task = Task(
            text="Nested subtask",
            completed=True,
            indent_level=2
        )

        assert task.text == "Nested subtask"
        assert task.completed is True
        assert task.indent_level == 2


class TestTasksManager:
    """Test TasksManager functionality."""

    def test_init_with_nonexistent_file(self, tasks_file):
        """Test initialization with non-existent file."""
        manager = TasksManager(str(tasks_file))
        assert manager.tasks_file == tasks_file
        assert manager._last_modified is None
        assert manager._cached_tasks == []

    def test_load_tasks_file_not_found(self, tasks_file):
        """Test loading tasks when file doesn't exist."""
        manager = TasksManager(str(tasks_file))
        tasks = manager.load_tasks()

        assert tasks == []
        assert manager._cached_tasks == []

    def test_load_tasks_empty_file(self, tasks_file):
        """Test loading tasks from empty file."""
        # Create empty file
        tasks_file.write_text("")

        manager = TasksManager(str(tasks_file))
        tasks = manager.load_tasks()

        assert tasks == []

    def test_load_tasks_simple(self, tasks_file):
        """Test loading simple tasks."""
        content = """# Project Tasks

- [ ] Task 1
- [x] Task 2
- [ ] Task 3
"""
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))
        tasks = manager.load_tasks()

        assert len(tasks) == 3
        assert tasks[0].text == "Task 1"
        assert tasks[0].completed is False
        assert tasks[0].indent_level == 0

        assert tasks[1].text == "Task 2"
        assert tasks[1].completed is True
        assert tasks[1].indent_level == 0

        assert tasks[2].text == "Task 3"
        assert tasks[2].completed is False
        assert tasks[2].indent_level == 0

    def test_load_tasks_with_asterisk_bullet(self, tasks_file):
        """Test loading tasks with asterisk bullets."""
        content = """
* [ ] Task with asterisk
* [x] Completed with asterisk
"""
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))
        tasks = manager.load_tasks()

        assert len(tasks) == 2
        assert tasks[0].text == "Task with asterisk"
        assert tasks[0].completed is False
        assert tasks[1].text == "Completed with asterisk"
        assert tasks[1].completed is True

    def test_load_tasks_nested(self, tasks_file):
        """Test loading nested tasks with indentation."""
        content = """
- [ ] Parent task 1
  - [ ] Nested task 1.1
  - [x] Nested task 1.2
    - [ ] Double nested 1.2.1
- [x] Parent task 2
  - [ ] Nested task 2.1
"""
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))
        tasks = manager.load_tasks()

        assert len(tasks) == 6

        # Parent task 1
        assert tasks[0].text == "Parent task 1"
        assert tasks[0].indent_level == 0
        assert tasks[0].completed is False

        # Nested task 1.1 (2 spaces = indent level 1)
        assert tasks[1].text == "Nested task 1.1"
        assert tasks[1].indent_level == 1
        assert tasks[1].completed is False

        # Nested task 1.2
        assert tasks[2].text == "Nested task 1.2"
        assert tasks[2].indent_level == 1
        assert tasks[2].completed is True

        # Double nested 1.2.1 (4 spaces = indent level 2)
        assert tasks[3].text == "Double nested 1.2.1"
        assert tasks[3].indent_level == 2
        assert tasks[3].completed is False

        # Parent task 2
        assert tasks[4].text == "Parent task 2"
        assert tasks[4].indent_level == 0
        assert tasks[4].completed is True

        # Nested task 2.1
        assert tasks[5].text == "Nested task 2.1"
        assert tasks[5].indent_level == 1
        assert tasks[5].completed is False

    def test_load_tasks_uppercase_x(self, tasks_file):
        """Test loading tasks with uppercase X for completion."""
        content = """
- [X] Task with uppercase X
- [x] Task with lowercase x
"""
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))
        tasks = manager.load_tasks()

        assert len(tasks) == 2
        assert tasks[0].completed is True
        assert tasks[1].completed is True

    def test_load_tasks_mixed_content(self, tasks_file):
        """Test loading tasks from file with mixed content."""
        content = """# Project Tasks

Some description here.

## In Progress
- [ ] Task 1
- [x] Task 2

## Completed
- [x] Task 3

Some notes here.

- [ ] Task 4

Not a task: just a regular list item
"""
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))
        tasks = manager.load_tasks()

        # Should only parse lines with checkbox format
        assert len(tasks) == 4

    def test_load_tasks_caching(self, tasks_file):
        """Test that tasks are cached and not reloaded if file unchanged."""
        content = "- [ ] Task 1\n- [x] Task 2"
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))

        # First load
        tasks1 = manager.load_tasks()
        assert len(tasks1) == 2

        # Second load should return cached version
        tasks2 = manager.load_tasks()
        assert tasks2 is tasks1  # Same object reference

        # Modify file
        time.sleep(0.01)  # Ensure mtime changes
        content = "- [ ] Task 1\n- [x] Task 2\n- [ ] Task 3"
        tasks_file.write_text(content)

        # Third load should reload
        tasks3 = manager.load_tasks()
        assert len(tasks3) == 3
        assert tasks3 is not tasks1

    def test_load_tasks_force_reload(self, tasks_file):
        """Test force reload functionality."""
        content = "- [ ] Task 1"
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))

        # First load
        tasks1 = manager.load_tasks()
        assert len(tasks1) == 1

        # Force reload should reload even if file unchanged
        tasks2 = manager.load_tasks(force_reload=True)
        assert len(tasks2) == 1
        # Note: Depending on implementation, this might be a new list

    def test_get_file_status_not_exists(self, tasks_file):
        """Test get_file_status when file doesn't exist."""
        manager = TasksManager(str(tasks_file))
        status = manager.get_file_status()

        assert status['exists'] is False
        assert status['path'] == str(tasks_file)
        assert status['last_modified'] is None
        assert status['task_count'] == 0

    def test_get_file_status_exists(self, tasks_file):
        """Test get_file_status when file exists."""
        content = "- [ ] Task 1\n- [x] Task 2"
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))
        manager.load_tasks()  # Load tasks first
        status = manager.get_file_status()

        assert status['exists'] is True
        assert status['path'] == str(tasks_file)
        assert status['last_modified'] is not None
        assert status['task_count'] == 2

    def test_get_completion_stats_empty(self, tasks_file):
        """Test completion stats with no tasks."""
        manager = TasksManager(str(tasks_file))
        stats = manager.get_completion_stats()

        assert stats['total'] == 0
        assert stats['completed'] == 0
        assert stats['pending'] == 0
        assert stats['completion_percent'] == 0

    def test_get_completion_stats(self, tasks_file):
        """Test completion stats calculation."""
        content = """
- [ ] Task 1
- [x] Task 2
- [x] Task 3
- [ ] Task 4
- [x] Task 5
"""
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))
        manager.load_tasks()
        stats = manager.get_completion_stats()

        assert stats['total'] == 5
        assert stats['completed'] == 3
        assert stats['pending'] == 2
        assert stats['completion_percent'] == 60  # 3/5 = 60%

    def test_get_completion_stats_all_completed(self, tasks_file):
        """Test completion stats when all tasks completed."""
        content = "- [x] Task 1\n- [x] Task 2"
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))
        manager.load_tasks()
        stats = manager.get_completion_stats()

        assert stats['total'] == 2
        assert stats['completed'] == 2
        assert stats['pending'] == 0
        assert stats['completion_percent'] == 100

    def test_parse_tasks_malformed(self, tasks_file):
        """Test parsing with malformed markdown."""
        content = """
- [ ] Good task
-[ ] Missing space
- [] Missing checkbox state
- [y] Invalid checkbox state
- [ Task without closing bracket
"""
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))
        tasks = manager.load_tasks()

        # Should only parse the valid task
        assert len(tasks) == 1
        assert tasks[0].text == "Good task"

    def test_large_file_performance(self, tasks_file):
        """Test performance with large number of tasks."""
        # Generate 500 tasks
        lines = []
        for i in range(500):
            checkbox = "[x]" if i % 2 == 0 else "[ ]"
            indent = "  " * (i % 5)  # Vary indentation
            lines.append(f"{indent}- {checkbox} Task {i}")

        content = "\n".join(lines)
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))

        # Measure load time
        import time
        start = time.time()
        tasks = manager.load_tasks()
        duration = time.time() - start

        assert len(tasks) == 500
        assert duration < 1.0  # Should load in under 1 second

    def test_file_permission_error(self, tasks_file, monkeypatch):
        """Test handling of file permission errors."""
        content = "- [ ] Task 1"
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))

        # Mock open to raise permission error
        def mock_open(*args, **kwargs):
            raise PermissionError("Permission denied")

        monkeypatch.setattr("builtins.open", mock_open)

        # Should handle gracefully
        tasks = manager.load_tasks()
        assert tasks == []

    def test_max_nesting_depth(self, tasks_file):
        """Test handling of deeply nested tasks."""
        content = """
- [ ] Level 0
  - [ ] Level 1
    - [ ] Level 2
      - [ ] Level 3
        - [ ] Level 4
          - [ ] Level 5
            - [ ] Level 6
"""
        tasks_file.write_text(content)

        manager = TasksManager(str(tasks_file))
        tasks = manager.load_tasks()

        assert len(tasks) == 7
        for i, task in enumerate(tasks):
            assert task.indent_level == i
