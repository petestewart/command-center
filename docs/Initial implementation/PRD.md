# Command Center - Product Requirements Document

## Overview

Command Center (cc) is a terminal-based mission control interface for software developers managing multiple tickets with AI coding agents. It provides a unified view of active work, enables quick navigation between different contexts (agent terminals, server logs, test output), and tracks progress across concurrent development efforts.

## Problem Statement

Modern software developers increasingly work on multiple tickets simultaneously, often with AI coding assistants like Claude Code. This creates several pain points:

1. **Context Switching Overhead**: Developers must mentally track which terminal has which agent, which branch is checked out where, and what the current state of each ticket is.

2. **Lost Visibility**: When agents work autonomously, it's difficult to know what they're doing without explicitly checking their terminal output. Progress and blockers are hidden until explicitly investigated.

3. **Terminal Chaos**: Working on 3-4 tickets means juggling 9-12 terminal windows (agent, server, tests per ticket), leading to constant window switching and lost terminals.

4. **Status Ambiguity**: Without explicit tracking, developers must reconstruct the current state by examining git status, reading terminal scrollback, and remembering what was in progress.

5. **Workflow Interruption**: Simple actions like "check if tests pass on ticket IN-413" require multiple steps: find the right terminal, navigate to directory, remember test command, run it, interpret output.

## Solution

Command Center provides a LazyGit-style TUI that serves as a single pane of glass for multi-ticket development:

### Core Capabilities

**Ticket Registry & Organization**

- Maintains a registry of active tickets with metadata (ID, title, branch, worktree path)
- Each ticket is associated with organized terminal sessions for different contexts
- Simple lifecycle management: create, work on, complete, archive

**Terminal Session Orchestration**

- Automatically manages tmux sessions per ticket with predefined windows
- Provides instant navigation to agent terminals, server logs, or test output
- Eliminates manual terminal management and discovery

**Real-Time Status Visibility**

- Displays current status of agents working on each ticket
- Shows what each agent is currently doing without requiring manual investigation
- Updates automatically as agents make progress or encounter issues

**Unified Navigation Interface**

- Single TUI showing all active tickets and their current state
- Keyboard-driven navigation to any context in one keypress
- Quick return to mission control from any spawned terminal

## How It Works

### Architecture

```
┌─────────────────┐
│   Command       │  ← User interacts with TUI
│   Center TUI    │
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
    ┌────▼─────┐     ┌────▼──────┐
    │  Ticket  │     │   Tmux    │
    │ Registry │     │  Session  │
    │  (YAML)  │     │  Manager  │
    └──────────┘     └─────┬─────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
         ┌────▼───┐   ┌───▼────┐  ┌───▼────┐
         │ Agent  │   │ Server │  │ Tests  │
         │Terminal│   │Terminal│  │Terminal│
         └────────┘   └────────┘  └────────┘
```

### Workflow Example

1. **Starting Work**: Developer runs `ccc create IN-413 "API bulk uploads"`

   - Command Center creates ticket entry in registry
   - Spawns tmux session with three windows
   - Sets up worktree and checks out feature branch

2. **Launching Agent**: Developer attaches to agent terminal and starts Claude Code

   - Claude Code begins working on the ticket
   - Periodically writes status updates to a known file location
   - Command Center polls this file and displays status

3. **Monitoring Progress**: Developer opens Command Center TUI

   - Sees all active tickets in list view
   - Each ticket shows current agent status
   - Can navigate to any ticket for more details

4. **Context Switching**: Developer needs to check server logs for IN-413

   - Presses `s` key while IN-413 is selected
   - Instantly attached to server terminal for that ticket
   - Reviews logs, then presses escape sequence to return to TUI

5. **Verification**: After agent completes work
   - Developer jumps to test terminal with `t` key
   - Runs tests manually to verify
   - Can jump to agent terminal to see what was done
   - Can open IDE to review code changes

## Success Metrics

### Quantitative

- Time to switch between ticket contexts (target: <2 seconds)
- Number of "lost terminal" incidents (target: 0)
- Time spent searching for correct terminal/branch (target: 0)

### Qualitative

- Developer can maintain mental model of 3+ concurrent tickets
- Confidence in agent progress without explicit checking
- Reduced cognitive load from terminal management
- Natural integration into existing development workflow

## User Personas

### Primary: Multi-Tasking Senior Developer

- Works on 2-4 tickets simultaneously
- Uses AI coding assistants for routine tasks
- Values efficiency and keyboard-driven workflows
- Comfortable with terminal-based tools

### Secondary: Tech Lead Overseeing Agent Work

- Monitors multiple agents across team's tickets
- Needs quick visibility into progress and blockers
- Makes architectural decisions requiring context switching
- Reviews code changes across multiple branches

## Technical Requirements

### Platforms

- Linux (primary)
- macOS (secondary)
- Requires tmux 3.0+

### Performance

- TUI must respond to inputs in <100ms
- Status updates should refresh every 2-3 seconds
- Minimal resource usage (<50MB RAM for TUI)

### Integration Points

- Git (for worktree and branch management)
- Tmux (for terminal session management)
- File system (for status tracking)
- Shell environment (for launching terminals, IDEs)

## Non-Goals (Initial Version)

- **Not a task management system**: No ticket assignment, priority management, or team coordination features
- **Not a CI/CD tool**: No automated builds, deployments, or complex test orchestration
- **Not an IDE**: No code editing, diffing, or syntax highlighting within the TUI
- **Not cross-machine**: No synchronization of state across multiple development machines
- **Not agent-controlling**: Does not start, stop, or directly control Claude Code agents

## Future Considerations

- Integration with issue trackers (Jira, Linear, GitHub Issues)
- Built-in diff viewer and code navigation
- Automated build and test execution
- AI-powered status summarization
- Team coordination features
- API testing library integration
- Git operation shortcuts (commit, push, merge)

## Appendix: Key Design Principles

1. **Keyboard First**: Every action should be achievable via keyboard shortcuts
2. **Immediate Visibility**: Status should be visible without explicit requests
3. **Low Friction**: Minimize steps between intention and action
4. **Fail Gracefully**: If agent status unavailable, degrade to basic functionality
5. **Respect Autonomy**: Don't force workflows, enable existing ones
6. **Terminal Native**: Leverage existing tools (tmux, git) rather than reinventing
