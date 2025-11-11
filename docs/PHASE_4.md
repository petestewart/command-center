# Phase 4: Todo List Management - Implementation Plan

## Overview

**Duration:** 2 weeks  
**Goal:** Break tickets into trackable subtasks with progress visualization

Phase 4 adds the ability to break down work into discrete tasks, track progress, and assign tasks to agents.

---

## Goal

Break tickets into trackable subtasks with progress visualization

## Key Features

### 4.1 Todo List Structure

**Todo item format:**
```python
@dataclass
class TodoItem:
    id: int
    description: str
    status: str  # "not_started", "in_progress", "done", "blocked"
    assigned_agent: Optional[str]
    blocked_by: Optional[int]  # ID of blocking task
    completed_at: Optional[datetime]
    estimated_minutes: Optional[int]
```

**Storage:** `~/.cc-control/<branch-name>/todos.yaml`

**Example:**
```yaml
todos:
  - id: 1
    description: Design API endpoint schema
    status: done
    assigned_agent: agent-1
    completed_at: 2025-11-09T10:30:00Z
    
  - id: 2
    description: Implement batch processor
    status: done
    assigned_agent: agent-1
    completed_at: 2025-11-09T12:15:00Z
    
  - id: 3
    description: Add input validation
    status: in_progress
    assigned_agent: agent-1
    
  - id: 4
    description: Write integration tests
    status: not_started
    blocked_by: 3
    
  - id: 5
    description: Update API documentation
    status: not_started
```

### 4.2 Todo Management UI

**Todo list view (in ticket detail):**
```
┌─ Todo List: IN-413 ────────────────────────────┐
│                                                │
│ ✓ 1. Design API endpoint schema               │
│ ✓ 2. Implement batch processor                │
│ ⚙ 3. Add input validation          [agent-1]  │
│ ⏸ 4. Write integration tests       (blocked)  │
│ ☐ 5. Update API documentation                 │
│                                                │
│ Progress: 3/5 complete (60%)                   │
│                                                │
│ [n]ew task [e]dit [d]elete [m]ove [r]eorder   │
└────────────────────────────────────────────────┘
```

**Add task dialog:**
```
┌─ New Todo Item ────────────────────────────────┐
│                                                │
│ Description:                                   │
│ ┌────────────────────────────────────────────┐ │
│ │ Write unit tests for validator            │ │
│ └────────────────────────────────────────────┘ │
│                                                │
│ Estimated time: [  ] minutes (optional)        │
│                                                │
│ Blocked by task: [  ] (optional)               │
│                                                │
│ [Enter] create [Esc] cancel                    │
└────────────────────────────────────────────────┘
```

### 4.3 Progress Visualization

**In list view:**
```
● IN-413  Public API bulk uploads    [████░░] 60%   Working
```

**Progress bar with details:**
```
Progress: [████████████░░░░░░░] 60%
3 done | 1 in progress | 1 not started
```

### 4.4 Agent Assignment

- Manually assign tasks to agents
- Agent updates which task they're working on
- Status file includes `current_task_id`

```json
{
  "status": "working",
  "current_task_id": 3,
  "current_task": "Add input validation"
}
```

## CLI Commands

**Todo management:**
```bash
# Add a new todo
cc todo add <branch> "Write unit tests"

# List todos
cc todo list <branch>

# Mark todo as done
cc todo done <branch> <task-id>

# Update todo status
cc todo status <branch> <task-id> in_progress

# Delete a todo
cc todo delete <branch> <task-id>

# Reorder todos
cc todo move <branch> <task-id> <new-position>
```

## Technical Implementation

### Data Structure

```python
@dataclass
class TodoList:
    branch_name: str
    items: List[TodoItem]
    
    def progress_percentage(self) -> float:
        if not self.items:
            return 0.0
        done = sum(1 for item in self.items if item.status == "done")
        return (done / len(self.items)) * 100
    
    def next_task_id(self) -> int:
        if not self.items:
            return 1
        return max(item.id for item in self.items) + 1
```

### Storage

```python
def save_todos(branch_name: str, todos: TodoList):
    """Save todo list to YAML file"""
    path = get_branch_dir(branch_name) / "todos.yaml"
    with open(path, 'w') as f:
        yaml.dump(todos.to_dict(), f)

def load_todos(branch_name: str) -> TodoList:
    """Load todo list from YAML file"""
    path = get_branch_dir(branch_name) / "todos.yaml"
    if not path.exists():
        return TodoList(branch_name=branch_name, items=[])
    with open(path) as f:
        data = yaml.safe_load(f)
        return TodoList.from_dict(data)
```

### Progress Calculation

```python
def calculate_progress(todos: List[TodoItem]) -> dict:
    """Calculate detailed progress statistics"""
    total = len(todos)
    done = sum(1 for t in todos if t.status == "done")
    in_progress = sum(1 for t in todos if t.status == "in_progress")
    blocked = sum(1 for t in todos if t.status == "blocked")
    not_started = total - done - in_progress - blocked
    
    return {
        "total": total,
        "done": done,
        "in_progress": in_progress,
        "blocked": blocked,
        "not_started": not_started,
        "percentage": (done / total * 100) if total > 0 else 0
    }
```

## Deliverables

✅ Todo list data structure  
✅ Todo CRUD operations  
✅ Todo list display in TUI  
✅ Progress visualization  
✅ Task dependencies  
✅ Agent task assignment  

## Success Criteria

### Functionality
✅ Can create todos with descriptions and optional metadata  
✅ Can mark todos as done/in-progress/blocked  
✅ Can reorder todos via drag-drop or commands  
✅ Can assign todos to specific agents  
✅ Can set task dependencies (blocked_by)  
✅ Progress percentage calculates correctly  

### User Experience
✅ Todo list is easy to navigate with keyboard  
✅ Progress bar updates immediately when status changes  
✅ Can quickly add todos without leaving TUI  
✅ Visual indicators clearly show task status  

### Integration
✅ Agent status updates reference current task  
✅ Todos persist across sessions  
✅ Todo list integrates smoothly into branch detail view  

## Testing Plan

### CRUD Operations Testing
- Create todos with various descriptions
- Edit existing todos
- Delete todos
- Verify IDs remain stable after deletions
- Test with empty todo list

### Progress Tracking Testing
- Verify percentage with all statuses
- Test with 0 todos (should show 0%)
- Test with all todos done (should show 100%)
- Verify progress bar renders correctly

### Dependencies Testing
- Create todo blocked by another
- Verify blocked tasks show correctly
- Complete blocking task, verify UI updates
- Test circular dependencies (should prevent)

### Agent Integration Testing
- Assign todo to agent
- Agent updates current_task_id
- Verify TUI shows which agent is on which task
- Test multiple agents on different tasks

## Configuration

### Todo Settings

Add to `~/.cc-control/config.yaml`:
```yaml
todos:
  auto_assign_first_task: true  # Auto-assign first task to agent
  show_completed: true           # Show completed tasks in list
  max_display: 10                # Max todos to show in TUI
  estimate_in_hours: false       # Use hours instead of minutes
```

## UI Enhancements

### Keyboard Shortcuts (in Todo View)

- `n` - New todo
- `e` - Edit selected todo
- `d` - Delete selected todo
- `Space` - Toggle status (done ↔ not_started)
- `m` - Move/reorder todo
- `a` - Assign to agent
- `b` - Set as blocked by another task

### Visual Indicators

```
✓  - Done
⚙  - In progress
☐  - Not started
⏸  - Blocked
```

## Known Limitations

❌ No subtasks (todos within todos)  
❌ No time tracking (just estimates)  
❌ No todo templates  
❌ No recurring todos  
❌ No automatic todo generation from code comments  

## Future Enhancements (Post-Phase 4)

- AI-suggested task breakdown
- Automatic estimation based on past tasks
- Todo templates for common workflows
- Integration with commit messages
- Burndown charts and velocity tracking

## Documentation Updates

Required documentation:
1. **TODO_MANAGEMENT.md** - Using todo lists
2. **PROGRESS_TRACKING.md** - Understanding progress metrics
3. **AGENT_ASSIGNMENT.md** - Assigning tasks to agents
4. **KEYBOARD_SHORTCUTS.md** - Updated with todo shortcuts

## Migration Notes

For users upgrading from Phase 3:
- Existing branches gain empty todo lists by default
- No breaking changes
- Todo feature is optional (branches work without todos)

## Next Steps to Phase 5

After Phase 4 completes:
- Analyze which todos take longest
- Identify common todo patterns
- Plan IDE integration to jump to task-related files
