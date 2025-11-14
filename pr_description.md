## PR: Implement Phase 6 - Replanning & Communication with Claude Code Integration

### Overview

This PR implements Phase 6 of the Command Center project, adding AI-powered communication and replanning capabilities using Claude Code CLI integration. The implementation enables developers to chat with Claude, launch focused AI sessions for TODOs, manage agent questions, and get AI-powered plan suggestions.

### Key Features Implemented

#### 🤖 Claude Chat Integration

- **CLI-based chat** with Claude Code for branch-specific discussions
- **Context-aware responses** including todos, git status, build/test status
- **Persistent chat history** stored per branch
- **CLI commands**: `ccc chat send`, `ccc chat history`, `ccc chat clear`

#### 🎯 Claude Sessions for TODOs

- **Dedicated Claude sessions** attached to individual TODO items
- **Tmux integration** - sessions run in named windows (`claude-#<todo_id>`)
- **Session persistence** with automatic todo assignment updates
- **Resume capability** for continued conversations
- **CLI/TUI access** for session management

#### 💬 Agent Questions System

- **Asynchronous communication** allowing agents to post questions
- **Question lifecycle management** (post, answer, dismiss)
- **TUI notifications** with banner alerts for unanswered questions
- **Context preservation** including file paths and line numbers
- **CLI commands**: `ccc question list`, `ccc question reply`, `ccc question dismiss`

#### 📋 AI-Powered Plan Revision

- **Intelligent suggestions** for improving todo lists
- **Context-aware recommendations** considering current branch state
- **Next-step guidance** from Claude
- **CLI commands**: `ccc plan review`, `ccc plan next`

### Technical Implementation

#### New Core Modules

- **`ccc/claude_chat.py`**: Claude Code CLI integration with context building
- **`ccc/claude_session.py`**: Session management with tmux integration
- **`ccc/questions.py`**: Agent question management system
- **`ccc/plan_reviser.py`**: AI-powered plan analysis and suggestions

#### TUI Enhancements

- **Question notification banner** in main interface
- **Reply dialogs** for agent questions
- **Session management actions** (start, resume, view)
- **New keyboard shortcuts**: `R` (reply), `s` (start session), `S` (resume), `v` (view)

#### CLI Extensions

- **Chat command group** with send/history/clear subcommands
- **Plan command group** with review/next subcommands
- **Question command group** with list/reply/dismiss subcommands
- **Configuration support** for Claude CLI settings

#### Configuration Updates

```yaml
# New Phase 6 settings
claude_cli_path: claude
claude_timeout: 30
chat_history_limit: 50
chat_context_window: 10
questions_notification_style: banner
questions_auto_dismiss: 3600
```

### Files Added/Modified

#### New Files

- `ccc/claude_chat.py` - Claude Code CLI integration
- `ccc/claude_session.py` - Session management
- `ccc/questions.py` - Agent questions system
- `ccc/plan_reviser.py` - Plan revision logic
- `ccc/tui/chat_dialogs.py` - TUI dialogs for chat/questions
- `ccc/tui/chat_widgets.py` - Question notification widgets
- `examples/phase6_demo.py` - Comprehensive demo script
- `tests/test_claude_chat.py` - Unit tests

#### Modified Files

- `ccc/cli.py` - Added chat/plan/question command groups
- `ccc/config.py` - Added Claude and question settings
- `ccc/tui/app.py` - Added TUI bindings and actions
- `docs/PHASE_6.md` - Updated to reflect implementation
- `docs/PHASE_6_USAGE.md` - Complete usage guide

### Data Storage

Phase 6 adds new per-branch data files:

- `chat-history.yaml` - Conversation persistence
- `questions.yaml` - Agent questions and answers
- `claude-sessions.yaml` - Session metadata

### Dependencies

- **Claude Code CLI**: `npm install -g @anthropic-ai/claude-code`
- **Authentication**: `claude login` (uses Claude Pro subscription)
- **No API keys required** - subscription-based authentication

### Testing

- **Unit tests** for core functionality (`tests/test_claude_chat.py`)
- **Demo script** showcasing all features (`examples/phase6_demo.py`)
- **Integration testing** with existing branch/tmux infrastructure

### Architecture Decisions

1. **Claude Code vs Claude CLI**: Chose Claude Code for its session persistence and tmux integration
2. **Sessions over Chat UI**: Implemented dedicated sessions instead of rich chat interface for better workflow integration
3. **CLI-First Design**: Prioritized CLI commands with minimal TUI additions for broad accessibility
4. **Agent Questions**: Built asynchronous question system for non-blocking agent communication

### Usage Examples

```bash
# Chat with Claude about a branch decision
ccc chat send feature/api "Should we use Zod or Joi for validation?"

# Start a Claude session for a TODO
ccc session start feature/api --todo 5 --prompt "Implement validation"

# Get plan suggestions
ccc plan review feature/api

# Handle agent questions
ccc question list feature/api
ccc question reply feature/api <id> "Use Zod for better types"
```

### TUI Integration

- Press `R` to reply to unanswered questions
- Press `s` to start Claude session for selected TODO
- Press `S` to resume existing session
- Press `v` to view/switch to active session

### Migration Notes

- **New dependencies**: Requires Claude Code CLI installation
- **New data files**: Creates additional YAML files per branch
- **Optional features**: All Phase 6 features are opt-in
- **No breaking changes**: Existing functionality remains unchanged

### Future Enhancements

- Rich TUI chat interface
- Voice input integration
- Multi-branch planning
- Team collaboration features
- Code suggestion integration

Closes: Phase 6 implementation
Implements: Claude Code integration, AI-assisted development workflow
Related: #10, #11, #12 (Phase 5 implementation)

---

**Ready for review and testing!** The implementation provides a solid foundation for AI-assisted development with comprehensive CLI and TUI integration.
