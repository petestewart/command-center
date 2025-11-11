# Phases 3-10: Detailed Planning Overview

This document provides detailed planning for phases 3 through 10 of Command Center development. Each phase builds incrementally on previous work.

---

## Phase 3: Developer Actions (2 weeks)

### Goal

Enable common actions directly from Command Center without dropping to CLI

### Key Features

#### 3.1 Git Operations

**In-TUI git commands:**

- `c` - Commit with message dialog
- `p` - Push to remote
- `P` - Pull from remote
- `l` - View commit log (inline)
- `g` - Enhanced git status (modal view)

**Git commit dialog:**

```
┌─ Commit Changes: IN-413 ───────────────────────┐
│ Modified files (3):                            │
│ ☑ src/api/bulk-upload.ts                      │
│ ☑ src/validators/input.ts                     │
│ ☐ tests/api/bulk-upload.test.ts               │
│                                                │
│ Commit message:                                │
│ ┌────────────────────────────────────────────┐ │
│ │ Add input validation for bulk uploads     │ │
│ │                                            │ │
│ │ - Validate required fields                │ │
│ │ - Check data types                        │ │
│ │ - Add error messages                      │ │
│ └────────────────────────────────────────────┘ │
│                                                │
│ [Tab] toggle files [Enter] commit [Esc] cancel│
└────────────────────────────────────────────────┘
```

#### 3.2 Build Triggering

- `b` key to trigger build from TUI
- Show build progress in real-time
- Stream build output to panel
- Toast notification on completion

**Build output view:**

```
┌─ Building: IN-413 ─────────────────────────────┐
│ Running: npm run build                         │
│                                                │
│ > tsc --project tsconfig.json                  │
│ ✓ Compiled successfully                        │
│                                                │
│ Time: 45.2s                                    │
│ Warnings: 3                                    │
│                                                │
│ [Press any key to close]                       │
└────────────────────────────────────────────────┘
```

#### 3.3 Test Execution

- `t` key to run tests from TUI
- Show test progress
- Display results immediately
- Jump to failed test files

#### 3.4 File Preview

- `f` key to browse changed files
- Show inline diffs with syntax highlighting
- Use `delta` or `diff-so-fancy` for rendering

**File diff view:**

```
┌─ File: src/api/bulk-upload.ts ─────────────────┐
│ Modified 2 hours ago (47 lines changed)        │
│                                                │
│  40 │   export async function bulkUpload(     │
│  41 │     data: BulkUploadRequest              │
│  42 │   ): Promise<Result> {                   │
│+ 43 │     // Validate input                    │
│+ 44 │     const validation = validateInput(    │
│+ 45 │       data                               │
│+ 46 │     );                                   │
│                                                │
│ [j/k] scroll [e] edit [n]ext file [p]revious  │
└────────────────────────────────────────────────┘
```

### Technical Implementation

**Git operations:**

```python
def commit_changes(ticket: Ticket, message: str, files: List[str]):
    """Execute git commit with selected files"""
    os.chdir(ticket.worktree_path)
    subprocess.run(["git", "add"] + files)
    subprocess.run(["git", "commit", "-m", message])
```

**Build triggering:**

```python
def trigger_build(ticket: Ticket):
    """Run build command and stream output"""
    # Read build command from .cc-control/config.yaml
    build_cmd = get_build_command(ticket)

    process = subprocess.Popen(
        build_cmd,
        cwd=ticket.worktree_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Stream output to TUI
    for line in process.stdout:
        yield line
```

### Deliverables

✅ Git commit dialog working  
✅ Push/pull operations working  
✅ Build triggering and progress display  
✅ Test execution from TUI  
✅ File diff preview  
✅ Keyboard shortcuts documented

---

## Phase 4: Todo List Management (2 weeks)

### Goal

Break tickets into trackable subtasks with progress visualization

### Key Features

#### 4.1 Todo List Structure

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

**Storage:** `~/.cc-control/<ticket-id>/todos.yaml`

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

#### 4.2 Todo Management UI

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

#### 4.3 Progress Visualization

**In list view:**

```
● IN-413  Public API bulk uploads    [████░░] 60%   Working
```

**Progress bar with details:**

```
Progress: [████████████░░░░░░░] 60%
3 done | 1 in progress | 1 not started
```

#### 4.4 Agent Assignment

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

### Deliverables

✅ Todo list data structure  
✅ Todo CRUD operations  
✅ Todo list display in TUI  
✅ Progress visualization  
✅ Task dependencies  
✅ Agent task assignment

---

## Phase 5: IDE Integration (2 weeks)

### Goal

Seamlessly connect to code editors for file viewing and editing

### Key Features

#### 5.1 Editor Detection

```python
def detect_editor() -> str:
    """Auto-detect user's preferred editor"""
    # Check environment variables
    if os.getenv("EDITOR"):
        return os.getenv("EDITOR")

    # Check for common editors
    editors = ["cursor", "code", "nvim", "vim", "nano"]
    for editor in editors:
        if shutil.which(editor):
            return editor

    return "vi"  # Fallback
```

#### 5.2 Cursor/VSCode Integration

```python
def open_in_cursor(file_path: str, line: int = None):
    """Open file in Cursor at specific line"""
    if line:
        subprocess.run(["cursor", "--goto", f"{file_path}:{line}"])
    else:
        subprocess.run(["cursor", file_path])
```

#### 5.3 Built-in Diff Viewer

- Uses `delta` for beautiful diffs
- Syntax highlighting
- Side-by-side or unified view
- Navigate between hunks

#### 5.4 File Tree Navigation

```
┌─ Changed Files: IN-413 ────────────────────────┐
│ src/                                           │
│ ├─● api/                                       │
│ │  ├─ M bulk-upload.ts           [e]dit       │
│ │  └─ M response.ts               [d]iff      │
│ ├─● validators/                                │
│ │  └─ M input.ts                               │
│ └─● types/                                     │
│    └─ A upload.d.ts               (new)       │
│ tests/                                         │
│ └─● api/                                       │
│    └─ M bulk-upload.test.ts                   │
│                                                │
│ M=modified A=added D=deleted                   │
│ [j/k] navigate [e]dit [d]iff [v]iew in IDE    │
└────────────────────────────────────────────────┘
```

### Deliverables

✅ Editor auto-detection  
✅ Open files in external editor  
✅ Built-in diff viewer with syntax highlighting  
✅ File tree navigation  
✅ Jump to specific lines

---

## Phase 6: Replanning & Communication (2 weeks)

### Goal

Enable dynamic plan adjustments and bidirectional agent communication

### Key Features

#### 6.1 Mini-Chat Interface

```
┌─ Chat: IN-413 ─────────────────────────────────┐
│ You:                                           │
│ Should we use Zod or Joi for validation?      │
│                                                │
│ Claude:                                        │
│ For this TypeScript project, I'd recommend    │
│ Zod because:                                   │
│ - Better TypeScript integration               │
│ - Automatic type inference                    │
│ - Smaller bundle size                         │
│                                                │
│ > █                                            │
│                                                │
│ [Enter] send [Esc] close [↑↓] scroll          │
└────────────────────────────────────────────────┘
```

#### 6.2 Agent Questions

Agents can post questions that appear in TUI:

```
┌─ Agent Questions: IN-413 ──────────────────────┐
│ ⚠ Agent-1 asked (2 minutes ago):              │
│                                                │
│ "Should I use Zod or Joi for input            │
│  validation? Both are available."             │
│                                                │
│ [r]eply [i]gnore [c]hat                       │
└────────────────────────────────────────────────┘
```

#### 6.3 Plan Revision

- Edit todo list inline
- Add/remove/reorder tasks
- Ask Claude to suggest revisions
- View revision history

### Deliverables

✅ Mini-chat interface  
✅ Claude API integration  
✅ Agent question notifications  
✅ Reply mechanism  
✅ Plan revision UI  
✅ Revision history

---

## Phase 7: API Testing Tools (2 weeks)

### Goal

Test API endpoints without leaving Command Center

### Key Features

#### 7.1 Request Library

```yaml
# ~/.cc-control/<ticket-id>/api-requests.yaml
requests:
  - name: "Valid bulk upload"
    method: POST
    url: http://localhost:3000/api/bulk-upload
    headers:
      Content-Type: application/json
    body: |
      {
        "items": [
          {"id": 1, "value": "test"}
        ]
      }
    expected_status: 200

  - name: "Invalid schema"
    method: POST
    url: http://localhost:3000/api/bulk-upload
    body: |
      {
        "invalid": "data"
      }
    expected_status: 400
```

#### 7.2 Request Builder

```
┌─ New API Request ──────────────────────────────┐
│ Name: Valid bulk upload                        │
│                                                │
│ Method: [POST ▼]  URL: http://localhost:3000  │
│         /api/bulk-upload                       │
│                                                │
│ Headers:                                       │
│ Content-Type: application/json                 │
│ [+ Add header]                                 │
│                                                │
│ Body:                                          │
│ ┌────────────────────────────────────────────┐ │
│ │ {                                          │ │
│ │   "items": [{"id": 1}]                    │ │
│ │ }                                          │ │
│ └────────────────────────────────────────────┘ │
│                                                │
│ [Enter] save [Ctrl-T] test now [Esc] cancel   │
└────────────────────────────────────────────────┘
```

#### 7.3 Response Viewer

```
┌─ Response: Valid bulk upload ──────────────────┐
│ Status: 200 OK                     Time: 234ms │
│                                                │
│ Headers:                                       │
│ Content-Type: application/json                 │
│ X-Request-ID: abc123                           │
│                                                │
│ Body:                                          │
│ {                                              │
│   "success": true,                             │
│   "processed": 1                               │
│ }                                              │
│                                                │
│ ✓ Status matches expected (200)                │
│                                                │
│ [Enter] close [s] save [e] edit request        │
└────────────────────────────────────────────────┘
```

### Deliverables

✅ Request library storage  
✅ Request builder UI  
✅ Execute requests  
✅ Response viewer with formatting  
✅ Request history  
✅ Assertions/validation

---

## Phase 8: Team Features (3 weeks)

### Goal

Enable collaboration and visibility across team members

### Key Features

#### 8.1 Shared State

- Tickets visible to team members
- Read-only views for non-assignees
- Activity feed of changes

#### 8.2 Ticket Assignment

```yaml
ticket:
  id: IN-413
  assigned_to: alice
  reviewers: [bob, charlie]
  watchers: [dave]
```

#### 8.3 Notifications

- Slack/Discord webhooks
- Email notifications
- In-TUI notifications

#### 8.4 State Synchronization

- Export ticket state to JSON
- Import on another machine
- Sync via git repo or shared storage

### Deliverables

✅ Multi-user ticket views  
✅ Assignment system  
✅ Notification integrations  
✅ State export/import  
✅ Activity feed

---

## Phase 9: Advanced Integrations (2 weeks)

### Goal

Connect to external tools and services

### Key Features

#### 9.1 Issue Tracker Sync

- Jira integration
- Linear integration
- GitHub Issues integration
- Two-way sync of ticket metadata

#### 9.2 Chat Integrations

- Slack notifications
- Discord webhooks
- Teams integration

#### 9.3 CI/CD Integration

- Trigger GitHub Actions
- View CircleCI status
- GitLab pipeline integration

#### 9.4 Plugin System

```python
# ~/.cc-control/plugins/custom_build.py
from ccc.plugin import Plugin

class CustomBuildPlugin(Plugin):
    def on_build_start(self, ticket):
        # Custom pre-build logic
        pass

    def on_build_complete(self, ticket, success):
        # Custom post-build logic
        pass
```

### Deliverables

✅ Jira/Linear/GitHub sync  
✅ Chat platform integrations  
✅ CI/CD status display  
✅ Plugin system API  
✅ Example plugins

---

## Phase 10: Polish & Optimization (2 weeks)

### Goal

Production-ready reliability, performance, and user experience

### Key Features

#### 10.1 Performance Optimization

- Profile and optimize hot paths
- Reduce memory usage
- Optimize polling intervals
- Cache expensive operations

#### 10.2 Error Recovery

- Graceful degradation
- Automatic retry logic
- Better error messages
- Recovery suggestions

#### 10.3 Configuration Management

- Per-project configs
- Project templates
- Config validation
- Migration tools

#### 10.4 Documentation

- Comprehensive user guide
- Video tutorials
- API documentation
- Architecture guide

#### 10.5 Distribution

- PyPI package
- Homebrew formula
- apt/yum packages
- Installer script

### Deliverables

✅ Sub-100ms TUI response  
✅ Handles 20+ tickets smoothly  
✅ Complete error recovery  
✅ Full documentation  
✅ Easy installation  
✅ Configuration wizard

---

## Cross-Phase Considerations

### Backward Compatibility

Each phase must maintain compatibility with previous phases:

- Old ticket formats still work
- Configs can be incrementally adopted
- Features degrade gracefully if unsupported

### Testing Strategy

- Unit tests for core logic
- Integration tests for workflows
- Manual testing checklist per phase
- Beta testing with real users

### Documentation Updates

Each phase requires:

- Updated README
- New feature guides
- Updated keyboard shortcuts
- Example configurations

### Performance Budgets

- TUI refresh: <100ms
- Git status query: <500ms
- Status file read: <50ms
- Total memory: <100MB
- CPU (idle): <1%

---

## Timeline Summary

| Phase | Weeks | Cumulative | Key Milestone       |
| ----- | ----- | ---------- | ------------------- |
| 1     | 3     | 3          | Core foundation     |
| 2     | 2     | 5          | Enhanced visibility |
| 3     | 2     | 7          | Developer actions   |
| 4     | 2     | 9          | Todo management     |
| 5     | 2     | 11         | IDE integration     |
| 6     | 2     | 13         | Replanning          |
| 7     | 2     | 15         | API testing         |
| 8     | 3     | 18         | Team features       |
| 9     | 2     | 20         | Integrations        |
| 10    | 2     | 22         | Production ready    |

**Total: 22 weeks (~5.5 months) to v1.0**

---

## Post-v1.0 Roadmap

### v1.1 - Enhanced Intelligence

- AI-powered insights
- Predictive completion times
- Anomaly detection
- Smart suggestions

### v1.2 - Cloud Sync

- Cloud state storage
- Multi-machine sync
- Team dashboards
- Mobile companion app

### v1.3 - Advanced Analytics

- Velocity tracking
- Bottleneck detection
- Agent performance metrics
- Custom reports

### v2.0 - Distributed Development

- Remote agent support
- Cloud-based agents
- Distributed builds
- Multi-repo coordination
