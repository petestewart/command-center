# CCC Restructure Implementation Plan

## Phase 1: Validation & Planning ✅

### Validation Results

**✅ Codebase Structure Confirmed:**
- app.py: 1297 lines (matches design doc)
- Tmux integration: 3 windows per ticket (agent:0, server:1, tests:2)
- CommandRunner: Subprocess execution with streaming output
- State management: File-based JSON/YAML in ~/.ccc-control/branches/{branch}/
- Polling: 3-second interval already implemented

**✅ Current File Structure:**
```
ccc/
├── cli.py                  ✅ Entry point
├── tui/
│   ├── app.py              ✅ 1297 lines (monolithic)
│   ├── widgets.py          ✅ Existing widgets
│   ├── dialogs.py          ✅ Existing dialogs
│   ├── chat_widgets.py     ✅ Chat components
│   └── api_widgets.py      ✅ API components
├── status.py               ✅ AgentStatus dataclass
├── session.py              ✅ TmuxSessionManager
├── build_runner.py         ✅ CommandRunner
├── config.py               ✅ Configuration
├── todo.py                 ✅ TodoItem/TodoList
├── claude_chat.py          ✅ Claude integration
└── [other modules]         ✅ Existing
```

**✅ Tmux Windows Current Usage:**
- Window 0 (agent): ✅ Active - Claude sessions run here
- Window 1 (server): ⚠️  Created but idle - ready for server processes
- Window 2 (tests): ⚠️  Created but idle - ready for test processes

**✅ Agent Launching:**
- `action_start_session()` in app.py launches Claude
- Currently single-agent only
- Sessions tracked in claude-sessions.yaml
- Attaches to tmux window 0 (agent)

**✅ Build/Test Execution:**
- Uses CommandRunner with callbacks
- Displays in OutputDialog (not using tmux windows)
- Saves results to build-status.json and test-status.json

---

## Phase 2: Detailed Implementation Plan

### Overview
Transform CCC from single-agent ticket viewer into multi-agent project orchestrator by:
1. Adding persistent status bar with health monitoring
2. Adding external tool launchers via button bar
3. Enhancing single-agent to multi-agent tracking
4. Adding tasks pane for project TODO list
5. Refactoring layout to support toggleable panes
6. Polish and documentation

### Implementation Phases

---

## **PHASE 1: Status Bar System** (3-5 days)

### Prerequisites
- None (foundation phase)

### Goals
- Always-visible status bar showing server, database, build, test status
- Health checks for services without blocking UI
- Leverage existing tmux windows and polling infrastructure

### Tasks

#### 1.1 Create status_monitor.py (2 days)
**Files to Create:**
- `ccc/status_monitor.py`

**Components:**
```python
@dataclass
class ServerStatus:
    state: str  # 'stopped', 'starting', 'healthy', 'unhealthy', 'error'
    url: Optional[str]
    port: Optional[int]
    error_message: Optional[str]
    last_check: Optional[datetime]
    uptime: Optional[float]

@dataclass
class DatabaseStatus:
    state: str  # 'stopped', 'connected', 'error'
    connection_string: Optional[str]
    error_message: Optional[str]
    last_check: Optional[datetime]

@dataclass
class StatusBarState:
    server: ServerStatus
    database: DatabaseStatus
    build: dict  # Reuse existing build-status.json
    tests: dict  # Reuse existing test-status.json

class LogPatternMatcher:
    """Parse subprocess output for status patterns"""
    - extract_server_url(line) -> Optional[str]
    - is_error(line) -> bool

class StatusMonitor:
    """Monitor server, database, build, test status"""
    - start_server() -> None
    - check_server_health() -> None
    - check_database_connection() -> None
    - load_status() -> StatusBarState
    - save_status(status) -> None
```

**Dependencies:**
- Reuse `CommandRunner` from build_runner.py
- Reuse tmux window management from session.py
- Read existing build-status.json and test-status.json

#### 1.2 Create StatusBar widget (1 day)
**Files to Create:**
- `ccc/tui/widgets/status_bar.py`

**Components:**
```python
class StatusBar(Static):
    status = reactive({})

    - watch_status(status: dict) -> None
    - _render_status(status: dict) -> Text
    - _get_status_icon(state: str) -> str
    - _get_status_style(state: str) -> str
    - on_click() -> None  # Focus relevant terminal
```

**Layout Integration:**
- Add to app.py compose()
- Place above Footer, below main content
- Height: 3 lines

#### 1.3 Extend config.py (0.5 days)
**Files to Modify:**
- `ccc/config.py`

**New Config Fields:**
```python
@dataclass
class Config:
    # ... existing fields ...

    # Server configuration
    server_command: str = "npm run dev"
    server_health_check_url: Optional[str] = None
    server_health_check_interval: int = 10
    server_ready_patterns: List[str] = field(default_factory=lambda: [
        r"Server listening on :?(\d+)",
        r"Ready on http://([\w:.]+)"
    ])
    server_error_patterns: List[str] = field(default_factory=lambda: [
        r"^ERROR", r"EADDRINUSE", r"Fatal"
    ])

    # Database configuration
    database_type: str = "postgresql"
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "mydb_dev"
    database_connection_string: Optional[str] = None
    database_health_check_interval: int = 30
```

#### 1.4 Wire into app.py (1 day)
**Files to Modify:**
- `ccc/tui/app.py`

**Changes:**
```python
# Add imports
from ccc.status_monitor import StatusMonitor
from ccc.tui.widgets.status_bar import StatusBar

class CommandCenterTUI(App):
    # Add field
    status_monitor: Optional[StatusMonitor] = None

    def compose(self):
        yield Header()
        with Horizontal():
            # ... existing layout ...
        yield StatusBar(id="status_bar")  # NEW
        yield Footer()

    def on_mount(self):
        # ... existing code ...

        # Initialize status monitor
        if self.selected_ticket_id:
            ticket = self.registry.get(self.selected_ticket_id)
            if ticket:
                self.status_monitor = StatusMonitor(
                    branch_name=ticket.branch,
                    config=load_config()
                )

        # Add to existing poll
        self.set_interval(3, self._update_all_status)

    def _update_all_status(self):
        """Existing 3s poll + status bar update"""
        # ... existing refresh logic ...

        # Update status bar
        if self.status_monitor:
            status = self.status_monitor.load_status()
            status_bar = self.query_one("#status_bar", StatusBar)
            status_bar.status = asdict(status)

            # Perform health checks
            if self.status_monitor.server_runner:
                self.status_monitor.check_server_health()
            self.status_monitor.check_database_connection()

    def action_start_server(self):
        """New action to start server"""
        if self.status_monitor:
            self.status_monitor.start_server()

    def action_focus_server(self):
        """Focus server terminal (tmux window 1)"""
        ticket = self._get_selected_ticket()
        if ticket:
            manager = TmuxSessionManager()
            manager.attach_to_window(ticket.tmux_session, "server")
```

#### 1.5 Testing (0.5 days)
- [ ] Status bar visible and updates
- [ ] Server process starts in tmux window 1
- [ ] Health checks detect server ready
- [ ] Health checks detect server errors
- [ ] Database connection checks work
- [ ] Build/Test status integrated
- [ ] No performance degradation

### Deliverables
- ✅ Status bar always visible
- ✅ Server status reflects process state
- ✅ Health checks run without blocking UI
- ✅ Database connection status accurate
- ✅ Clicking status focuses tmux window

### Files Created
- `ccc/status_monitor.py` (new)
- `ccc/tui/widgets/` (new directory)
- `ccc/tui/widgets/__init__.py` (new)
- `ccc/tui/widgets/status_bar.py` (new)

### Files Modified
- `ccc/config.py` (extend Config dataclass)
- `ccc/tui/app.py` (add StatusBar widget, integrate monitoring)

---

## **PHASE 2: External Tool Launchers** (2-3 days)

### Prerequisites
- Phase 1 complete (uses status bar for server/db access)

### Goals
- Quick-launch buttons for external tools
- Support IDE, Git UI, browser, database client
- Keyboard shortcuts for all tools

### Tasks

#### 2.1 Create external_tools.py (1 day)
**Files to Create:**
- `ccc/external_tools.py`

**Components:**
```python
class ExternalToolLauncher:
    """Launch external tools from CCC"""

    def __init__(self, config: dict, session_manager: TmuxSessionManager)

    # Tool launchers
    def launch_ide(self, file_path: str) -> None
    def launch_git_ui(self) -> None  # lazygit in new tmux window
    def launch_database_client(self) -> None  # TablePlus, DBeaver
    def open_url(self, url: str) -> None
    def open_jira_ticket(self, ticket_id: str) -> None
    def open_api_docs(self) -> None
```

**Implementation Notes:**
- Reuse subprocess patterns from build_runner.py
- Git UI creates new tmux window, tracks window ID
- Database client gets connection string from config
- Browser opening: platform-specific (open/xdg-open/start)

#### 2.2 Create ButtonBar widget (0.5 days)
**Files to Create:**
- `ccc/tui/widgets/button_bar.py`

**Components:**
```python
class ButtonBar(Static):
    active_pane = reactive(None)

    def compose(self):
        with Horizontal():
            # Pane toggles
            yield Button("Tasks", id="btn_tasks", variant="primary")
            yield Button("Agents", id="btn_agents", variant="primary")
            yield Static("│")

            # External launchers
            yield Button("Plan", id="btn_plan")
            yield Button("Git", id="btn_git")
            yield Button("API", id="btn_api")
            yield Button("Notes", id="btn_notes")
            yield Static("│")

            # Status actions
            yield Button("Server", id="btn_server")
            yield Button("Database", id="btn_database")
            yield Button("Build", id="btn_build")
            yield Button("Tests", id="btn_tests")
            yield Button("Jira", id="btn_jira")

    def on_button_pressed(self, event):
        self.post_message(self.ButtonClicked(event.button.id))

    class ButtonClicked(Message):
        def __init__(self, button_id: str)
```

#### 2.3 Wire into app.py (0.5 days)
**Files to Modify:**
- `ccc/tui/app.py`

**Changes:**
```python
from ccc.external_tools import ExternalToolLauncher
from ccc.tui.widgets.button_bar import ButtonBar

class CommandCenterTUI(App):
    tool_launcher: Optional[ExternalToolLauncher] = None

    BINDINGS = [
        # ... existing bindings ...
        ("p", "open_plan", "Open Plan"),
        ("g", "open_git", "Git UI"),
        ("shift+n", "open_notes", "Notes"),
        ("j", "open_jira", "Jira"),
        ("d", "open_api_docs", "API Docs"),
        ("s", "focus_server", "Server"),
        ("b", "run_build", "Build"),
        ("shift+t", "run_tests", "Tests"),
    ]

    def compose(self):
        yield Header()
        with Horizontal():
            # ... existing layout ...
        yield StatusBar(id="status_bar")
        yield ButtonBar(id="button_bar")  # NEW
        yield Footer()

    def on_mount(self):
        # ... existing code ...
        self.tool_launcher = ExternalToolLauncher(
            config=load_config(),
            session_manager=TmuxSessionManager()
        )

    def on_button_bar_button_clicked(self, event):
        handlers = {
            'btn_plan': self.action_open_plan,
            'btn_git': self.action_open_git,
            'btn_api': self.action_open_api_docs,
            # ... etc
        }
        handler = handlers.get(event.button_id)
        if handler:
            handler()

    # Action handlers
    def action_open_plan(self):
        plan_file = self.config.get('files.plan', 'PLAN.md')
        self.tool_launcher.launch_ide(plan_file)

    def action_open_git(self):
        self.tool_launcher.launch_git_ui()

    # ... etc
```

#### 2.4 Extend config.py (0.5 days)
**Files to Modify:**
- `ccc/config.py`

**New Fields:**
```python
@dataclass
class Config:
    # ... existing ...

    # Tool configuration
    ide_command: str = "cursor"
    ide_args: List[str] = field(default_factory=list)
    git_ui_command: str = "lazygit"
    git_ui_args: List[str] = field(default_factory=list)
    db_client_command: str = "open"
    db_client_args: List[str] = field(default_factory=lambda: ["-a", "TablePlus"])

    # URL configuration
    jira_base_url: str = ""
    api_docs_url: str = ""

    # File paths
    plan_file: str = "PLAN.md"
    notes_file: str = "NOTES.md"
    tasks_file: str = "TASKS.md"
```

#### 2.5 Testing (0.5 days)
- [ ] Plan/Notes buttons open in IDE
- [ ] Git button launches lazygit in tmux
- [ ] Second Git press focuses existing window
- [ ] API/Jira buttons open URLs
- [ ] Database button launches client
- [ ] All keyboard shortcuts work
- [ ] Configuration respected

### Deliverables
- ✅ Button bar visible and functional
- ✅ All tool launchers work
- ✅ Git UI in tracked tmux window
- ✅ Keyboard shortcuts implemented

### Files Created
- `ccc/external_tools.py` (new)
- `ccc/tui/widgets/button_bar.py` (new)

### Files Modified
- `ccc/config.py` (extend Config)
- `ccc/tui/app.py` (add ButtonBar, actions)

---

## **PHASE 3: Multi-Agent Tracking** (5-7 days)

### Prerequisites
- Phase 1 complete (uses existing infrastructure)

### Goals
- Track multiple concurrent Claude agents
- Parse TODO lists from agent output
- Display agent cards with progress
- Focus/archive agents

### Tasks

#### 3.1 Enhance status.py data models (0.5 days)
**Files to Modify:**
- `ccc/status.py`

**New Models:**
```python
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
    error_message: Optional[str] = None
```

**Keep existing AgentStatus for backward compatibility**

#### 3.2 Create multi_agent_manager.py (2 days)
**Files to Create:**
- `ccc/multi_agent_manager.py`

**Components:**
```python
class TodoParser:
    """Parse Claude's TODO output"""

    TODO_PATTERNS = {
        'completed': r'[✓✅]\s*(.*)',
        'pending': r'[-⚬○]\s*(.*)',
        'blocked': r'[✗❌]\s*(.*)',
    }

    def parse_todo_list(self, text: str) -> List[AgentTodo]

class MultiAgentManager:
    """Manage multiple Claude agent sessions"""

    def __init__(self, branch_name: str)

    # Session management
    def list_sessions(self) -> List[AgentSession]
    def add_session(self, session: AgentSession) -> None
    def update_session(self, session_id: str, **kwargs) -> None
    def remove_session(self, session_id: str) -> None

    # TODO tracking
    def update_todos_from_output(self, session_id: str, output: str) -> None
    def calculate_progress(self, session: AgentSession) -> int

    # Internal
    def _extract_todo_section(self, output: str) -> Optional[str]
    def _save_sessions(self, sessions: List[AgentSession]) -> None
```

**State File:**
- `~/.ccc-control/branches/{branch}/agent-sessions.json`

#### 3.3 Create AgentCard widget (1 day)
**Files to Create:**
- `ccc/tui/widgets/agent_card.py`

**Components:**
```python
class AgentCard(Static):
    """Display card for individual agent session"""

    def __init__(self, session: AgentSession, **kwargs)

    def compose(self):
        with Vertical():
            # Header: emoji + title + progress
            yield Static(self._render_header())

            # Current files
            yield Static(self._render_files())

            # TODO list
            yield Static(self._render_todos())

            # Actions
            with Horizontal():
                yield Button("Open", id=f"open_{self.session.id}")
                yield Button("Archive", id=f"archive_{self.session.id}")

    def _render_header(self) -> Text
    def _render_files(self) -> Text
    def _render_todos(self) -> Text
    def _render_progress_bar(self, percent: int) -> str
    def _get_status_emoji(self, status: str) -> str
```

#### 3.4 Create AgentsPane widget (1 day)
**Files to Create:**
- `ccc/tui/widgets/agents_pane.py`

**Components:**
```python
class AgentsPane(Static):
    """Container for multiple agent cards"""

    def __init__(self, agent_manager: MultiAgentManager, **kwargs)

    def compose(self):
        yield Static("Active Agents", id="agents_header")
        yield Button("+ New Agent", id="new_agent_btn")
        yield ScrollableContainer(id="agents_list")

    def refresh_agents(self) -> None

    def on_button_pressed(self, event):
        # Handle Open/Archive/New Agent buttons

    class NewAgentRequested(Message): pass
    class OpenAgentRequested(Message): pass
    class ArchiveAgentRequested(Message): pass
```

#### 3.5 Wire into app.py (1 day)
**Files to Modify:**
- `ccc/tui/app.py`

**Changes:**
```python
from ccc.multi_agent_manager import MultiAgentManager
from ccc.tui.widgets.agents_pane import AgentsPane

class CommandCenterTUI(App):
    agent_manager: Optional[MultiAgentManager] = None

    def on_mount(self):
        # ... existing code ...

        if self.selected_ticket_id:
            ticket = self.registry.get(self.selected_ticket_id)
            if ticket:
                self.agent_manager = MultiAgentManager(
                    branch_name=ticket.branch
                )

        # Add to polling
        self.set_interval(3, self._update_agents)

    def _update_agents(self):
        """Update agent display (called every 3s)"""
        if self.agent_manager:
            agents_pane = self.query_one(AgentsPane)
            agents_pane.refresh_agents()

    def on_agents_pane_new_agent_requested(self, event):
        # Reuse existing action_start_session logic
        self.action_start_session()

    def on_agents_pane_open_agent_requested(self, event):
        # Focus tmux pane
        sessions = self.agent_manager.list_sessions()
        for session in sessions:
            if session.id == event.session_id and session.terminal_ref:
                # Use libtmux to focus pane
                pass

    def on_agents_pane_archive_agent_requested(self, event):
        self.agent_manager.remove_session(event.session_id)
```

#### 3.6 Integrate with claude_chat.py (1 day)
**Files to Modify:**
- `ccc/claude_chat.py`

**Changes:**
- Register new sessions with MultiAgentManager on launch
- Stream agent output to MultiAgentManager for TODO parsing
- Update session status on events

```python
# In ClaudeChat or relevant function
from ccc.multi_agent_manager import MultiAgentManager

def start_claude_session(branch_name: str, todo_item: TodoItem):
    # ... existing code ...

    # Register with multi-agent manager
    agent_manager = MultiAgentManager(branch_name)
    session = AgentSession(
        id=session_id,
        todo_id=str(todo_item.id) if todo_item else None,
        title=todo_item.description if todo_item else "General session",
        status='working',
        terminal_ref=pane_id,
        started_at=datetime.now()
    )
    agent_manager.add_session(session)

    # ... rest of existing code ...
```

#### 3.7 Testing (1 day)
- [ ] Multiple agent cards display
- [ ] TODO lists parsed from agent output
- [ ] Progress bars update
- [ ] Open button focuses correct tmux pane
- [ ] Archive button removes session
- [ ] New Agent button launches session
- [ ] State persists across CCC restarts

### Deliverables
- ✅ Multi-agent cards display simultaneously
- ✅ Each card shows title, files, progress, TODOs
- ✅ TODO parsing from agent output
- ✅ Focus/archive functionality
- ✅ Persistent state

### Files Created
- `ccc/multi_agent_manager.py` (new)
- `ccc/tui/widgets/agent_card.py` (new)
- `ccc/tui/widgets/agents_pane.py` (new)

### Files Modified
- `ccc/status.py` (add AgentSession, AgentTodo)
- `ccc/tui/app.py` (integrate AgentsPane)
- `ccc/claude_chat.py` (register sessions)

---

## **PHASE 4: Tasks Pane** (2-3 days)

### Prerequisites
- None (independent feature)

### Goals
- Display project task list from TASKS.md
- Parse markdown checkboxes
- Show completion status
- Toggleable display

### Tasks

#### 4.1 Create tasks_manager.py (1 day)
**Files to Create:**
- `ccc/tasks_manager.py`

**Components:**
```python
@dataclass
class Task:
    text: str
    completed: bool
    indent_level: int = 0

class TasksManager:
    """Manage project task list"""

    def __init__(self, tasks_file: str = "TASKS.md")

    def load_tasks(self) -> List[Task]
    def _parse_markdown_tasks(self, content: str) -> List[Task]
    def toggle_task(self, task_index: int) -> None  # Optional
    def _save_tasks(self, tasks: List[Task]) -> None  # Optional
```

**Markdown Format:**
```markdown
- [ ] Not completed
- [x] Completed
  - [ ] Nested task (2 space indent)
```

#### 4.2 Create TasksPane widget (1 day)
**Files to Create:**
- `ccc/tui/widgets/tasks_pane.py`

**Components:**
```python
class TasksPane(Static):
    """Display project task list"""

    def __init__(self, tasks_manager: TasksManager, **kwargs)

    def compose(self):
        yield Static("Project Tasks", id="tasks_header")
        yield ScrollableContainer(id="tasks_list")

    def refresh_tasks(self) -> None
    def _render_task(self, task: Task) -> Text
```

**Rendering:**
- Completed: `✓ Task` (dim, strikethrough)
- Pending: `⚬ Task` (normal)
- Indentation: 2 spaces per level

#### 4.3 Wire into app.py (0.5 days)
**Files to Modify:**
- `ccc/tui/app.py`

**Changes:**
```python
from ccc.tasks_manager import TasksManager
from ccc.tui.widgets.tasks_pane import TasksPane

class CommandCenterTUI(App):
    tasks_manager: Optional[TasksManager] = None
    tasks_pane_visible: bool = False

    BINDINGS = [
        # ... existing ...
        ("t", "toggle_tasks", "Tasks"),
        ("a", "toggle_agents", "Agents"),  # Change from "a" for API
    ]

    def on_mount(self):
        # ... existing code ...

        config = load_config()
        tasks_file = config.tasks_file  # "TASKS.md"
        self.tasks_manager = TasksManager(tasks_file)

    def action_toggle_tasks(self):
        """Toggle tasks pane visibility"""
        if self.tasks_pane_visible:
            self.tasks_pane_visible = False
        else:
            self.tasks_pane_visible = True
        # Layout update handled in Phase 5
```

#### 4.4 Testing (0.5 days)
- [ ] Tasks display from TASKS.md
- [ ] Checkboxes show correctly
- [ ] Nested tasks indent properly
- [ ] Toggle works (after Phase 5)
- [ ] File not found handled gracefully

### Deliverables
- ✅ Tasks pane displays TASKS.md
- ✅ Checkboxes reflect completion
- ✅ Nested tasks render with indentation
- ✅ Toggle action implemented

### Files Created
- `ccc/tasks_manager.py` (new)
- `ccc/tui/widgets/tasks_pane.py` (new)

### Files Modified
- `ccc/tui/app.py` (add TasksPane, toggle action)
- `ccc/config.py` (add tasks_file field)

---

## **PHASE 5: Layout Refactoring** (2-3 days)

### Prerequisites
- Phase 3 complete (AgentsPane exists)
- Phase 4 complete (TasksPane exists)

### Goals
- Dynamic pane toggling (Tasks/Agents/None)
- Maintain ticket list visibility
- Smooth transitions
- Responsive layout

### Tasks

#### 5.1 Update CSS layout (1 day)
**Files to Modify:**
- `ccc/tui/app.py`

**Current CSS:**
```python
CSS = """
Screen {
    layout: horizontal;
}

#ticket-list-container {
    width: 50%;
}

#detail-container {
    width: 50%;
}
"""
```

**New CSS:**
```python
CSS = """
Screen {
    layout: grid;
    grid-size: 2 4;  /* 2 columns, 4 rows */
    grid-rows: auto 1fr auto auto;
}

#header {
    column-span: 2;
    row-span: 1;
}

#ticket-list-container {
    column-span: 1;
    row-span: 2;
}

#pane-container {
    column-span: 1;
    row-span: 2;
}

#status-bar {
    column-span: 2;
    row-span: 1;
    height: 3;
}

#button-bar {
    column-span: 2;
    row-span: 1;
    height: 1;
}

/* Pane visibility */
.pane {
    display: none;
}

.pane.visible {
    display: block;
}

/* Active button styling */
.button-active {
    background: $primary;
    color: $text;
}
"""
```

#### 5.2 Implement pane toggle logic (1 day)
**Files to Modify:**
- `ccc/tui/app.py`

**Changes:**
```python
class CommandCenterTUI(App):
    active_pane = reactive(None)  # 'tasks', 'agents', or None

    def compose(self):
        yield Header(id="header")
        yield DataTable(id="ticket-table")

        # Pane container with both panes
        with Container(id="pane-container"):
            yield TasksPane(self.tasks_manager, classes="pane", id="tasks-pane")
            yield AgentsPane(self.agent_manager, classes="pane", id="agents-pane")

        yield StatusBar(id="status-bar")
        yield ButtonBar(id="button-bar")
        yield Footer()

    def watch_active_pane(self, pane: Optional[str]) -> None:
        """Update pane visibility when active_pane changes"""
        tasks_pane = self.query_one("#tasks-pane")
        agents_pane = self.query_one("#agents-pane")

        tasks_pane.remove_class("visible")
        agents_pane.remove_class("visible")

        if pane == 'tasks':
            tasks_pane.add_class("visible")
        elif pane == 'agents':
            agents_pane.add_class("visible")

        self._update_button_bar()

    def action_toggle_tasks(self):
        if self.active_pane == 'tasks':
            self.active_pane = None
        else:
            self.active_pane = 'tasks'

    def action_toggle_agents(self):
        if self.active_pane == 'agents':
            self.active_pane = None
        else:
            self.active_pane = 'agents'

    def _update_button_bar(self):
        """Highlight active pane button"""
        button_bar = self.query_one("#button-bar")

        for btn in button_bar.query(".button-toggle"):
            btn.remove_class("button-active")

        if self.active_pane == 'tasks':
            button_bar.query_one("#btn-tasks").add_class("button-active")
        elif self.active_pane == 'agents':
            button_bar.query_one("#btn-agents").add_class("button-active")
```

#### 5.3 Testing (1 day)
- [ ] Tasks pane toggles on/off
- [ ] Agents pane toggles on/off
- [ ] Only one pane visible at a time
- [ ] Ticket list remains visible
- [ ] Active button highlighted
- [ ] Layout works at 80x24 terminal
- [ ] Layout works at 200x60 terminal
- [ ] No flickering during transitions

### Deliverables
- ✅ Dynamic pane toggling works
- ✅ Layout stable across terminal sizes
- ✅ Active button highlighted
- ✅ Smooth transitions

### Files Modified
- `ccc/tui/app.py` (update CSS, add toggle logic)

---

## **PHASE 6: Polish & Documentation** (2-3 days)

### Prerequisites
- All previous phases complete

### Goals
- Complete keyboard shortcuts
- Help overlay
- Error handling
- Documentation

### Tasks

#### 6.1 Complete keyboard shortcuts (0.5 days)
**Files to Modify:**
- `ccc/tui/app.py`

**Ensure all shortcuts work:**
```python
BINDINGS = [
    ("q", "quit", "Quit"),
    ("r", "refresh", "Refresh"),
    ("j", "cursor_down", "Down", show=False),
    ("k", "cursor_up", "Up", show=False),
    ("enter", "select", "Select", show=False),

    # Git & Build
    ("c", "commit", "Commit"),
    ("shift+p", "push", "Push"),
    ("shift+P", "pull", "Pull"),
    ("l", "log", "Log"),

    # External Tools
    ("p", "open_plan", "Plan"),
    ("g", "open_git", "Git"),
    ("n", "open_notes", "Notes"),
    ("j", "open_jira", "Jira"),
    ("d", "open_api_docs", "Docs"),

    # Panes
    ("t", "toggle_tasks", "Tasks"),
    ("a", "toggle_agents", "Agents"),

    # Status Actions
    ("s", "focus_server", "Server"),
    ("b", "run_build", "Build"),
    ("shift+t", "run_tests", "Tests"),

    # Help
    ("?", "show_help", "Help"),
]
```

#### 6.2 Create help overlay (1 day)
**Files to Create:**
- `ccc/tui/help_dialog.py`

**Components:**
```python
class HelpDialog(ModalScreen):
    """Display keyboard shortcuts and help"""

    def compose(self):
        with Container(id="help-container"):
            yield Static("Command Center - Keyboard Shortcuts", id="help-title")

            with VerticalScroll(id="help-content"):
                yield Static(self._render_shortcuts())

            yield Button("Close", id="close-btn")

    def _render_shortcuts(self) -> Text:
        # Organized by category
        shortcuts = {
            "Navigation": [
                ("j/k", "Move up/down"),
                ("enter", "Select ticket"),
            ],
            "Git & Build": [
                ("c", "Commit changes"),
                ("P", "Push to remote"),
                # ...
            ],
            "Panes": [
                ("t", "Toggle tasks"),
                ("a", "Toggle agents"),
            ],
            # ...
        }
```

**Wire into app.py:**
```python
def action_show_help(self):
    self.push_screen(HelpDialog())
```

#### 6.3 Improve error handling (0.5 days)
**Files to Modify:**
- All new modules

**Improvements:**
- Graceful fallbacks when tools not found
- Clear error messages
- Log errors to ~/.ccc-control/logs/ccc.log
- Don't crash on malformed state files

#### 6.4 Write documentation (1 day)
**Files to Create/Modify:**
- `README.md` (update)
- `docs/ARCHITECTURE.md` (new)
- `docs/USER_GUIDE.md` (new)
- `docs/CONFIGURATION.md` (new)

**Documentation Topics:**
- Status bar usage
- External tools configuration
- Multi-agent workflows
- Tasks pane usage
- Keyboard shortcuts
- Configuration reference
- Troubleshooting

#### 6.5 Final testing (0.5 days)
- [ ] Fresh install workflow
- [ ] All keyboard shortcuts
- [ ] Error scenarios
- [ ] Performance with 10+ agents
- [ ] State persistence
- [ ] Configuration changes

### Deliverables
- ✅ All shortcuts documented and working
- ✅ Help overlay accessible
- ✅ Comprehensive error handling
- ✅ Complete documentation

### Files Created
- `ccc/tui/help_dialog.py` (new)
- `docs/ARCHITECTURE.md` (new)
- `docs/USER_GUIDE.md` (new)
- `docs/CONFIGURATION.md` (new)

### Files Modified
- `README.md` (update)
- All modules (error handling)

---

## Total Timeline Summary

| Phase | Duration | Complexity |
|-------|----------|-----------|
| Phase 1: Status Bar | 3-5 days | MEDIUM |
| Phase 2: External Tools | 2-3 days | LOW |
| Phase 3: Multi-Agent | 5-7 days | HIGH |
| Phase 4: Tasks Pane | 2-3 days | LOW |
| Phase 5: Layout | 2-3 days | MEDIUM |
| Phase 6: Polish | 2-3 days | LOW |
| **TOTAL** | **16-24 days** | |

---

## Dependencies Graph

```
Phase 1 (Status Bar)
    │
    ├─→ Phase 2 (External Tools) ─┐
    │                              │
    ├─→ Phase 3 (Multi-Agent) ────┤
    │                              ├─→ Phase 5 (Layout)
    └─→ Phase 4 (Tasks Pane) ─────┘           │
                                               │
                                               └─→ Phase 6 (Polish)
```

**Critical Path:**
Phase 1 → Phase 3 → Phase 5 → Phase 6

**Parallel Opportunities:**
- Phase 2 can run parallel to Phase 3
- Phase 4 can run parallel to Phase 2/3

---

## Risk Assessment

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Log parsing misses edge cases | MEDIUM | HIGH | Comprehensive pattern testing, user-configurable patterns |
| Health checks block UI | HIGH | MEDIUM | Async implementation, configurable intervals |
| Textual CSS layout breaks | MEDIUM | MEDIUM | Test across terminal sizes, minimum size check |
| Multi-agent TODO parsing fragile | MEDIUM | HIGH | Robust regex, fallback to raw output, manual override |
| External tools vary by platform | LOW | HIGH | Platform detection, fallbacks, clear errors |
| app.py refactor breaks features | HIGH | MEDIUM | Incremental changes, comprehensive testing |
| File-based state race conditions | MEDIUM | LOW | File locking, atomic writes, retry logic |

### Implementation Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Scope creep | MEDIUM | MEDIUM | Stick to design doc, defer enhancements |
| Integration issues | HIGH | MEDIUM | Test after each phase, maintain compatibility |
| Performance degradation | MEDIUM | LOW | Profile after major changes, optimize polling |
| State migration needed | LOW | LOW | Keep backward compatibility, migration script |

---

## Success Metrics

### Quantitative
- ✅ Startup time: < 500ms (no regression)
- ✅ Status update latency: < 1s from event to UI
- ✅ Memory footprint: < 100MB baseline
- ✅ Agent tracking overhead: < 50ms per agent
- ✅ All tests passing

### Qualitative
- ✅ Clear at-a-glance project status
- ✅ Reduced context switching time
- ✅ Faster project onboarding
- ✅ Developers use CCC instead of manual tmux
- ✅ Positive user feedback

---

## Next Steps

1. **Review & Approve Plan** ✅ (This document)
2. **Create Feature Branches**
   - `feature/status-bar` for Phase 1
   - `feature/external-tools` for Phase 2
   - `feature/multi-agent` for Phase 3
   - `feature/tasks-pane` for Phase 4
   - `feature/layout-refactor` for Phase 5
   - `feature/polish` for Phase 6

3. **Begin Implementation**
   - Start with Phase 1 (Status Bar)
   - Test thoroughly after each phase
   - Merge to main after validation

4. **Documentation Updates**
   - Keep docs in sync with implementation
   - Update README with new features
   - Create migration guide if needed

---

## Questions for Clarification

### Phase 1 (Status Bar)
1. Should server auto-start when ticket is selected?
2. What database types to support? (PostgreSQL, MySQL, MongoDB?)
3. Should status bar be clickable to focus terminals?

### Phase 2 (External Tools)
4. Which IDE to default to? (Cursor, VS Code, Neovim?)
5. Should Git UI create permanent tmux window or temporary?
6. Database client preferences? (TablePlus, DBeaver, pgAdmin?)

### Phase 3 (Multi-Agent)
7. Should old agents auto-archive after N hours?
8. How to handle agent name conflicts?
9. Parse TODOs from chat history or just latest output?

### Phase 4 (Tasks Pane)
10. Should tasks be editable from CCC?
11. Auto-reload TASKS.md on file change?
12. Support other formats besides markdown?

### Phase 5 (Layout)
13. Default pane visibility (Tasks/Agents/None)?
14. Remember pane preference per ticket?
15. Minimum terminal size requirement?

### Phase 6 (Polish)
16. Log level configuration?
17. Telemetry/analytics desired?
18. Beta testing plan?

---

## Appendix: File Inventory

### Files to Create (18 new files)

```
ccc/
├── status_monitor.py
├── multi_agent_manager.py
├── tasks_manager.py
├── external_tools.py
└── tui/
    ├── widgets/
    │   ├── __init__.py
    │   ├── status_bar.py
    │   ├── button_bar.py
    │   ├── agent_card.py
    │   ├── agents_pane.py
    │   └── tasks_pane.py
    └── help_dialog.py

docs/
├── ARCHITECTURE.md
├── USER_GUIDE.md
└── CONFIGURATION.md

~/.ccc-control/branches/{branch}/
├── status-bar.json (state file)
└── agent-sessions.json (state file)
```

### Files to Modify (4 files)

```
ccc/
├── config.py (extend Config dataclass)
├── status.py (add AgentSession, AgentTodo)
├── claude_chat.py (register multi-agent sessions)
└── tui/
    └── app.py (integrate all new widgets)

README.md (update features)
```

### Files Unchanged (all other existing files)

```
ccc/
├── cli.py ✅
├── ticket.py ✅
├── session.py ✅
├── build_runner.py ✅
├── git_operations.py ✅
├── questions.py ✅
├── todo.py ✅
├── api_request.py ✅
├── plan_reviser.py ✅
└── ... (all other modules)
```

---

**END OF IMPLEMENTATION PLAN**
