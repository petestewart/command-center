# Phase 6: Replanning & Communication - Usage Guide

Phase 6 adds AI-powered communication features using Claude CLI, enabling developers to chat about decisions, get plan reviews, and handle agent questions.

## Prerequisites

Before using Phase 6 features, you need to install and authenticate the Claude CLI:

```bash
# Install Claude CLI
npm install -g @anthropic-ai/claude-cli

# Authenticate (uses your Claude Pro subscription)
claude login
```

**No API key needed!** The Claude CLI uses your Claude Pro subscription.

## Features

### 1. Interactive Chat

Chat with Claude about your branch, decisions, and implementation approaches.

#### CLI Usage

```bash
# Send a message
ccc chat send feature/IN-413 "Should I use Zod or Joi for validation?"

# View chat history
ccc chat history feature/IN-413

# View recent messages
ccc chat history feature/IN-413 --limit 10

# Clear chat history
ccc chat clear feature/IN-413
```

#### TUI Usage

Press **`i`** (interactive) from the branch detail view to open the chat interface.

Features:
- See full conversation history
- Type messages in real-time
- Get responses with full branch context
- Auto-scroll to latest messages

### 2. Agent Questions

Agents can post questions that appear as notifications in the TUI, allowing asynchronous communication when agents need input.

#### CLI Usage

```bash
# List unanswered questions
ccc question list feature/IN-413

# List all questions (including answered)
ccc question list feature/IN-413 --all

# Reply to a question
ccc question reply feature/IN-413 <question-id> "Use Zod for better TypeScript support"

# Dismiss a question
ccc question dismiss feature/IN-413 <question-id>
```

#### TUI Usage

- Questions appear as yellow banners when unanswered
- Press **`R`** (capital R) to reply to the first unanswered question
- Notification shows: "⚠ 2 unanswered questions - Press 'r' to reply"

#### Programmatic API (for agents)

```python
from ccc.questions import QuestionManager

# Post a question
manager = QuestionManager("feature/IN-413")
question = manager.post_question(
    agent_id="agent-1",
    question="Should I use async/await or callbacks?",
    context={
        "file": "src/api.py",
        "line": 42
    }
)

# Check for answers
if question.answered:
    print(f"Answer: {question.answer}")
```

### 3. Plan Review & Suggestions

Get AI-powered suggestions for improving your todo list and development plan.

#### CLI Usage

```bash
# Get plan review with suggestions
ccc plan review feature/IN-413

# Add context to the review
ccc plan review feature/IN-413 --context "Focus on security"

# Ask what to work on next
ccc plan next feature/IN-413
```

#### TUI Usage

Press **`v`** (view) from the branch detail view to open the plan review interface.

Features:
- See all suggestions in a scrollable list
- Refresh suggestions with latest context
- Suggestions consider current todos, git status, and build/test status

#### Example Output

```
Plan Review: feature/IN-413
Received 3 suggestion(s)

1. Consider splitting "Add validation" into smaller tasks
   Details: Validation should be broken down by:
   - Input sanitization
   - Schema validation
   - Error handling

2. Add error handling before deployment tasks
   Details: Task 4 (Deploy) depends on error handling being complete.
   Consider adding this as task 2.5.

3. Integration tests should come before deployment
   Details: Move "Write tests" before "Deploy to staging"
```

## Configuration

Add Claude CLI settings to `~/.ccc-control/config.yaml`:

```yaml
# Phase 6: Claude CLI & Communication
claude_cli_path: claude  # Path to CLI (or 'claude' if in PATH)
claude_timeout: 30  # Timeout in seconds
chat_history_limit: 50  # Max messages to keep
chat_context_window: 10  # Recent messages in context
questions_notification_style: banner  # or "toast", "silent"
questions_auto_dismiss: 3600  # Auto-dismiss after N seconds
```

## Context Awareness

When you chat with Claude or request plan reviews, Claude receives rich context about your branch:

- **Branch info**: Name, title, status
- **Todos**: All tasks with their status, assignments, and blockers
- **Git status**: Modified files, commits ahead, last commit
- **Build status**: Pass/fail status, errors, warnings
- **Test status**: Pass/fail ratios, specific failures

This means Claude's suggestions are tailored to your specific situation!

## TUI Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| **i** | Interactive Chat | Open chat interface for the selected branch |
| **R** | Reply to Question | Reply to first unanswered agent question |
| **v** | Plan Review | Get AI suggestions for improving the plan |

## Common Workflows

### 1. Getting Help with a Decision

```bash
# Start a conversation
ccc chat send feature/api "What's the best way to handle rate limiting?"

# Follow up
ccc chat send feature/api "Should rate limits be per-user or per-IP?"

# View the full conversation
ccc chat history feature/api
```

### 2. Handling Agent Questions

**Agent posts question** → **Notification appears in TUI** → **Developer replies**

```bash
# Agent (programmatically)
manager.post_question("agent-1", "Use Redis or Memcached for caching?")

# Developer (CLI)
ccc question list feature/api
ccc question reply feature/api <id> "Use Redis for persistence support"

# Or use TUI: Press 'R' to reply
```

### 3. Plan Optimization

```bash
# Get initial plan review
ccc plan review feature/api

# Ask about priorities
ccc plan next feature/api

# Adjust todos based on suggestions
ccc todo add feature/api "Add rate limiting middleware"
ccc todo move feature/api 5 2  # Reorder based on suggestions
```

## Storage

Phase 6 data is stored per branch:

```
~/.ccc-control/
└── <branch-name>/
    ├── chat-history.yaml    # Conversation messages
    ├── questions.yaml       # Agent questions and answers
    ├── todos.yaml          # Existing todo list
    └── status.yaml         # Existing status info
```

## Troubleshooting

### "Claude CLI not found"

```bash
npm install -g @anthropic-ai/claude-cli
```

### "Claude CLI not authenticated"

```bash
claude login
```

This will open a browser window to authenticate with your Claude Pro account.

### "Request timed out"

Increase timeout in config:

```yaml
claude_timeout: 60  # Increase to 60 seconds
```

### "Empty response from Claude"

Check your internet connection and try again. The CLI requires network access.

## Privacy & Security

- All communication goes through the Claude CLI
- Uses your Claude Pro subscription
- No API keys stored locally
- Chat history is stored locally in YAML files
- Only branch context is sent to Claude (no credentials or secrets)

## Examples

See `examples/phase6_demo.py` for a complete demonstration of all Phase 6 features.

Run the demo:

```bash
python examples/phase6_demo.py
```

## What's Next?

Phase 6 enables bidirectional communication and dynamic planning. Future enhancements could include:

- Voice input via Whisper
- Multi-branch strategic planning
- Team collaboration features
- Integration with external documentation
- AI-powered code suggestions in chat

---

**Questions or issues?** Open an issue on GitHub or check the troubleshooting section above.
