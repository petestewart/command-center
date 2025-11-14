# CCC Restructure - Getting Started Guide

**Last Updated:** November 14, 2025
**Status:** Ready for Implementation
**Current Branch:** `claude/ccc-restructure-design-01PrMD4vz7DzsyPTGm3GbuST`

---

## Quick Start

### For a New Agent Starting Phase 1

1. **Read This File First** - You're in the right place!
2. **Read** `IMPLEMENTATION_PLAN.md` - Detailed technical specs
3. **Read** `VALIDATION_REPORT.md` - Known issues and mitigations
4. **Review** User Configuration Decisions (below)
5. **Create Feature Branch** - `git checkout -b feature/phase1-status-bar`
6. **Start Coding** - Begin with Phase 1, Task 1.1

### For Other Phases

- **Phase 2:** External Tools - See "Phase 2 Entry Point" below
- **Phase 3:** Multi-Agent - See "Phase 3 Entry Point" below
- **Phase 4:** Tasks Pane - See "Phase 4 Entry Point" below
- **Phase 5:** Layout - See "Phase 5 Entry Point" below
- **Phase 6:** Polish - See "Phase 6 Entry Point" below

---

## User Configuration Decisions ⭐

**IMPORTANT:** These are the user's actual preferences. Use these for all implementation:

### Server Configuration
```yaml
commands:
  server:
    auto_start: false  # ❌ NO auto-start on ticket select
    command: "npm run dev"
    health_check_interval: 10
    # User starts manually via Server button or keyboard shortcut
```

### Database Configuration
```yaml
connections:
  database:
    type: "postgresql"  # ✅ PostgreSQL only (for now)
    client_command: "open"
    client_args: ["-a", "TablePlus"]  # ✅ Launch TablePlus
    health_check_interval: 30
```

### IDE Configuration
```yaml
tools:
  ide:
    command: "cursor"  # ✅ Cursor is the default IDE
    args: []
```

### Git UI Configuration
```yaml
tools:
  git_ui:
    command: "lazygit"
    window_mode: "temporary"  # ✅ Create fresh window each time (simpler)
    # Window closes when lazygit exits
    # No state tracking needed
```

### Feature Flags
```yaml
features:
  agent_auto_archive: false  # ❌ User manually archives agents
  tasks_editable: false      # ❌ Read-only for now (simpler)
  tasks_auto_reload: true    # ✅ Watch TASKS.md for changes
```

### UI Configuration
```yaml
ui:
  default_pane: "tasks"  # ✅ Tasks pane visible by default
  min_terminal_width: 120   # Match lazygit requirements
  min_terminal_height: 30
```

### Logging
```yaml
logging:
  level: "INFO"  # INFO default, DEBUG available via config
  file: "~/.ccc-control/logs/ccc.log"
```

### Development/Release
- **Beta Testing:** User is the beta tester
- **Release Plan:** Incremental (user tests locally before any public release)
- **Documentation:** In-code (not separate hosted docs)
- **Support:** Self-supported (greenfield, no existing users)
- **State Migration:** Not needed (no existing users)
- **Telemetry:** None

---

## Project Overview

### What We're Building

Transform CCC from a **single-agent ticket viewer** into a **comprehensive project orchestrator**:

**Before (Current):**
```
┌─────────────────┬───────────────────┐
│  Ticket List    │  Detail Panels    │
│                 │  - Agent Status   │
│                 │  - Git Status     │
│                 │  - Build Status   │
│                 │  - Test Status    │
└─────────────────┴───────────────────┘
```

**After (Target):**
```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃           CCC Command Center        ┃
┣━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┫
┃ Ticket List  ┃  Tasks/Agents Pane  ┃
┃              ┃  (toggleable)       ┃
┣━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━━━┫
┃ STATUS BAR (always visible)        ┃
┃ SERVER: ● :7878  DATABASE: ● :5432 ┃
┃ TESTS: ✓ 187/187  BUILD: ● (2m ago)┃
┣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┫
┃ [Tasks] [Agents] │ [Plan] [Git]    ┃
┃ [Server] [DB] [Build] [Tests]      ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
```

### Key Features

1. **Status Bar** (Phase 1) - Real-time monitoring of server, DB, build, tests
2. **External Tools** (Phase 2) - Quick launch IDE, Git UI, browser, DB client
3. **Multi-Agent** (Phase 3) - Track multiple Claude agents with TODO parsing
4. **Tasks Pane** (Phase 4) - Display project TASKS.md with auto-reload
5. **Layout** (Phase 5) - Toggleable panes, responsive design
6. **Polish** (Phase 6) - Help overlay, docs, testing

### Timeline

- **Total:** 16-24 days across 6 phases
- **Critical Path:** Phase 1 → Phase 3 → Phase 5 → Phase 6 (12-18 days)
- **Parallel Opportunities:** Phase 2 & 4 can run parallel with Phase 3

---

## Technical Foundation

### Current Architecture

**Verified and Ready:**
- ✅ **app.py:** 1297 lines (monolithic, to be refactored)
- ✅ **Tmux:** 3 windows per ticket (agent:0, server:1, tests:2)
- ✅ **CommandRunner:** Subprocess execution with streaming output
- ✅ **State:** File-based JSON/YAML in `~/.ccc-control/branches/{branch}/`
- ✅ **Polling:** 3-second interval already implemented
- ✅ **Textual:** v0.40.0+ with reactive properties and CSS layouts

### Dependencies

**Required Packages (already installed):**
```toml
libtmux>=0.23.0
textual>=0.40.0
rich>=13.0.0
requests>=2.31.0  # For health checks
pyyaml>=6.0
click>=8.1.0
python-dateutil>=2.8.0
```

**Test Dependencies:**
```bash
pytest>=9.0.0
pytest-cov>=7.0.0
```

### File Structure

**Current:**
```
ccc/
├── cli.py                 # Entry point
├── tui/
│   ├── app.py             # Main TUI (1297 lines)
│   ├── widgets.py         # Existing widgets
│   ├── dialogs.py         # Existing dialogs
│   ├── chat_widgets.py    # Chat components
│   └── api_widgets.py     # API components
├── status.py              # AgentStatus dataclass
├── session.py             # TmuxSessionManager
├── build_runner.py        # CommandRunner
├── config.py              # Configuration
├── todo.py                # TodoItem/TodoList
└── claude_chat.py         # Claude integration
```

**After Implementation (18 new files, 4 modified):**
```
ccc/
├── status_monitor.py          # NEW - Server/DB monitoring
├── multi_agent_manager.py     # NEW - Multi-agent tracking
├── tasks_manager.py           # NEW - TASKS.md parsing
├── external_tools.py          # NEW - Tool launchers
├── status.py                  # MODIFIED - Add AgentSession
├── config.py                  # MODIFIED - Extend Config
├── claude_chat.py             # MODIFIED - Register sessions
└── tui/
    ├── app.py                 # MODIFIED - Integrate all
    ├── help_dialog.py         # NEW - Help overlay
    └── widgets/               # NEW DIRECTORY
        ├── __init__.py        # NEW
        ├── status_bar.py      # NEW - Status bar widget
        ├── button_bar.py      # NEW - Button bar widget
        ├── agent_card.py      # NEW - Agent card widget
        ├── agents_pane.py     # NEW - Agents pane widget
        └── tasks_pane.py      # NEW - Tasks pane widget
```

---

## Phase Entry Points

### Phase 1: Status Bar System

**📍 You Are Here** - Start with this phase

**Prerequisites:** None (foundation phase)

**Goal:** Add always-visible status bar showing server, database, build, test status

**Starting Point:**
1. Read `IMPLEMENTATION_PLAN.md` - Phase 1 section (lines 66-269)
2. Create `ccc/status_monitor.py` first (Task 1.1)
3. Follow tasks 1.1 → 1.2 → 1.3 → 1.4 → 1.5 in order

**Files to Create:**
- `ccc/status_monitor.py`
- `ccc/tui/widgets/` (directory)
- `ccc/tui/widgets/__init__.py`
- `ccc/tui/widgets/status_bar.py`

**Files to Modify:**
- `ccc/config.py` (extend Config dataclass)
- `ccc/tui/app.py` (add StatusBar widget)

**Success Criteria:**
- [ ] Status bar visible at all times
- [ ] Server status reflects process state
- [ ] Health checks run without blocking UI
- [ ] Database connection status accurate
- [ ] Build/Test status integrated
- [ ] Clicking status focuses tmux window

**Estimated Time:** 3-5 days

---

### Phase 2: External Tool Launchers

**Prerequisites:** Phase 1 complete

**Goal:** Quick-launch buttons for IDE, Git UI, browser, DB client

**Starting Point:**
1. Read `IMPLEMENTATION_PLAN.md` - Phase 2 section (lines 270-458)
2. Create `ccc/external_tools.py` first
3. Follow tasks 2.1 → 2.2 → 2.3 → 2.4 → 2.5

**Key Implementation Notes:**
- Git UI: **Temporary window** (create fresh each time, no state tracking)
- IDE: Default to **Cursor**, fallback to `$EDITOR`
- Database: Launch **TablePlus** with PostgreSQL connection

**Files to Create:**
- `ccc/external_tools.py`
- `ccc/tui/widgets/button_bar.py`

**Files to Modify:**
- `ccc/config.py` (add tool configuration)
- `ccc/tui/app.py` (add ButtonBar, actions)

**Success Criteria:**
- [ ] Plan/Notes open in Cursor
- [ ] Git button launches lazygit in temporary tmux window
- [ ] API/Jira buttons open URLs in browser
- [ ] Database button launches TablePlus
- [ ] All keyboard shortcuts work

**Estimated Time:** 2-3 days

---

### Phase 3: Multi-Agent Tracking

**Prerequisites:** Phase 1 complete

**Goal:** Track multiple concurrent Claude agents with TODO parsing

**Starting Point:**
1. Read `IMPLEMENTATION_PLAN.md` - Phase 3 section (lines 459-706)
2. Read `VALIDATION_REPORT.md` - Issue #3 (TODO parsing fragility)
3. Extend `ccc/status.py` first (Task 3.1)
4. Follow tasks 3.1 → 3.2 → 3.3 → 3.4 → 3.5 → 3.6 → 3.7

**Key Implementation Notes:**
- **TODO Parsing:** Support multiple formats (✓, [x], -, [ ])
- **Progress:** Calculate from TODO completion ratio
- **State File:** `~/.ccc-control/branches/{branch}/agent-sessions.json`
- **No Auto-Archive:** User manually archives agents

**Files to Create:**
- `ccc/multi_agent_manager.py`
- `ccc/tui/widgets/agent_card.py`
- `ccc/tui/widgets/agents_pane.py`

**Files to Modify:**
- `ccc/status.py` (add AgentSession, AgentTodo dataclasses)
- `ccc/tui/app.py` (integrate AgentsPane)
- `ccc/claude_chat.py` (register sessions with manager)

**Success Criteria:**
- [ ] Multiple agent cards display simultaneously
- [ ] TODO lists parsed from agent output
- [ ] Progress bars update
- [ ] Open button focuses tmux pane
- [ ] Archive button removes session
- [ ] State persists across CCC restarts

**Estimated Time:** 5-7 days

**⚠️ High Risk Area:** TODO parsing is fragile - see mitigation in VALIDATION_REPORT.md

---

### Phase 4: Tasks Pane

**Prerequisites:** None (independent feature)

**Goal:** Display project TASKS.md with auto-reload

**Starting Point:**
1. Read `IMPLEMENTATION_PLAN.md` - Phase 4 section (lines 707-831)
2. Create `ccc/tasks_manager.py` first
3. Follow tasks 4.1 → 4.2 → 4.3 → 4.4

**Key Implementation Notes:**
- **Read-Only:** Tasks not editable from CCC (simpler implementation)
- **Auto-Reload:** Watch TASKS.md for file changes
- **Format:** Standard markdown checkboxes `- [ ]` and `- [x]`
- **Nesting:** Support 2-space indentation

**Files to Create:**
- `ccc/tasks_manager.py`
- `ccc/tui/widgets/tasks_pane.py`

**Files to Modify:**
- `ccc/tui/app.py` (add TasksPane, toggle action)
- `ccc/config.py` (add tasks_file field)

**Success Criteria:**
- [ ] Tasks display from TASKS.md
- [ ] Checkboxes show correctly
- [ ] Nested tasks indent properly
- [ ] File changes auto-reload
- [ ] Toggle action works

**Estimated Time:** 2-3 days

**💡 Can Run in Parallel with Phase 2 or 3**

---

### Phase 5: Layout Refactoring

**Prerequisites:** Phases 2, 3, 4 complete

**Goal:** Dynamic pane toggling, responsive layout

**Starting Point:**
1. Read `IMPLEMENTATION_PLAN.md` - Phase 5 section (lines 832-1002)
2. Update CSS in `app.py` first (Task 5.1)
3. Follow tasks 5.1 → 5.2 → 5.3

**Key Implementation Notes:**
- **Default Pane:** Tasks pane visible by default
- **Toggle:** Only one pane visible at a time (Tasks OR Agents OR None)
- **Layout:** 2-column grid, ticket list always visible
- **Minimum Size:** 120x30 (match lazygit requirements)

**CSS Changes:**
```python
# From horizontal layout to grid
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

**Files to Modify:**
- `ccc/tui/app.py` (update CSS, add toggle logic)

**Success Criteria:**
- [ ] Panes toggle smoothly
- [ ] Only one pane visible at a time
- [ ] Ticket list remains visible
- [ ] Active button highlighted
- [ ] Works at 80x24 minimum
- [ ] Works at 200x60 large
- [ ] No flickering

**Estimated Time:** 2-3 days

**⚠️ Risk Area:** CSS layout complexity - test extensively

---

### Phase 6: Polish & Documentation

**Prerequisites:** Phase 5 complete

**Goal:** Help overlay, keyboard shortcuts, docs, testing

**Starting Point:**
1. Read `IMPLEMENTATION_PLAN.md` - Phase 6 section (lines 1003-1350)
2. Create `ccc/tui/help_dialog.py` first
3. Follow tasks 6.1 → 6.2 → 6.3 → 6.4 → 6.5

**Key Deliverables:**
- Help overlay with all keyboard shortcuts
- Comprehensive error handling
- In-code documentation
- Final testing across scenarios

**Files to Create:**
- `ccc/tui/help_dialog.py`
- Update inline documentation

**Files to Modify:**
- All modules (add error handling)
- `ccc/tui/app.py` (add help action)

**Success Criteria:**
- [ ] Help accessible with `?` key
- [ ] All shortcuts documented
- [ ] Error messages clear
- [ ] No critical bugs
- [ ] All tests passing
- [ ] Ready for user testing

**Estimated Time:** 2-3 days

---

## Known Issues & Mitigations

**See `VALIDATION_REPORT.md` for complete list. Key issues:**

### 🔴 High Priority

1. **Log Parsing Reliability** (Phase 1)
   - **Risk:** Server logs may have unexpected formats
   - **Mitigation:** User-configurable patterns, comprehensive testing
   - **See:** VALIDATION_REPORT.md - Issue #1

2. **Health Check Performance** (Phase 1)
   - **Risk:** HTTP checks could block UI
   - **Mitigation:** Async implementation, 2s timeout, 10s interval
   - **See:** VALIDATION_REPORT.md - Issue #2

3. **TODO Parsing Fragility** (Phase 3)
   - **Risk:** Claude output varies, parsing may fail
   - **Mitigation:** Multiple format support, fallback to raw output
   - **See:** VALIDATION_REPORT.md - Issue #3

### 🟡 Medium Priority

4. **Platform Variance** (Phase 2) - Different OS tool launching
5. **CSS Layout** (Phase 5) - Complex grid layout may break
6. **State Race Conditions** (Phases 1, 3) - Multiple writes to same file

**All mitigations documented in VALIDATION_REPORT.md**

---

## Testing Strategy

### Unit Tests (Required for Each Phase)

Create test file for each new module:
```bash
tests/test_status_monitor.py
tests/test_multi_agent_manager.py
tests/test_tasks_manager.py
tests/test_external_tools.py
```

**Minimum Coverage:** 80% for new code

### Integration Tests

Test end-to-end workflows:
- Server start → health check → status update
- Multi-agent launch → TODO parsing → progress update
- TASKS.md change → auto-reload → display update

### Manual Testing Checklist

At end of each phase:
- [ ] Fresh installation workflow
- [ ] All keyboard shortcuts
- [ ] Terminal sizes (80x24 to 200x60)
- [ ] Error scenarios
- [ ] State persistence
- [ ] Configuration changes

**Full checklist in VALIDATION_REPORT.md**

---

## Git Workflow

### Branch Strategy

```
main
  ↓
feature/phase1-status-bar
  ↓
feature/phase2-external-tools
  ↓
feature/phase3-multi-agent
  ↓
[etc...]
```

### Commit Guidelines

**Granular commits preferred:**
```bash
git commit -m "Add ServerStatus and DatabaseStatus dataclasses"
git commit -m "Implement LogPatternMatcher for server logs"
git commit -m "Add StatusMonitor with health check system"
```

**Not:**
```bash
git commit -m "Implement Phase 1"  # Too large
```

### PR Process

1. Create PR from feature branch
2. Self-review using checklist
3. Ensure tests pass
4. User reviews and merges

---

## Common Pitfalls

### For Phase 1
- ❌ Don't block UI thread with health checks → Use threading
- ❌ Don't assume server logs follow one format → Make patterns configurable
- ❌ Don't forget to handle tmux window not existing → Check before focusing

### For Phase 3
- ❌ Don't assume TODO format is consistent → Support multiple patterns
- ❌ Don't parse entire chat history → Only parse latest output
- ❌ Don't forget session cleanup → Provide manual archive button

### For Phase 5
- ❌ Don't test only at one terminal size → Test 80x24 to 200x60
- ❌ Don't modify existing panels → Only add new pane container
- ❌ Don't change CSS without testing → Textual CSS can be fragile

---

## Communication

### Questions During Implementation

If you encounter:
- **Technical blocker:** Document in PR, propose solution
- **Design decision:** Refer to user configuration decisions above
- **Unclear requirement:** Check IMPLEMENTATION_PLAN.md first, then ask

### Progress Updates

Commit messages should be clear about progress:
```
✅ Good: "Complete Task 1.1: Create status_monitor.py"
❌ Bad: "Work on status monitoring"
```

---

## Resources

### Documentation Files

- **IMPLEMENTATION_PLAN.md** - Complete technical specifications (1,350 lines)
- **VALIDATION_REPORT.md** - Issues, risks, mitigations (829 lines)
- **THIS FILE** - Getting started guide
- **README.md** - Project overview

### Code References

- **Existing widgets:** `ccc/tui/widgets.py` - Widget patterns
- **Existing dialogs:** `ccc/tui/dialogs.py` - Dialog patterns
- **CommandRunner:** `ccc/build_runner.py` - Subprocess execution
- **TmuxSessionManager:** `ccc/session.py` - Tmux integration
- **Config pattern:** `ccc/config.py` - Configuration management

### External References

- **Textual Docs:** https://textual.textualize.io/
- **libtmux Docs:** https://libtmux.readthedocs.io/
- **Rich Docs:** https://rich.readthedocs.io/

---

## Quick Reference Commands

### Setup
```bash
# Clone and install
git clone <repo>
cd command-center
pip install -e .
pip install pytest pytest-cov

# Run tests
pytest tests/ -v

# Run app
ccc tui
```

### Development
```bash
# Create feature branch
git checkout -b feature/phase1-status-bar

# Run specific test
pytest tests/test_status_monitor.py -v

# Check coverage
pytest --cov=ccc --cov-report=html

# Run linter
ruff check ccc/
```

### Debugging
```bash
# View logs
tail -f ~/.ccc-control/logs/ccc.log

# Check state files
cat ~/.ccc-control/branches/<branch>/agent-status.json
cat ~/.ccc-control/branches/<branch>/status-bar.json

# List tmux sessions
tmux ls

# Attach to session
tmux attach -t ccc-<branch>
```

---

## Success Criteria (Overall)

Project is complete when:

- ✅ All 6 phases implemented
- ✅ All tests passing (>80% coverage)
- ✅ No critical bugs
- ✅ User successfully using in daily workflow
- ✅ Documentation complete
- ✅ Performance meets targets:
  - Startup < 500ms
  - Status updates < 1s latency
  - Memory < 100MB baseline

---

## Contact & Support

**Primary User/Tester:** Pete Stewart (you!)

**Questions:** Add to PR or implementation branch as needed

**Feedback:** Direct user feedback during testing

---

**Ready to Start?**

👉 Begin with **Phase 1: Status Bar System**
👉 Read `IMPLEMENTATION_PLAN.md` lines 66-269
👉 Create `ccc/status_monitor.py`
👉 Let's build! 🚀

---

*Last updated: November 14, 2025*
