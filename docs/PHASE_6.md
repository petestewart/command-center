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

### Claude API Integration

```python
import anthropic

class ClaudeChat:
    def __init__(self, branch: str):
        self.branch = branch
        self.client = anthropic.Anthropic()
        self.history = self.load_history()
    
    def send_message(self, message: str) -> str:
        """Send message to Claude and get response"""
        # Build context about the branch
        context = self.build_context()
        
        # Add message to history
        self.history.append({
            "role": "user",
            "content": message
        })
        
        # Get response from Claude
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=context,
            messages=self.history
        )
        
        # Save response to history
        assistant_message = response.content[0].text
        self.history.append({
            "role": "assistant",
            "content": assistant_message
        })
        
        self.save_history()
        return assistant_message
    
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

### Plan Revision with AI

```python
class PlanReviser:
    def suggest_revisions(self, branch: str, context: str) -> List[str]:
        """Ask Claude to suggest plan improvements"""
        todos = load_todos(branch)
        
        prompt = f"""Given this development plan:

{self.format_todos(todos)}

And this context: {context}

Suggest improvements or revisions to the plan. Consider:
- Are tasks in the right order?
- Are any tasks missing?
- Should any tasks be split or combined?
- Are there any blockers to address?"""
        
        response = self.claude_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self.parse_suggestions(response.content[0].text)
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

### Claude API Settings

Add to `~/.cc-control/config.yaml`:
```yaml
claude:
  api_key: ${ANTHROPIC_API_KEY}  # Read from environment
  model: claude-sonnet-4-20250514
  max_tokens: 1000
  
chat:
  history_limit: 50  # Max messages to keep
  context_window: 10  # How many recent messages to send
  
questions:
  notification_style: banner  # or "toast", "silent"
  auto_dismiss_after: 3600  # seconds
```

## Dependencies

New dependencies required:
- `anthropic` - Official Anthropic Python SDK

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
4. **ANTHROPIC_API.md** - Setting up API access

## Migration Notes

For users upgrading from Phase 5:
- Requires Anthropic API key (set ANTHROPIC_API_KEY)
- New chat history files created per branch
- No breaking changes to existing features
- Chat feature is optional

## Next Steps to Phase 7

After Phase 6 completes:
- Gather feedback on chat usefulness
- Identify common questions/patterns
- Plan API testing tools based on needs
