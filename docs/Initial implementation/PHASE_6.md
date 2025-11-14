# Phase 6: Replanning & Communication - Implementation Plan

## Overview

**Duration:** 2 weeks  
**Goal:** Enable dynamic plan adjustments and bidirectional agent communication

Phase 6 adds communication features that allow developers to discuss plans with Claude, agents to ask questions, and plans to be revised mid-stream.

---

## Goal

Enable dynamic replanning and bidirectional agent communication

## Key Features

### 6.1 Claude Chat Integration

Simple CLI-based chat with Claude about branch decisions:

```bash
ccc chat send feature/IN-413 "Should we use Zod or Joi for validation?"
# Claude: For this TypeScript project, I'd recommend Zod because:
# - Better TypeScript integration
# - Automatic type inference
# - Smaller bundle size
```

### 6.2 Claude Sessions for TODOs

Dedicated Claude Code sessions attached to individual TODO items:

```bash
# Start a Claude session for a specific TODO
ccc session start feature/IN-413 --todo 5 --prompt "Implement the validation logic"

# Session opens in tmux window: claude-#5
# Claude gets context about the specific task and can work on it
```

### 6.3 Agent Questions

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

### 6.4 Plan Revision

- Ask Claude to suggest improvements to todo lists
- Get recommendations for what to work on next
- Review specific tasks with AI assistance

## CLI Commands

**Chat commands:**

```bash
# Send a message to Claude about a branch
ccc chat send <branch> "Should we use Zod or Joi?"

# View chat history
ccc chat history <branch>

# Clear chat history
ccc chat clear <branch>
```

**Session commands:**

```bash
# Start a Claude session for a TODO
ccc session start <branch> --todo <id> --prompt "Custom prompt"

# Resume an existing session
ccc session resume <branch> <session-id>

# Stop/complete a session
ccc session stop <branch> <session-id>
```

**Question commands:**

```bash
# List unanswered questions
ccc question list <branch>

# Reply to a question
ccc question reply <branch> <question-id> "Your answer"

# Dismiss a question
ccc question dismiss <branch> <question-id>
```

**Plan commands:**

```bash
# Get plan review and suggestions
ccc plan review <branch>

# Ask what to work on next
ccc plan next <branch>
```

## Technical Implementation

### Chat Storage

```yaml
# ~/.cc-control/<branch-name>/chat-history.yaml
conversations:
  - timestamp: 2025-11-09T14:30:00Z
    role: user
    message: "Should we use Zod or Joi for validation?"

  - timestamp: 2025-11-09T14:30:15Z
    role: assistant
    message: "For this TypeScript project, I'd recommend Zod..."

  - timestamp: 2025-11-09T14:35:00Z
    role: user
    message: "Can you update the todo list to use Zod?"
```

### Claude Code CLI Integration

**Note:** This phase uses the `claude` (Claude Code) CLI tool for AI assistance. No API key required - uses your Claude Pro subscription.

```python
from ccc.claude_chat import ClaudeChat

class ClaudeChat:
    def __init__(self, branch_name: str, cli_path: str = "claude", timeout: int = 60):
        self.branch_name = branch_name
        self.cli_path = cli_path
        self.timeout = timeout
        self.messages = []

    def send_message(self, user_message: str) -> Tuple[Optional[str], Optional[str]]:
        """Send message to Claude Code and get response"""
        # Verify CLI is available
        is_available, error = self.verify_cli()
        if not is_available:
            return None, error

        # Build context and prompt
        context = self._build_context()
        full_prompt = f"{context}\n\n---\n\nUser: {user_message}"

        # Call Claude Code CLI
        result = subprocess.run(
            [self.cli_path, "--print", full_prompt],
            capture_output=True, text=True, timeout=self.timeout,
            cwd=str(self.branch_dir)
        )

        if result.returncode != 0:
            return None, f"Claude CLI error: {result.stderr}"

        response = result.stdout.strip()
        if not response:
            return None, "Empty response from Claude"

        # Save to history
        self._add_to_history(user_message, response)
        return response, None
```

### Claude Session Management

```python
@dataclass
class ClaudeSession:
    session_id: str
    todo_id: int
    branch_name: str
    tmux_window_name: str  # e.g., "claude-#5"
    status: str = "running"  # "starting", "running", "completed", "error"

class ClaudeSessionManager:
    def start_session_for_todo(self, todo_id: int, custom_prompt: Optional[str] = None):
        """Start a Claude Code session for a TODO item in tmux"""
        # Create tmux window with Claude session
        cmd = f'claude --session-id {session_id} {shlex.quote(prompt)}'
        window = tmux_session.new_window(f"claude-#{todo_id}")
        window.send_keys(f"cd {worktree_path}", enter=True)
        window.send_keys(cmd, enter=True)

    def resume_session(self, session_id: str):
        """Resume an existing Claude session"""
        cmd = f"claude --resume {session_id}"
        pane.send_keys(cmd, enter=True)
```

### Agent Questions System

```python
@dataclass
class AgentQuestion:
    id: str
    timestamp: datetime
    agent_id: str
    question: str
    answered: bool
    answer: Optional[str] = None
    answer_timestamp: Optional[datetime] = None

class QuestionManager:
    def post_question(self, branch: str, agent_id: str, question: str):
        """Agent posts a question"""
        q = AgentQuestion(
            id=generate_id(),
            timestamp=datetime.now(),
            agent_id=agent_id,
            question=question,
            answered=False
        )
        self.save_question(branch, q)
        return q.id

    def answer_question(self, branch: str, question_id: str, answer: str):
        """Developer answers a question"""
        question = self.load_question(branch, question_id)
        question.answered = True
        question.answer = answer
        question.answer_timestamp = datetime.now()
        self.save_question(branch, question)
```

### Plan Revision with Claude

```python
class PlanReviser:
    def suggest_improvements(self, additional_context: Optional[str] = None) -> List[PlanSuggestion]:
        """Get AI suggestions for improving the todo list"""
        prompt = self._build_review_prompt(todo_list, additional_context)

        response, error = self.chat.send_message(prompt, include_context=True)
        if error:
            return [], error

        return self._parse_suggestions(response, todo_list)

    def suggest_next_steps(self) -> Tuple[Optional[str], Optional[str]]:
        """Ask Claude what to work on next"""
        prompt = """Based on the current todo list and branch status, what should I work on next?

Consider:
- Which tasks are not blocked
- Task dependencies
- Priority and impact
- Current progress

Provide a clear recommendation."""

        return self.chat.send_message(prompt, include_context=True)
```

## TUI Integration

### Chat Dialogs

Modal dialogs for chat and question management:

```python
class QuickChatDialog(ModalScreen):
    """Quick chat dialog for sending a single message"""
    def compose(self):
        yield Static(f"[bold]Quick Chat: {self.branch_name}[/bold]")
        yield TextArea(id="message-input", language="markdown")
        yield Button("Send", id="send", variant="primary")

    def send_message(self):
        """Send message to Claude in background thread"""
        from ccc.claude_chat import create_chat
        chat = create_chat(self.branch_name)
        response, error = chat.send_message(message)

class ReplyToQuestionDialog(ModalScreen):
    """Dialog for replying to agent questions"""
    def compose(self):
        yield Static(f"[bold]Reply to Question from {question.agent_id}[/bold]")
        yield Static(f"Question: {question.question}")
        yield TextArea(id="answer-input")
        yield Button("Submit", id="submit", variant="primary")
```

### Question Notifications

Banner notifications for unanswered questions:

```python
class QuestionNotificationBanner(Static):
    """Banner showing unanswered question count"""
    def render(self):
        if self.question_count > 0:
            return f"⚠ {self.question_count} unanswered questions - Press 'R' to reply"
        return ""
```

## Deliverables

✅ Claude Chat CLI integration
✅ Claude Sessions for TODOs
✅ Agent question system
✅ Question reply mechanism
✅ Plan revision with AI suggestions
✅ TUI dialogs for chat and questions

## Success Criteria

### Functionality

✅ Can chat with Claude via CLI about branch decisions
✅ Chat maintains context about todos, git status, build status
✅ Can start Claude sessions attached to TODO items
✅ Agents can post questions with context
✅ Developer can reply to/dismiss questions via CLI/TUI
✅ Claude can suggest plan improvements and next steps
✅ Chat history and session data persist

### User Experience

✅ CLI commands are intuitive and discoverable
✅ Claude responses include relevant branch context
✅ Question notifications appear in TUI banner
✅ Plan suggestions consider current branch state
✅ Sessions integrate with existing tmux workflow

### Integration

✅ Chat understands current todos  
✅ Chat aware of git status  
✅ Suggestions can be applied to todo list  
✅ Questions link to relevant code/files

## Testing Plan

### Chat Testing

- Send various questions to Claude
- Verify responses are relevant
- Test with long conversation history
- Verify history persists across sessions

### Agent Questions Testing

- Agent posts question
- Verify notification appears in TUI
- Reply to question
- Verify reply is saved
- Test multiple unanswered questions

### Plan Revision Testing

- Ask for plan suggestions
- Verify suggestions make sense
- Apply suggestions to todo list
- Test with various plan complexities

## Configuration

### Claude Code Settings

Add to `~/.ccc-control/config.yaml`:

```yaml
# Phase 6: Claude Code & Communication
claude_cli_path: claude # Path to claude CLI binary (default: 'claude')
claude_timeout: 30 # Timeout in seconds for Claude responses
chat_history_limit: 50 # Max messages to keep in chat history
chat_context_window: 10 # Recent messages to include in context
questions_notification_style: banner # "banner", "toast", or "silent"
questions_auto_dismiss: 3600 # Auto-dismiss questions after N seconds
```

## Dependencies

**Required:**

- Claude Code CLI tool - Install with: `npm install -g @anthropic-ai/claude-code`
- Must be authenticated with your Claude account

**No API key needed** - Uses your Claude Pro subscription via the CLI tool.

## Known Limitations

❌ No rich TUI chat interface (CLI-only)
❌ Claude sessions require tmux integration
❌ No voice input/output
❌ No file attachments in chat
❌ No multi-branch planning discussions
❌ No team collaboration features

## Future Enhancements (Post-Phase 6)

- Voice input via Whisper
- Attach code snippets to messages
- Multi-branch strategy discussions
- Team collaboration in chat
- AI-powered code suggestions in chat
- Integration with external docs/knowledge bases

## Documentation Updates

Required documentation:

1. **PHASE_6_USAGE.md** - Complete usage guide for all Phase 6 features
2. **AGENT_QUESTIONS.md** - Handling agent questions system
3. **PLAN_REVISION.md** - AI-powered plan review and suggestions
4. **CLAUDE_CODE_SETUP.md** - Installing and using Claude Code CLI

## Migration Notes

For users upgrading from Phase 5:

- Requires Claude Code CLI tool (install: `npm install -g @anthropic-ai/claude-code`)
- Must authenticate with Claude Code (uses your Claude Pro subscription)
- No API key needed
- New data files created per branch: `chat-history.yaml`, `questions.yaml`, `claude-sessions.yaml`
- No breaking changes to existing features
- All new features are optional

## Next Steps to Phase 7

After Phase 6 completes:

- Gather feedback on chat usefulness
- Identify common questions/patterns
- Plan API testing tools based on needs
