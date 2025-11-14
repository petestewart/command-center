# Phase Reference Cards - Quick Handoff Guide

**Purpose:** One-page summaries for quick agent handoff to any phase

---

## 📋 Phase 1: Status Bar System

### What You're Building
Always-visible status bar showing server, database, build, and test status with real-time health checks.

### Prerequisites
✅ None - This is the foundation phase

### Time Estimate
3-5 days

### Start Here
1. Create `ccc/status_monitor.py`
2. Create `ccc/tui/widgets/status_bar.py`
3. Extend `ccc/config.py`
4. Wire into `ccc/tui/app.py`

### Key Files
**Create:**
- `ccc/status_monitor.py` (StatusMonitor, LogPatternMatcher, ServerStatus, DatabaseStatus)
- `ccc/tui/widgets/__init__.py`
- `ccc/tui/widgets/status_bar.py` (StatusBar widget)

**Modify:**
- `ccc/config.py` (add server/database config fields)
- `ccc/tui/app.py` (add StatusBar to layout, integrate with polling)

### Implementation Order
```
1. status_monitor.py
   ├─ ServerStatus dataclass
   ├─ DatabaseStatus dataclass
   ├─ StatusBarState dataclass
   ├─ LogPatternMatcher class
   └─ StatusMonitor class

2. tui/widgets/status_bar.py
   └─ StatusBar widget (Textual Static)

3. config.py
   └─ Add server_command, database_connection_string, etc.

4. app.py
   ├─ Import StatusBar
   ├─ Add to compose()
   ├─ Initialize StatusMonitor in on_mount()
   ├─ Update _update_all_status() polling
   └─ Add action_start_server() / action_focus_server()
```

### Code Skeleton

```python
# ccc/status_monitor.py
from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import re
import requests
import threading
from ccc.build_runner import CommandRunner

@dataclass
class ServerStatus:
    state: str  # 'stopped', 'starting', 'healthy', 'unhealthy', 'error'
    url: Optional[str] = None
    port: Optional[int] = None
    error_message: Optional[str] = None
    last_check: Optional[datetime] = None

@dataclass
class DatabaseStatus:
    state: str  # 'stopped', 'connected', 'error'
    connection_string: Optional[str] = None
    error_message: Optional[str] = None
    last_check: Optional[datetime] = None

@dataclass
class StatusBarState:
    server: ServerStatus
    database: DatabaseStatus
    build: dict
    tests: dict

class LogPatternMatcher:
    SERVER_READY_PATTERNS = [
        r"Server listening on.*:(\d+)",
        r"Ready on http://.*:(\d+)",
    ]

    def extract_server_url(self, line: str) -> Optional[str]:
        # Parse line for server URL
        pass

    def is_error(self, line: str) -> bool:
        # Check if line is error
        pass

class StatusMonitor:
    def __init__(self, branch_name: str, config: dict):
        self.branch_name = branch_name
        self.config = config
        self.state_file = Path(f"~/.ccc-control/branches/{branch_name}/status-bar.json")
        self.server_runner: Optional[CommandRunner] = None

    def start_server(self) -> None:
        # Start server in tmux window 1
        command = self.config.get('server_command', 'npm run dev')
        self.server_runner = CommandRunner(
            command=command,
            on_output=self._handle_server_output,
            on_complete=self._handle_server_complete
        )
        self.server_runner.start()

    def check_server_health(self) -> None:
        # HTTP health check (async, non-blocking)
        def _check():
            try:
                response = requests.get(self.server_url, timeout=2)
                self._update_server_status(
                    state='healthy' if response.status_code == 200 else 'unhealthy'
                )
            except:
                self._update_server_status(state='unhealthy')

        threading.Thread(target=_check, daemon=True).start()

    def load_status(self) -> StatusBarState:
        # Load from file
        pass

    def save_status(self, status: StatusBarState) -> None:
        # Save to file (atomic write)
        pass
```

```python
# ccc/tui/widgets/status_bar.py
from textual.widgets import Static
from textual.reactive import reactive
from rich.text import Text

class StatusBar(Static):
    status = reactive({})

    def watch_status(self, status: dict) -> None:
        self.update(self._render_status(status))

    def _render_status(self, status: dict) -> Text:
        text = Text()

        # Render server, database, tests, build
        server = status.get('server', {})
        server_icon = self._get_status_icon(server.get('state', 'stopped'))
        text.append(f"SERVER: {server_icon} {server.get('url', 'N/A')}  ")

        # ... (database, tests, build)

        return text

    def _get_status_icon(self, state: str) -> str:
        icons = {
            'healthy': '●', 'connected': '●',
            'starting': '◐', 'unhealthy': '◐',
            'error': '✗', 'stopped': '○',
        }
        return icons.get(state, '?')
```

### Configuration
```python
# ccc/config.py additions
@dataclass
class Config:
    # ... existing fields ...

    # Server
    server_command: str = "npm run dev"
    server_health_check_url: Optional[str] = None
    server_health_check_interval: int = 10

    # Database
    database_type: str = "postgresql"
    database_connection_string: str = "postgresql://localhost:5432/mydb"
    database_health_check_interval: int = 30
```

### Success Criteria
- [ ] Status bar visible at bottom of screen
- [ ] Server button starts server in tmux window 1
- [ ] Server status updates (stopped → starting → healthy)
- [ ] Health checks run every 10s without blocking UI
- [ ] Database status shows connection state
- [ ] Build/Test status integrated from existing files
- [ ] Clicking status indicators focuses tmux windows
- [ ] Tests pass

### Common Pitfalls
- ❌ Blocking UI thread with health checks → Use threading
- ❌ Not handling tmux window not existing → Check before accessing
- ❌ Hardcoding server patterns → Make configurable

### Testing
```python
# tests/test_status_monitor.py
def test_log_pattern_matcher():
    matcher = LogPatternMatcher()
    url = matcher.extract_server_url("Server listening on :3000")
    assert url == "http://localhost:3000"

def test_status_monitor_start_server():
    monitor = StatusMonitor("test-branch", config)
    monitor.start_server()
    # Assert server_runner is created
```

---

## 📋 Phase 2: External Tool Launchers

### What You're Building
Quick-launch buttons for IDE (Cursor), Git UI (lazygit), browser, database client (TablePlus).

### Prerequisites
✅ Phase 1 complete (uses status bar for server/db access)

### Time Estimate
2-3 days

### Start Here
1. Create `ccc/external_tools.py`
2. Create `ccc/tui/widgets/button_bar.py`
3. Extend `ccc/config.py`
4. Wire into `ccc/tui/app.py`

### Key Implementation Notes
- **Git UI:** Temporary window (create fresh each time, closes on exit)
- **IDE:** Default to Cursor, fallback to $EDITOR
- **Database:** Launch TablePlus with PostgreSQL connection
- **URLs:** Platform-specific opening (macOS: open, Linux: xdg-open)

### Key Files
**Create:**
- `ccc/external_tools.py` (ExternalToolLauncher)
- `ccc/tui/widgets/button_bar.py` (ButtonBar widget)

**Modify:**
- `ccc/config.py` (add tool configuration)
- `ccc/tui/app.py` (add ButtonBar, action handlers)

### Code Skeleton
```python
# ccc/external_tools.py
import subprocess
import sys
import shutil
from pathlib import Path

class ExternalToolLauncher:
    def __init__(self, config: dict, session_manager):
        self.config = config
        self.session_manager = session_manager

    def launch_ide(self, file_path: str) -> None:
        ide_command = self.config.get('ide_command', 'cursor')

        if shutil.which(ide_command):
            subprocess.Popen([ide_command, file_path])
        else:
            # Fallback to $EDITOR
            editor = os.environ.get('EDITOR', 'vim')
            subprocess.Popen([editor, file_path])

    def launch_git_ui(self) -> None:
        # Create temporary tmux window
        window = self.session_manager.new_window(
            window_name='git',
            command='lazygit'
        )
        # Window closes when lazygit exits (temporary mode)

    def open_url(self, url: str) -> None:
        if sys.platform == 'darwin':
            subprocess.Popen(['open', url])
        elif sys.platform == 'linux':
            subprocess.Popen(['xdg-open', url])
```

### Success Criteria
- [ ] Plan/Notes buttons open files in Cursor
- [ ] Git button launches lazygit in temporary tmux window
- [ ] API/Jira buttons open URLs in browser
- [ ] Database button launches TablePlus
- [ ] All keyboard shortcuts work
- [ ] Platform detection works (macOS/Linux)

---

## 📋 Phase 3: Multi-Agent Tracking

### What You're Building
Track multiple concurrent Claude agents with TODO parsing, progress tracking, and terminal focus.

### Prerequisites
✅ Phase 1 complete

### Time Estimate
5-7 days

### Start Here
1. Extend `ccc/status.py` (add AgentSession, AgentTodo)
2. Create `ccc/multi_agent_manager.py` (TodoParser, MultiAgentManager)
3. Create `ccc/tui/widgets/agent_card.py`
4. Create `ccc/tui/widgets/agents_pane.py`
5. Modify `ccc/claude_chat.py` (register sessions)
6. Wire into `ccc/tui/app.py`

### ⚠️ HIGH RISK: TODO Parsing
This is the most fragile part. Support multiple formats:
```
✓ Task completed
- [ ] Task pending
- [x] Task completed
* Task pending
○ Task pending
✗ Task blocked
```

### Key Files
**Create:**
- `ccc/multi_agent_manager.py`
- `ccc/tui/widgets/agent_card.py`
- `ccc/tui/widgets/agents_pane.py`

**Modify:**
- `ccc/status.py` (add AgentSession, AgentTodo dataclasses)
- `ccc/claude_chat.py` (register sessions with manager)
- `ccc/tui/app.py` (integrate AgentsPane)

### Code Skeleton
```python
# ccc/status.py additions
@dataclass
class AgentTodo:
    text: str
    completed: bool
    blocked: bool = False

@dataclass
class AgentSession:
    id: str
    todo_id: Optional[str]
    title: str
    status: str  # 'idle', 'working', 'waiting', 'completed', 'error'
    current_files: List[str] = field(default_factory=list)
    progress_percent: Optional[int] = None
    todo_list: List[AgentTodo] = field(default_factory=list)
    terminal_ref: Optional[str] = None  # Tmux pane ID
    started_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
```

```python
# ccc/multi_agent_manager.py
class TodoParser:
    TODO_PATTERNS = {
        'completed': [
            r'[✓✅]\s*(.*)',
            r'\[x\]\s*(.*)',
            r'\* \[x\]\s*(.*)',
        ],
        'pending': [
            r'[-⚬○]\s*(.*)',
            r'\[ \]\s*(.*)',
        ],
        'blocked': [
            r'[✗❌]\s*(.*)',
        ]
    }

    def parse_todo_list(self, text: str) -> List[AgentTodo]:
        todos = []
        for line in text.split('\n'):
            # Try each pattern
            for status, patterns in self.TODO_PATTERNS.items():
                for pattern in patterns:
                    match = re.match(pattern, line.strip())
                    if match:
                        todos.append(AgentTodo(
                            text=match.group(1),
                            completed=(status == 'completed'),
                            blocked=(status == 'blocked')
                        ))
                        break
        return todos
```

### State File
```json
// ~/.ccc-control/branches/{branch}/agent-sessions.json
{
  "sessions": [
    {
      "id": "abc123",
      "title": "Setup Postman Auth",
      "status": "working",
      "progress_percent": 45,
      "todo_list": [
        {"text": "Generate API key", "completed": true, "blocked": false},
        {"text": "Add to GitHub secrets", "completed": false, "blocked": false}
      ],
      "terminal_ref": "ccc-branch:0.1",
      "started_at": "2025-11-14T10:00:00"
    }
  ]
}
```

### Success Criteria
- [ ] Multiple agent cards display
- [ ] TODOs parsed from multiple formats
- [ ] Progress calculated from TODO completion
- [ ] Open button focuses agent's tmux pane
- [ ] Archive button removes session
- [ ] State persists across CCC restarts
- [ ] Handles malformed TODO output gracefully

---

## 📋 Phase 4: Tasks Pane

### What You're Building
Display project TASKS.md file with auto-reload and checkbox rendering.

### Prerequisites
✅ None (independent)

### Time Estimate
2-3 days

### Key Implementation Notes
- **Read-Only:** Tasks not editable from CCC
- **Auto-Reload:** Watch TASKS.md for file changes
- **Format:** Standard markdown `- [ ]` and `- [x]`
- **Nesting:** Support 2-space indentation

### Code Skeleton
```python
# ccc/tasks_manager.py
@dataclass
class Task:
    text: str
    completed: bool
    indent_level: int = 0

class TasksManager:
    def __init__(self, tasks_file: str = "TASKS.md"):
        self.tasks_file = Path(tasks_file)
        self.watcher = None  # File watcher for auto-reload

    def load_tasks(self) -> List[Task]:
        if not self.tasks_file.exists():
            return []

        with open(self.tasks_file) as f:
            content = f.read()

        return self._parse_markdown_tasks(content)

    def _parse_markdown_tasks(self, content: str) -> List[Task]:
        tasks = []
        checkbox_pattern = r'^(\s*)[-*]\s+\[([ xX])\]\s+(.*)$'

        for line in content.split('\n'):
            match = re.match(checkbox_pattern, line)
            if match:
                indent = len(match.group(1))
                completed = match.group(2).lower() == 'x'
                text = match.group(3)

                tasks.append(Task(
                    text=text,
                    completed=completed,
                    indent_level=indent // 2
                ))

        return tasks
```

### Success Criteria
- [ ] Tasks display from TASKS.md
- [ ] Checkboxes render correctly
- [ ] Nested tasks show indentation
- [ ] File changes auto-reload (within 3s)
- [ ] Toggle action works
- [ ] Handle file not found gracefully

---

## 📋 Phase 5: Layout Refactoring

### What You're Building
Dynamic pane toggling with responsive grid layout.

### Prerequisites
✅ Phases 2, 3, 4 complete

### Time Estimate
2-3 days

### Key Changes
**From:**
```python
CSS = """
Screen {
    layout: horizontal;
}
"""
```

**To:**
```python
CSS = """
Screen {
    layout: grid;
    grid-size: 2 4;
    grid-rows: auto 1fr auto auto;
}

.pane {
    display: none;
}

.pane.visible {
    display: block;
}
"""
```

### Success Criteria
- [ ] Tasks pane visible by default
- [ ] Only one pane visible at time
- [ ] Ticket list always visible
- [ ] Active button highlighted
- [ ] Works at 80x24 minimum
- [ ] Works at 200x60 large
- [ ] No flickering during transitions

---

## 📋 Phase 6: Polish & Documentation

### What You're Building
Help overlay, error handling, testing, documentation.

### Time Estimate
2-3 days

### Deliverables
- Help dialog (`?` key)
- Complete keyboard shortcuts
- Comprehensive error handling
- All tests passing
- Documentation complete

### Success Criteria
- [ ] Help overlay accessible
- [ ] All shortcuts work and documented
- [ ] Error messages clear and helpful
- [ ] No critical bugs
- [ ] Test coverage > 80%
- [ ] Ready for user testing

---

## Quick Troubleshooting

### "Can't import StatusMonitor"
→ Check `ccc/status_monitor.py` exists and has no syntax errors

### "Tmux window doesn't exist"
→ Check session has 3 windows (agent:0, server:1, tests:2)

### "Health checks blocking UI"
→ Ensure using threading.Thread with daemon=True

### "TODO parsing not working"
→ Check log output format, add pattern to config

### "Layout broken on small terminal"
→ Add minimum size check in on_mount()

---

*Reference: See IMPLEMENTATION_PLAN.md for complete details*
