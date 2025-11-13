# Phase 6: Replanning & Communication - Implementation Plan

## Overview

**Duration:** 2 weeks  
**Goal:** Enable dynamic plan adjustments and bidirectional agent communication

Phase 6 adds communication features that allow developers to discuss plans with Claude, agents to ask questions, and plans to be revised mid-stream.

---

## Goal

Enable dynamic replanning and bidirectional agent communication

## Key Features

### 6.1 Mini-Chat Interface

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

### 6.2 Agent Questions

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

### 6.3 Plan Revision

- Edit todo list inline
- Add/remove/reorder tasks
- Ask Claude to suggest revisions
- View revision history

## CLI Commands

**Communication commands:**
```bash
# Start a chat about a branch
cc chat <branch>

# Ask Claude to review plan
cc plan review <branch>

# Ask Claude to suggest improvements
cc plan suggest <branch>

# View chat history
cc chat history <branch>

# Reply to agent question
cc reply <branch> <question-id> "Use Zod for better types"
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

### Claude CLI Integration

**Note:** This phase uses the `claude` CLI tool to communicate with Claude via your Claude Pro subscription. No API key required.

```python
import subprocess
import json

class ClaudeChat:
    def __init__(self, branch: str):
        self.branch = branch
        self.history = self.load_history()
        self._verify_claude_cli()
    
    def _verify_claude_cli(self):
        """Verify claude CLI is installed and authenticated"""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-cli")
        except FileNotFoundError:
            raise RuntimeError("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-cli")
    
    def send_message(self, message: str) -> str:
        """Send message to Claude and get response via CLI"""
        # Build context about the branch
        context = self.build_context()
        
        # Combine context and message
        full_prompt = f"""{context}

User question: {message}"""
        
        # Call claude CLI
        try:
            result = subprocess.run(
                ["claude", "chat", "--message", full_prompt],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Claude CLI error: {result.stderr}")
            
            assistant_message = result.stdout.strip()
            
            # Save to history
            self.history.append({
                "role": "user",
                "content": message,
                "timestamp": datetime.now().isoformat()
            })
            self.history.append({
                "role": "assistant",
                "content": assistant_message,
                "timestamp": datetime.now().isoformat()
            })
            
            self.save_history()
            return assistant_message
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude CLI request timed out")
        except Exception as e:
            raise RuntimeError(f"Failed to communicate with Claude: {str(e)}")
    
    def build_context(self) -> str:
        """Build context about current branch state"""
        todos = load_todos(self.branch)
        git_status = get_git_status(self.branch)
        
        return f"""You are helping a developer working on branch {self.branch}.

Current todos:
{self.format_todos(todos)}

Recent changes:
{self.format_git_status(git_status)}

Help the developer make decisions and adjust plans as needed."""
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

### Plan Revision with Claude CLI

```python
class PlanReviser:
    def suggest_revisions(self, branch: str, context: str) -> List[str]:
        """Ask Claude to suggest plan improvements via CLI"""
        todos = load_todos(branch)
        
        prompt = f"""Given this development plan:

{self.format_todos(todos)}

And this context: {context}

Suggest improvements or revisions to the plan. Consider:
- Are tasks in the right order?
- Are any tasks missing?
- Should any tasks be split or combined?
- Are there any blockers to address?

Provide your suggestions as a numbered list."""
        
        try:
            result = subprocess.run(
                ["claude", "chat", "--message", prompt],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Claude CLI error: {result.stderr}")
            
            response = result.stdout.strip()
            return self.parse_suggestions(response)
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude CLI request timed out")
        except Exception as e:
            raise RuntimeError(f"Failed to get plan suggestions: {str(e)}")
```

## TUI Integration

### Chat View

Accessible with `i` (interactive) key from branch detail:

```python
class ChatView(Container):
    def __init__(self, branch: str):
        super().__init__()
        self.branch = branch
        self.chat = ClaudeChat(branch)
    
    def compose(self):
        yield ChatHistory(self.chat.history)
        yield ChatInput()
    
    def on_message_send(self, message: str):
        """Handle user sending a message"""
        # Show loading indicator
        self.show_loading()
        
        # Get response from Claude
        response = self.chat.send_message(message)
        
        # Update UI
        self.refresh_history()
        self.hide_loading()
```

### Question Notifications

```python
class QuestionNotification(Static):
    """Display agent questions"""
    def __init__(self, question: AgentQuestion):
        super().__init__()
        self.question = question
    
    def render(self) -> str:
        return f"""⚠ {self.question.agent_id} asked:
{self.question.question}

[r]eply [i]gnore"""
    
    def action_reply(self):
        self.app.push_screen(ReplyDialog(self.question))
```

## Deliverables

✅ Mini-chat interface  
✅ Claude API integration  
✅ Agent question notifications  
✅ Reply mechanism  
✅ Plan revision UI  
✅ Revision history  

## Success Criteria

### Functionality
✅ Can chat with Claude about branch decisions  
✅ Chat maintains context about branch state  
✅ Agents can post questions  
✅ Developer can reply to questions  
✅ Claude can suggest plan revisions  
✅ Chat history persists  

### User Experience
✅ Chat interface feels natural  
✅ Responses appear quickly (<5 seconds)  
✅ Question notifications are visible but not intrusive  
✅ Plan suggestions are actionable  
✅ Can dismiss or snooze questions  

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

### Claude CLI Settings

Add to `~/.cc-control/config.yaml`:
```yaml
claude:
  cli_path: claude  # Path to claude CLI binary (or just 'claude' if in PATH)
  timeout: 30  # Timeout in seconds for Claude responses
  
chat:
  history_limit: 50  # Max messages to keep
  context_window: 10  # How many recent messages to send
  
questions:
  notification_style: banner  # or "toast", "silent"
  auto_dismiss_after: 3600  # seconds
```

## Dependencies

**Required:**
- Claude CLI tool - Install with: `npm install -g @anthropic-ai/claude-cli`
- Must be authenticated with your Claude Pro account: `claude login`

**No API key needed** - Uses your Claude Pro subscription via the CLI tool.

## Known Limitations

❌ No voice input/output  
❌ No file attachments in chat  
❌ No multi-branch planning discussions  
❌ No team chat (only developer ↔ Claude)  
❌ Limited to text-based communication  

## Future Enhancements (Post-Phase 6)

- Voice input via Whisper
- Attach code snippets to messages
- Multi-branch strategy discussions
- Team collaboration in chat
- AI-powered code suggestions in chat
- Integration with external docs/knowledge bases

## Documentation Updates

Required documentation:
1. **CHAT_INTERFACE.md** - Using the chat feature
2. **AGENT_QUESTIONS.md** - Handling agent questions
3. **PLAN_REVISION.md** - Revising plans with AI
4. **CLAUDE_CLI_SETUP.md** - Installing and authenticating Claude CLI

## Migration Notes

For users upgrading from Phase 5:
- Requires Claude CLI tool (install: `npm install -g @anthropic-ai/claude-cli`)
- Must authenticate CLI: `claude login` (uses your Claude Pro account)
- No API key needed
- New chat history files created per branch
- No breaking changes to existing features
- Chat feature is optional

## Next Steps to Phase 7

After Phase 6 completes:
- Gather feedback on chat usefulness
- Identify common questions/patterns
- Plan API testing tools based on needs
