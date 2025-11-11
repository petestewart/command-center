# Command Center - UI Specification

## Design Philosophy

Command Center follows the design principles of successful terminal UIs like LazyGit, htop, and lazydocker:

- Clear visual hierarchy
- Consistent keyboard shortcuts
- Contextual help always visible
- Minimal chrome, maximum content
- Status indicators using symbols and color

## Color Scheme

- **Green**: Active/working status, success states
- **Yellow**: Warning, attention needed
- **Red**: Error, blocked
- **Blue**: Informational highlights
- **Gray**: Inactive/completed items
- **White**: Primary text content

## Main Views

### 1. Ticket List View (Default)

This is the landing view when launching Command Center.

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Command Center                                               [?] Help [q] Quit ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│                                                                              │
│  Active Tickets (3)                                                          │
│                                                                              │
│  ● IN-413  Public API bulk uploads                           ⚙ Working      │
│     Branch: feature/IN-413-bulk-uploads                                     │
│     Agent: Adding input validation                                          │
│     Updated: 2 minutes ago                                                  │
│                                                                              │
│  ● IN-407  Refactor auth middleware                          ✓ Complete     │
│     Branch: feature/IN-407-auth-refactor                                    │
│     Agent: Idle - work complete                                             │
│     Updated: 1 hour ago                                                     │
│                                                                              │
│  ⚠ IN-391  Database migration                                ⏸ Blocked      │
│     Branch: feature/IN-391-db-migration                                     │
│     Agent: Waiting for schema approval                                      │
│     Updated: 3 hours ago                                                    │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
┌─ Actions ────────────────────────────────────────────────────────────────────┐
│ [↑↓] navigate  [Enter] details  [n] new ticket  [d] delete  [r] refresh     │
└──────────────────────────────────────────────────────────────────────────────┘
```

**Status Symbols:**

- `●` Green dot: Active/in progress
- `✓` Green check: Complete
- `⚠` Yellow warning: Needs attention
- `⏸` Gray pause: Blocked/paused
- `⚙` Spinning: Agent actively working

### 2. Ticket Detail View

Displayed when user presses Enter on a ticket in the list view.

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ IN-413: Public API bulk uploads                           [Esc] Back [q] Quit ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│                                                                              │
│  Branch: feature/IN-413-bulk-uploads                                         │
│  Worktree: ~/code/worktrees/IN-413                                           │
│  Created: 2025-11-09 10:23                                                   │
│                                                                              │
│ ┌─ Agent Status ─────────────────────────────────────────────────────────┐  │
│ │ Status: ⚙ Working                                                      │  │
│ │ Current Task: Adding input validation                                  │  │
│ │ Last Update: 2 minutes ago                                             │  │
│ │ Questions: None                                                        │  │
│ └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ ┌─ Git Status ───────────────────────────────────────────────────────────┐  │
│ │ Modified: 3 files                                                      │  │
│ │ Untracked: 1 file                                                      │  │
│ │ Commits ahead: 4                                                       │  │
│ └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
│ ┌─ Recent Changes ───────────────────────────────────────────────────────┐  │
│ │ src/api/bulk-upload.ts        (modified)                               │  │
│ │ src/validators/input.ts       (modified)                               │  │
│ │ tests/api/bulk-upload.test.ts (modified)                               │  │
│ │ docs/API.md                   (untracked)                              │  │
│ └────────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
┌─ Quick Actions ──────────────────────────────────────────────────────────────┐
│ [a] agent terminal  [s] server logs  [t] test terminal  [g] git status      │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 3. Terminal Navigation

When user presses a navigation key (a, s, t), Command Center:

1. Clears the screen
2. Shows a brief transition message
3. Attaches to the tmux session/window

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Attaching to Agent Terminal: IN-413                                          ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

  Connecting to tmux session: ccc-IN-413 (window: agent)

  Press [Ctrl-b] then [q] to return to Command Center



  [Switching now...]
```

Then the full tmux session takes over the terminal.

### 4. Help Overlay

Accessible from any view by pressing `?`.

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Command Center - Help                                         [Esc] Close    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│                                                                              │
│  Navigation                                                                  │
│  ──────────                                                                  │
│  ↑/k         Move selection up                                               │
│  ↓/j         Move selection down                                             │
│  Enter       View ticket details                                             │
│  Esc         Go back / Close overlay                                         │
│  q           Quit Command Center                                             │
│                                                                              │
│  Ticket Management                                                           │
│  ─────────────────                                                           │
│  n           Create new ticket                                               │
│  d           Delete/archive selected ticket                                  │
│  r           Refresh status from all agents                                  │
│                                                                              │
│  Quick Actions (from ticket detail)                                          │
│  ────────────────────────────────                                            │
│  a           Jump to Agent terminal                                          │
│  s           Jump to Server/logs terminal                                    │
│  t           Jump to Tests terminal                                          │
│  g           Show git status                                                 │
│                                                                              │
│  Tips                                                                        │
│  ────                                                                        │
│  • To return from a terminal: Press [Ctrl-b] then [q]                       │
│  • Status updates every 3 seconds automatically                             │
│  • Ticket colors indicate state: Green=active, Yellow=attention, Red=error  │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 5. Create Ticket Dialog

Appears when user presses `n` from the ticket list view.

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Create New Ticket                                         [Esc] Cancel       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│                                                                              │
│  Ticket ID (e.g., IN-413):                                                   │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ IN-█                                                                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Title:                                                                      │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ █                                                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│  Worktree Base Path (leave empty for default: ~/code/worktrees):            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                                                                        │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│                                                                              │
│                          [Tab] next field  [Enter] create                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 6. Status Panel (Phase 2+)

In future phases, a persistent status panel may appear on the right side:

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Active Tickets (3)          ┃ System Status                              ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╋━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│                             │                                            │
│ ● IN-413  Public API        │ ⚙ Active Agents: 2                        │
│   Agent: Working            │ ✓ Build Status: Passing                   │
│   Updated: 2m ago           │ ⚠ Tests: 47/50 passing                    │
│                             │ ● Servers: 1 running                      │
│ ● IN-407  Refactor auth     │                                            │
│   Agent: Idle               │ Last Refresh: 3 seconds ago               │
│   Updated: 1h ago           │                                            │
│                             │                                            │
│ ⚠ IN-391  Database          │                                            │
│   Agent: Blocked            │                                            │
│   Updated: 3h ago           │                                            │
│                             │                                            │
└─────────────────────────────┴────────────────────────────────────────────┘
```

## Keyboard Shortcuts Reference

### Global (Available in all views)

- `?` - Show help overlay
- `q` - Quit application
- `Esc` - Go back / Close dialog
- `Ctrl-c` - Force quit

### Ticket List View

- `↑` or `k` - Move selection up
- `↓` or `j` - Move selection down
- `Enter` - View ticket details
- `n` - Create new ticket
- `d` - Delete/archive selected ticket
- `r` - Refresh all status
- `1`-`9` - Quick select ticket by number

### Ticket Detail View

- `a` - Jump to agent terminal
- `s` - Jump to server terminal
- `t` - Jump to test terminal
- `g` - Show git status (inline view)
- `e` - Edit ticket metadata

### Form/Dialog Views

- `Tab` - Next field
- `Shift-Tab` - Previous field
- `Enter` - Submit
- `Esc` - Cancel

## Visual Design Elements

### Progress Indicators

```
In-progress: ⚙ ⟳ ◐ ◓ ◑ ◒ (animated spinner)
Complete:    ✓ ✔
Blocked:     ⏸ ⏯
Error:       ✗ ⚠
Idle:        ○ ◯
```

### Status Colors

```
Working:   Green    (active, making progress)
Complete:  Gray     (done, ready to archive)
Blocked:   Yellow   (needs attention)
Error:     Red      (failed, broken)
Idle:      Blue     (waiting for instructions)
```

### Layout Grid

- Full screen terminal (80x24 minimum, responsive to larger)
- 2-column layouts use 70/30 split
- Consistent 2-space padding inside panels
- Single-line borders using box-drawing characters
- Section headers use `─` character with labels

### Typography

- Monospace font (inherits from terminal)
- Bold for headers and emphasis
- Dim/gray for secondary information (timestamps, paths)
- Inverse video for selected items

## Accessibility Considerations

- All information conveyed through both color AND symbols
- Keyboard-only navigation (no mouse required)
- High contrast text
- Screen reader compatible (plain text output)
- Consistent layout across views (muscle memory)

## Animation

Minimal animation to reduce distraction:

- Spinner updates every 500ms for "working" status
- Status panel refresh fade (subtle)
- No transitions between views (instant switch)
- Loading states for slow operations (>500ms)

## Error States

### Network/File Access Error

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Error                                                                        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│                                                                              │
│  ⚠ Could not read status file for IN-413                                    │
│                                                                              │
│  Path: ~/.cc-control/IN-413/agent-status.json                               │
│  Error: File not found                                                      │
│                                                                              │
│  This usually means the agent hasn't started yet or the file was deleted.   │
│                                                                              │
│                              [Enter] Retry  [Esc] Dismiss                    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Tmux Session Not Found

```
  ⚠ Warning: Tmux session 'cc-IN-413' not found

  The terminal session for this ticket doesn't exist yet.
  Would you like to create it now?

  [y] Yes, create session  [n] No, go back
```

## Future UI Enhancements

- Split-pane diff viewer
- Inline git log visualization
- Real-time log streaming in panel
- Toast notifications for status changes
- Mini-map of file changes
- Integrated chat interface for replanning
