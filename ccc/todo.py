"""
Todo list management for branches

Provides data structures and operations for managing todo items
associated with each branch.
"""

import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict

from ccc.utils import get_branch_dir


@dataclass
class TodoItem:
    """Represents a single todo item in a branch's task list."""

    id: int
    description: str
    status: str  # "not_started", "in_progress", "done", "blocked"
    assigned_agent: Optional[str] = None
    blocked_by: Optional[int] = None  # ID of blocking task
    completed_at: Optional[datetime] = None
    estimated_minutes: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        data = asdict(self)
        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TodoItem":
        """Create from dictionary loaded from YAML."""
        # Parse datetime strings
        if isinstance(data.get("completed_at"), str):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        if isinstance(data.get("created_at"), str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])

        return cls(**data)


@dataclass
class TodoList:
    """Represents the complete todo list for a branch."""

    branch_name: str
    items: List[TodoItem] = field(default_factory=list)

    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        if not self.items:
            return 0.0
        done = sum(1 for item in self.items if item.status == "done")
        return (done / len(self.items)) * 100

    def progress_stats(self) -> Dict[str, int]:
        """Calculate detailed progress statistics."""
        stats = {
            "total": len(self.items),
            "done": 0,
            "in_progress": 0,
            "not_started": 0,
            "blocked": 0,
        }

        for item in self.items:
            if item.status in stats:
                stats[item.status] += 1

        return stats

    def next_task_id(self) -> int:
        """Get the next available task ID."""
        if not self.items:
            return 1
        return max(item.id for item in self.items) + 1

    def get_item(self, task_id: int) -> Optional[TodoItem]:
        """Get a todo item by ID."""
        for item in self.items:
            if item.id == task_id:
                return item
        return None

    def get_item_index(self, task_id: int) -> Optional[int]:
        """Get the index of a todo item by ID."""
        for i, item in enumerate(self.items):
            if item.id == task_id:
                return i
        return None

    def add_item(self, item: TodoItem) -> None:
        """Add a todo item to the list."""
        # Check for duplicate ID
        if self.get_item(item.id) is not None:
            raise ValueError(f"Todo item with ID {item.id} already exists")

        self.items.append(item)

    def delete_item(self, task_id: int) -> bool:
        """Delete a todo item by ID. Returns True if deleted, False if not found."""
        index = self.get_item_index(task_id)
        if index is None:
            return False

        # Check if any other items are blocked by this one
        for item in self.items:
            if item.blocked_by == task_id:
                item.blocked_by = None  # Clear the dependency

        self.items.pop(index)
        return True

    def move_item(self, task_id: int, new_position: int) -> bool:
        """
        Move a todo item to a new position in the list.

        Args:
            task_id: ID of the task to move
            new_position: New position (1-indexed)

        Returns:
            True if moved successfully, False if task not found or invalid position
        """
        current_index = self.get_item_index(task_id)
        if current_index is None:
            return False

        # Convert to 0-indexed and validate
        new_index = new_position - 1
        if new_index < 0 or new_index >= len(self.items):
            return False

        # Move the item
        item = self.items.pop(current_index)
        self.items.insert(new_index, item)
        return True

    def validate_dependency(self, task_id: int, blocked_by: int) -> bool:
        """
        Check if dependency is valid (no circular dependencies).

        Args:
            task_id: ID of the task that would be blocked
            blocked_by: ID of the task it would be blocked by

        Returns:
            True if dependency is valid, False if it would create a circular dependency
        """
        # Can't be blocked by itself
        if task_id == blocked_by:
            return False

        # Check that blocked_by task exists
        if self.get_item(blocked_by) is None:
            return False

        # Check for circular dependencies
        visited = set()
        current = blocked_by

        while current is not None:
            if current in visited or current == task_id:
                return False
            visited.add(current)

            task = self.get_item(current)
            if task:
                current = task.blocked_by
            else:
                break

        return True


# Storage functions


def get_todos_file_path(branch_name: str) -> Path:
    """Get path to todos.yaml for a branch."""
    return get_branch_dir(branch_name) / "todos.yaml"


def load_todos(branch_name: str) -> TodoList:
    """
    Load todo list from YAML file.

    Args:
        branch_name: Branch name

    Returns:
        TodoList instance (empty if file doesn't exist)
    """
    path = get_todos_file_path(branch_name)
    if not path.exists():
        return TodoList(branch_name=branch_name, items=[])

    try:
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        todos_data = data.get("todos", [])
        items = [TodoItem.from_dict(t) for t in todos_data]

        return TodoList(branch_name=branch_name, items=items)

    except Exception as e:
        from ccc.utils import print_warning

        print_warning(f"Error loading todos for {branch_name}: {e}")
        return TodoList(branch_name=branch_name, items=[])


def save_todos(todo_list: TodoList) -> None:
    """
    Save todo list to YAML file.

    Args:
        todo_list: TodoList instance to save
    """
    path = get_todos_file_path(todo_list.branch_name)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {"todos": [item.to_dict() for item in todo_list.items]}

    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


# CRUD operations


def add_todo(
    branch_name: str,
    description: str,
    estimated_minutes: Optional[int] = None,
    blocked_by: Optional[int] = None,
    assigned_agent: Optional[str] = None,
) -> TodoItem:
    """
    Add a new todo item to a branch.

    Args:
        branch_name: Branch name
        description: Todo description
        estimated_minutes: Estimated time in minutes (optional)
        blocked_by: ID of blocking task (optional)
        assigned_agent: Agent to assign to (optional)

    Returns:
        The created TodoItem

    Raises:
        ValueError: If blocked_by creates a circular dependency
    """
    todo_list = load_todos(branch_name)

    # Get next ID
    task_id = todo_list.next_task_id()

    # Validate dependency if provided
    if blocked_by is not None:
        if not todo_list.validate_dependency(task_id, blocked_by):
            raise ValueError(
                f"Invalid dependency: Task {blocked_by} not found or would create circular dependency"
            )

    # Create new todo item
    item = TodoItem(
        id=task_id,
        description=description,
        status="not_started",
        estimated_minutes=estimated_minutes,
        blocked_by=blocked_by,
        assigned_agent=assigned_agent,
    )

    todo_list.add_item(item)
    save_todos(todo_list)

    return item


def list_todos(branch_name: str) -> TodoList:
    """
    List all todos for a branch.

    Args:
        branch_name: Branch name

    Returns:
        TodoList instance
    """
    return load_todos(branch_name)


def update_todo_status(
    branch_name: str, task_id: int, status: str
) -> Optional[TodoItem]:
    """
    Update the status of a todo item.

    Args:
        branch_name: Branch name
        task_id: Task ID
        status: New status ("not_started", "in_progress", "done", "blocked")

    Returns:
        Updated TodoItem if found, None otherwise
    """
    if status not in ["not_started", "in_progress", "done", "blocked"]:
        raise ValueError(f"Invalid status: {status}")

    todo_list = load_todos(branch_name)
    item = todo_list.get_item(task_id)

    if item is None:
        return None

    item.status = status

    # Set completed_at timestamp when marking as done
    if status == "done":
        item.completed_at = datetime.now(timezone.utc)
    elif item.completed_at is not None:
        # Clear completed_at if changing from done to another status
        item.completed_at = None

    save_todos(todo_list)
    return item


def delete_todo(branch_name: str, task_id: int) -> bool:
    """
    Delete a todo item.

    Args:
        branch_name: Branch name
        task_id: Task ID

    Returns:
        True if deleted, False if not found
    """
    todo_list = load_todos(branch_name)
    deleted = todo_list.delete_item(task_id)

    if deleted:
        save_todos(todo_list)

    return deleted


def move_todo(branch_name: str, task_id: int, new_position: int) -> bool:
    """
    Move a todo item to a new position.

    Args:
        branch_name: Branch name
        task_id: Task ID
        new_position: New position (1-indexed)

    Returns:
        True if moved, False if not found or invalid position
    """
    todo_list = load_todos(branch_name)
    moved = todo_list.move_item(task_id, new_position)

    if moved:
        save_todos(todo_list)

    return moved


def assign_todo(
    branch_name: str, task_id: int, agent_name: Optional[str]
) -> Optional[TodoItem]:
    """
    Assign a todo item to an agent.

    Args:
        branch_name: Branch name
        task_id: Task ID
        agent_name: Agent name (None to unassign)

    Returns:
        Updated TodoItem if found, None otherwise
    """
    todo_list = load_todos(branch_name)
    item = todo_list.get_item(task_id)

    if item is None:
        return None

    item.assigned_agent = agent_name
    save_todos(todo_list)

    return item


def set_blocked_by(
    branch_name: str, task_id: int, blocked_by: Optional[int]
) -> Optional[TodoItem]:
    """
    Set or clear the blocking dependency for a todo item.

    Args:
        branch_name: Branch name
        task_id: Task ID
        blocked_by: ID of blocking task (None to clear)

    Returns:
        Updated TodoItem if successful, None if task not found

    Raises:
        ValueError: If dependency would create a circular dependency
    """
    todo_list = load_todos(branch_name)
    item = todo_list.get_item(task_id)

    if item is None:
        return None

    # Validate dependency if setting one
    if blocked_by is not None:
        if not todo_list.validate_dependency(task_id, blocked_by):
            raise ValueError(
                f"Invalid dependency: Task {blocked_by} not found or would create circular dependency"
            )

    item.blocked_by = blocked_by

    # Automatically set status to blocked if setting a dependency
    if blocked_by is not None:
        item.status = "blocked"

    save_todos(todo_list)
    return item


def update_todo_description(
    branch_name: str, task_id: int, description: str
) -> Optional[TodoItem]:
    """
    Update the description of a todo item.

    Args:
        branch_name: Branch name
        task_id: Task ID
        description: New description

    Returns:
        Updated TodoItem if found, None otherwise
    """
    todo_list = load_todos(branch_name)
    item = todo_list.get_item(task_id)

    if item is None:
        return None

    item.description = description
    save_todos(todo_list)

    return item


def init_todos(branch_name: str) -> None:
    """
    Initialize an empty todo list for a branch.

    Args:
        branch_name: Branch name
    """
    todo_list = TodoList(branch_name=branch_name, items=[])
    save_todos(todo_list)
