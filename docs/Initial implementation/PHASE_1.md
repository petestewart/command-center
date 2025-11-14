# Phase 1: Core Foundation - Implementation Plan

## Overview

**Duration:** 3 weeks  
**Goal:** Prove the core workflow is valuable by building minimal viable features

Phase 1 establishes the foundation: ticket management, tmux orchestration, basic TUI, and status tracking. At the end of this phase, a developer should be able to create tickets, track agent status, and quickly jump between terminal contexts.

---

## Week 1: CLI + Tmux Session Management

### Objectives

- Set up project structure and tooling
- Implement CLI commands for ticket lifecycle
- Build tmux session orchestration layer

### Technical Components

#### 1.1 Project Setup

**Files to create:**

```
cc/
├── cli.py           # CLI entry point and command routing
├── config.py        # Configuration management
├── ticket.py        # Ticket data structures and persistence
├── session.py       # Tmux session management
├── status.py        # Agent status file handling
└── utils.py         # Helper functions
```

**Dependencies:**

- Python 3.10+
- `libtmux` - Python wrapper for tmux
- `pyyaml` - YAML parsing for config/state
- `click` - CLI framework (or `argparse` for simpler option)

**Configuration file format:**

```yaml
# ~/.ccc-control/config.yaml
base_worktree_path: ~/code/worktrees
status_poll_interval: 3
tmux_session_prefix: ccc-
```

#### 1.2 Ticket Registry

**Data structure:**

```python
@dataclass
class Ticket:
    id: str                    # e.g., "IN-413"
    title: str                 # e.g., "Public API bulk uploads"
    branch: str                # e.g., "feature/IN-413-bulk-uploads"
    worktree_path: str         # e.g., "~/code/worktrees/IN-413"
    created_at: datetime
    status: str                # "active", "complete", "blocked"
    tmux_session: str          # e.g., "ccc-IN-413"
```

**Storage location:** `~/.ccc-control/tickets.yaml`

**Example tickets file:**

```yaml
tickets:
  - id: IN-413
    title: Public API bulk uploads
    branch: feature/IN-413-bulk-uploads
    worktree_path: /home/user/code/worktrees/IN-413
    created_at: 2025-11-09T10:23:00Z
    status: active
    tmux_session: ccc-IN-413

  - id: IN-407
    title: Refactor auth middleware
    branch: feature/IN-407-auth-refactor
    worktree_path: /home/user/code/worktrees/IN-407
    created_at: 2025-11-08T14:15:00Z
    status: complete
    tmux_session: ccc-IN-407
```

#### 1.3 CLI Commands

**`ccc create <ticket-id> <title>`**

```python
def create_ticket(ticket_id: str, title: str) -> None:
    """
    1. Validate ticket_id format
    2. Create ticket entry in registry
    3. Create git worktree and checkout branch
    4. Create tmux session with 3 windows
    5. Write initial status file
    6. Print success message with next steps
    """
```

**Example usage:**

```bash
$ ccc create IN-413 "Public API bulk uploads"
✓ Created ticket IN-413
✓ Created worktree at ~/code/worktrees/IN-413
✓ Created branch feature/IN-413-bulk-uploads
✓ Created tmux session ccc-IN-413 with windows:
  - agent (window 0)
  - server (window 1)
  - tests (window 2)

Next steps:
  - Attach to agent terminal: ccc attach IN-413 agent
  - Or open Command Center: cc
```

**`ccc list`**

```python
def list_tickets() -> None:
    """
    1. Load tickets from registry
    2. Read status files for each
    3. Print formatted table of tickets
    """
```

**Example output:**

```bash
$ ccc list
ID      TITLE                        STATUS      UPDATED
IN-413  Public API bulk uploads      Working     2m ago
IN-407  Refactor auth middleware     Complete    1h ago
IN-391  Database migration           Blocked     3h ago

3 tickets total (1 active, 1 complete, 1 blocked)
```

**`ccc delete <ticket-id>`**

```python
def delete_ticket(ticket_id: str) -> None:
    """
    1. Confirm with user
    2. Kill tmux session
    3. Remove worktree (optional, ask user)
    4. Remove from registry
    5. Archive status files (don't delete, move to archive)
    """
```

**`ccc attach <ticket-id> <window>`**

```python
def attach_to_terminal(ticket_id: str, window: str) -> None:
    """
    1. Validate ticket exists
    2. Validate window name (agent|server|tests)
    3. Execute tmux attach command
    """
```

**Example usage:**

```bash
$ ccc attach IN-413 agent
# Attaches to tmux session ccc-IN-413, window 0 (agent)
```

#### 1.4 Tmux Session Management

**Session structure:**

```
Session: ccc-IN-413
├── Window 0: agent
│   └── Working directory: ~/code/worktrees/IN-413
│   └── Initial command: bash (user starts claude code manually)
│
├── Window 1: server
│   └── Working directory: ~/code/worktrees/IN-413
│   └── Initial command: bash (user starts server manually)
│
└── Window 2: tests
    └── Working directory: ~/code/worktrees/IN-413
    └── Initial command: bash (user runs tests manually)
```

**Implementation:**

```python
import libtmux

def create_tmux_session(ticket: Ticket) -> None:
    server = libtmux.Server()
    session = server.new_session(
        session_name=ticket.tmux_session,
        window_name="agent",
        start_directory=ticket.worktree_path
    )

    # Create additional windows
    session.new_window("server", start_directory=ticket.worktree_path)
    session.new_window("tests", start_directory=ticket.worktree_path)

    # Don't attach yet - just create
```

**Attach mechanism:**

```python
def attach_to_window(ticket_id: str, window_name: str) -> None:
    ticket = load_ticket(ticket_id)
    window_map = {"agent": 0, "server": 1, "tests": 2}
    window_idx = window_map[window_name]

    # Execute tmux attach in current terminal
    os.system(f"tmux attach-session -t {ticket.tmux_session}:{window_idx}")
```

### Week 1 Deliverables

✅ Project structure created  
✅ Configuration system working  
✅ `ccc create` creates ticket + worktree + tmux session  
✅ `ccc list` shows all tickets  
✅ `ccc attach` switches to any terminal  
✅ `ccc delete` cleans up ticket  
✅ Basic error handling (ticket not found, etc.)

### Week 1 Testing Plan

**Manual tests:**

1. Create 3 tickets with different IDs
2. Verify worktrees created in correct locations
3. Verify branches checked out
4. Verify tmux sessions exist with 3 windows each
5. Attach to each window type (agent, server, tests)
6. Delete a ticket, verify cleanup

**Edge cases to test:**

- Create ticket with duplicate ID (should error)
- Attach to non-existent ticket (should error)
- Delete ticket with running tmux session
- Create ticket with invalid ID format

---

## Week 2: Basic TUI

### Objectives

- Build terminal UI using Textual framework
- Implement ticket list and detail views
- Enable keyboard navigation and shortcuts

### Technical Components

#### 2.1 TUI Framework Setup

**Add dependencies:**

- `textual` - Modern TUI framework with excellent docs

**Main TUI structure:**

```python
from textual.app import App
from textual.containers import Container
from textual.widgets import Header, Footer, Static

class CommandCenterApp(App):
    """Main TUI application"""

    CSS_PATH = "cc.css"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("?", "help", "Help"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self):
        yield Header()
        yield Container(
            TicketListView(),
            id="main"
        )
        yield Footer()
```

#### 2.2 Ticket List View

**Component hierarchy:**

```
TicketListView (Container)
└── TicketList (ListView)
    ├── TicketItem (ListItem) - IN-413
    ├── TicketItem (ListItem) - IN-407
    └── TicketItem (ListItem) - IN-391
```

**TicketItem display:**

```python
class TicketItem(ListItem):
    def __init__(self, ticket: Ticket):
        super().__init__()
        self.ticket = ticket

    def render(self) -> str:
        status_symbol = self._get_status_symbol()
        status_text = self._get_status_text()
        time_ago = self._format_time_ago()

        return f"{status_symbol} {self.ticket.id}  {self.ticket.title:<40} {status_text:>12} {time_ago:>10}"
```

**Keyboard bindings in list view:**

- `j`/`↓` - Move selection down
- `k`/`↑` - Move selection up
- `Enter` - Open ticket detail view
- `n` - Create new ticket
- `d` - Delete selected ticket

#### 2.3 Ticket Detail View

**Layout:**

```
┌─ Ticket Detail ────────────────────────────────────────┐
│ ID: IN-413                                             │
│ Title: Public API bulk uploads                         │
│ Branch: feature/IN-413-bulk-uploads                    │
│ Worktree: ~/code/worktrees/IN-413                      │
│                                                        │
│ [Agent Status Panel]                                   │
│ [Git Status Panel]                                     │
│ [Quick Actions]                                        │
└────────────────────────────────────────────────────────┘
```

**Keyboard bindings in detail view:**

- `Esc` - Return to list view
- `a` - Jump to agent terminal
- `s` - Jump to server terminal
- `t` - Jump to tests terminal

#### 2.4 Terminal Navigation Integration

**Challenge:** When user presses `a`, we need to:

1. Suspend the TUI
2. Attach to tmux session
3. When user detaches, resume TUI

**Implementation approach:**

```python
class TicketDetailView(Container):
    def action_jump_to_agent(self):
        # Suspend TUI
        self.app.suspend()

        # Attach to tmux
        ticket = self.current_ticket
        os.system(f"tmux attach-session -t {ticket.tmux_session}:0")

        # This blocks until user detaches from tmux
        # When they detach, resume TUI
        self.app.resume()

        # Refresh status when returning
        self.refresh_status()
```

**User instructions:**
When jumping to terminal, briefly show:

```
Attaching to agent terminal...
Press [Ctrl-b] then [d] to return to Command Center
```

#### 2.5 Styling

**CSS for Textual:**

```css
/* cc.css */

TicketItem {
  height: 3;
  padding: 1;
}

TicketItem:focus {
  background: $accent;
}

.status-working {
  color: $success;
}

.status-complete {
  color: $secondary;
}

.status-blocked {
  color: $warning;
}

StatusPanel {
  border: solid $primary;
  height: 8;
  padding: 1;
}
```

### Week 2 Deliverables

✅ TUI launches and displays ticket list  
✅ Can navigate tickets with keyboard  
✅ Can open ticket detail view  
✅ Can jump to terminals (a/s/t keys)  
✅ TUI suspends/resumes correctly  
✅ Basic styling and colors working  
✅ Help overlay accessible via `?`

### Week 2 Testing Plan

**Manual tests:**

1. Launch TUI, verify all tickets shown
2. Navigate with j/k keys
3. Press Enter, verify detail view appears
4. Press 'a', verify tmux attaches
5. Detach from tmux (Ctrl-b d), verify TUI resumes
6. Press '?' in various views, verify help shows
7. Create ticket from TUI (n key)

**UI tests:**

- Verify colors appear correctly
- Verify layout doesn't break on small terminals (80x24)
- Verify layout adapts to larger terminals

---

## Week 3: Status Tracking

### Objectives

- Define agent status file format
- Implement file watching and polling
- Display real-time status in TUI

### Technical Components

#### 3.1 Agent Status File Format

**Location:** `~/.ccc-control/<ticket-id>/agent-status.json`

**Format:**

```json
{
  "ticket_id": "IN-413",
  "status": "working",
  "current_task": "Adding input validation",
  "last_update": "2025-11-09T14:32:00Z",
  "questions": [],
  "blocked": false,
  "metadata": {
    "files_modified": 3,
    "commits": 2
  }
}
```

**Status values:**

- `idle` - Agent waiting for instructions
- `working` - Agent actively coding
- `complete` - Agent finished all work
- `blocked` - Agent needs input/approval
- `error` - Agent encountered error

**How agents write status:**

Agents (or developers manually) update this file periodically:

```bash
# From agent terminal, agent could run:
echo '{"status": "working", "current_task": "Adding validation", "last_update": "'$(date -Iseconds)'"}' > ~/.ccc-control/IN-413/agent-status.json
```

Or use a helper script we provide:

```bash
`ccc status update IN-413 --status working --task "Adding validation"
```

#### 3.2 Status Polling

**Polling mechanism:**

```python
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class StatusWatcher:
    def __init__(self, ticket_id: str, callback):
        self.ticket_id = ticket_id
        self.callback = callback
        self.status_file = f"~/.ccc-control/{ticket_id}/agent-status.json"

    def start(self):
        # Simple polling approach for Phase 1
        while True:
            status = self._read_status()
            self.callback(status)
            time.sleep(3)  # Poll every 3 seconds

    def _read_status(self) -> dict:
        try:
            with open(self.status_file) as f:
                return json.load(f)
        except FileNotFoundError:
            return {"status": "unknown", "last_update": None}
```

**Integration with TUI:**

```python
class CommandCenterApp(App):
    def on_mount(self):
        # Start status polling in background thread
        self.status_watcher = StatusWatcher("IN-413", self.update_status)
        threading.Thread(target=self.status_watcher.start, daemon=True).start()

    def update_status(self, status: dict):
        # Update TUI with new status
        self.query_one(TicketListView).update_ticket_status(status)
```

#### 3.3 Status Display in TUI

**In list view:**

```
● IN-413  Public API bulk uploads      ⚙ Working    2m ago
                                       ↑ status     ↑ time since last update
```

**In detail view:**

```
┌─ Agent Status ─────────────────────────────────┐
│ Status: ⚙ Working                              │
│ Current Task: Adding input validation          │
│ Last Update: 2 minutes ago                     │
│ Questions: None                                │
│ Blocked: No                                    │
└────────────────────────────────────────────────┘
```

**Status change notifications:**

When status changes (e.g., from "working" to "complete"), briefly show toast:

```
[✓] IN-413: Agent completed work
```

#### 3.4 Graceful Degradation

**If status file doesn't exist:**

- Show status as "Unknown"
- Don't error or crash
- Display helpful message: "Agent hasn't started yet"

**If status file is stale (>1 hour old):**

- Show status with ⚠ warning symbol
- Gray out the status
- Add note: "Last update 3 hours ago - may be stale"

**If status file is malformed:**

- Log error
- Show status as "Error reading status"
- Don't crash TUI

#### 3.5 Helper CLI for Agents

To make it easy for agents (or developers testing) to update status:

**`ccc status update <ticket-id> [options]`**

```bash
$ ccc status update IN-413 --status working --task "Adding validation"
✓ Updated status for IN-413

$ ccc status update IN-413 --status blocked --question "Should we use Zod or Joi?"
✓ Updated status for IN-413 (blocked, awaiting answer)

$ ccc status update IN-413 --status complete
✓ Updated status for IN-413 (work complete)
```

**`ccc status show <ticket-id>`**

```bash
$ ccc status show IN-413
Status: Working
Task: Adding input validation
Updated: 2 minutes ago
Blocked: No
Questions: None
```

### Week 3 Deliverables

✅ Status file format defined and documented  
✅ Status polling working in background  
✅ TUI displays live status updates  
✅ `ccc status` CLI commands working  
✅ Graceful handling of missing/stale status  
✅ Status change notifications appearing

### Week 3 Testing Plan

**Manual tests:**

1. Create ticket, start TUI
2. Manually update status file
3. Verify TUI updates within 3 seconds
4. Update status to different values (working, blocked, complete)
5. Delete status file, verify TUI handles gracefully
6. Create malformed JSON in status file, verify no crash

**Integration tests:**

1. Create ticket with `ccc create`
2. Update status with `ccc status update`
3. Verify TUI shows correct status
4. Update status to "complete"
5. Verify toast notification appears

---

## Phase 1 Success Criteria

At the end of Phase 1, the following must be possible:

### Core Workflow

✅ Developer can create a new ticket in <10 seconds  
✅ Developer can see all active tickets in one view  
✅ Developer can jump to any terminal context in <2 seconds  
✅ Agent status updates appear automatically without manual checking

### User Experience

✅ TUI is intuitive - first-time user can navigate without docs  
✅ Keyboard shortcuts feel natural (vim-like navigation)  
✅ No crashes or hangs during normal operation  
✅ Error messages are clear and actionable

### Technical Quality

✅ All CLI commands have help text and examples  
✅ Ticket registry persists across sessions  
✅ Tmux sessions survive terminal closures  
✅ Status polling uses <1% CPU

---

## Known Limitations (Phase 1)

These are explicitly out of scope and will be addressed in later phases:

❌ No todo list breakdown - just track overall ticket status  
❌ No git integration - developer uses git commands manually  
❌ No build/test automation - developer runs these manually  
❌ No diff viewing - developer uses `git diff` in terminal  
❌ No IDE integration - developer opens IDE separately  
❌ No multi-agent support - assumes one agent per ticket  
❌ No team features - single developer use only

---

## Risk Mitigation

### Risk: Tmux not installed

**Mitigation:** Check for tmux on first run, show installation instructions if missing

### Risk: TUI doesn't work on user's terminal

**Mitigation:** Test on common terminals (iTerm2, Alacritty, gnome-terminal), document requirements

### Risk: Status polling is too slow

**Mitigation:** Make poll interval configurable, provide manual refresh option

### Risk: Developers don't update status files

**Mitigation:**

- Make `ccc status update` command very easy to use
- Provide shell aliases/shortcuts
- In later phases, integrate with Claude Code directly

---

## Documentation Deliverables

For Phase 1, we need:

1. **README.md** - Installation, quick start, basic usage
2. **CLI_REFERENCE.md** - Every command with examples
3. **STATUS_FILE_FORMAT.md** - Spec for agent status files
4. **KEYBOARD_SHORTCUTS.md** - All TUI keyboard bindings
5. **TROUBLESHOOTING.md** - Common issues and fixes

---

## Next Steps After Phase 1

Once Phase 1 is complete and tested:

1. **User Testing** - Have 2-3 developers try it for a week
2. **Feedback Collection** - What works? What's confusing? What's missing?
3. **Iteration** - Fix bugs and UX issues before starting Phase 2
4. **Phase 2 Planning** - Refine Phase 2 plan based on Phase 1 learnings
