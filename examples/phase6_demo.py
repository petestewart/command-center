"""
Phase 6 Demo: Chat, Questions, and Plan Revision

This script demonstrates the Phase 6 features:
1. Chatting with Claude about a branch
2. Managing agent questions
3. Getting plan reviews and suggestions

Prerequisites:
- Claude CLI installed: npm install -g @anthropic-ai/claude-cli
- Claude CLI authenticated: claude login
- A branch/ticket created: ccc create test-branch
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def demo_chat():
    """Demonstrate chat functionality"""
    print("\n" + "="*60)
    print("DEMO 1: Chat with Claude")
    print("="*60)

    from ccc.claude_chat import create_chat

    branch_name = "test-branch"
    chat = create_chat(branch_name)

    # Verify CLI is available
    is_available, error = chat.verify_cli()
    if not is_available:
        print(f"❌ Error: {error}")
        print("\nPlease install and authenticate Claude CLI:")
        print("  npm install -g @anthropic-ai/claude-cli")
        print("  claude login")
        return

    print(f"✓ Claude CLI is available\n")

    # Example: Send a message
    print("Sending message: 'What's the best approach for error handling?'")
    response, error = chat.send_message(
        "What's the best approach for error handling in this project?"
    )

    if error:
        print(f"❌ Error: {error}")
    else:
        print(f"\n🤖 Claude's response:\n{response}\n")

    # Show history
    print("Chat history:")
    messages = chat.get_history(limit=5)
    for msg in messages:
        role = "You" if msg.role == "user" else "Claude"
        print(f"  {role}: {msg.content[:50]}...")


def demo_questions():
    """Demonstrate question management"""
    print("\n" + "="*60)
    print("DEMO 2: Agent Questions")
    print("="*60)

    from ccc.questions import QuestionManager

    branch_name = "test-branch"
    manager = QuestionManager(branch_name)

    # Post a question
    print("\n1. Agent posts a question:")
    question = manager.post_question(
        agent_id="agent-1",
        question="Should I use Zod or Joi for input validation?",
        context={"file": "src/validators.py", "line": 42}
    )
    print(f"   ✓ Question posted (ID: {question.id})")
    print(f"   Agent: {question.agent_id}")
    print(f"   Question: {question.question}")
    if question.context:
        print(f"   Context: {question.context}")

    # List unanswered questions
    print("\n2. List unanswered questions:")
    unanswered = manager.get_unanswered()
    print(f"   Found {len(unanswered)} unanswered question(s)")

    # Answer a question
    print("\n3. Answer the question:")
    answer = "Use Zod for better TypeScript integration and type inference"
    answered_q = manager.answer_question(question.id, answer)
    print(f"   ✓ Question answered")
    print(f"   Answer: {answered_q.answer}")

    # Show all questions
    print("\n4. All questions:")
    all_questions = manager.get_all()
    for q in all_questions:
        status = "✓ Answered" if q.answered else "⚠ Unanswered"
        print(f"   {status}: {q.question}")


def demo_plan_revision():
    """Demonstrate plan revision"""
    print("\n" + "="*60)
    print("DEMO 3: Plan Revision")
    print("="*60)

    from ccc.plan_reviser import get_plan_reviser
    from ccc.todo import add_todo

    branch_name = "test-branch"

    # Add some sample todos
    print("\n1. Creating sample todo list:")
    todos_to_add = [
        "Add input validation",
        "Implement API endpoints",
        "Write tests",
        "Deploy to staging"
    ]

    for desc in todos_to_add:
        try:
            add_todo(branch_name, desc)
            print(f"   ✓ Added: {desc}")
        except Exception as e:
            print(f"   ⚠ Skipped (may already exist): {desc}")

    # Get plan reviser
    reviser = get_plan_reviser(branch_name)

    # Verify CLI is available
    is_available, error = reviser.chat.verify_cli()
    if not is_available:
        print(f"\n❌ Error: {error}")
        return

    print("\n2. Asking Claude to review the plan...")
    suggestions, error = reviser.suggest_improvements(
        additional_context="Focus on security and performance"
    )

    if error:
        print(f"   ❌ Error: {error}")
    else:
        print(f"   ✓ Received {len(suggestions)} suggestion(s):")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n   {i}. {suggestion.description}")
            if suggestion.details:
                print(f"      Details: {suggestion.details}")

    # Ask what to work on next
    print("\n3. Asking Claude what to work on next...")
    next_step, error = reviser.suggest_next_steps()

    if error:
        print(f"   ❌ Error: {error}")
    else:
        print(f"   ✓ Claude's recommendation:")
        print(f"   {next_step}")


def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("Phase 6 Feature Demonstration")
    print("Replanning & Communication")
    print("="*60)

    print("\nThis demo requires:")
    print("  1. Claude CLI installed (npm install -g @anthropic-ai/claude-cli)")
    print("  2. Claude CLI authenticated (claude login)")
    print("  3. A test branch created (ccc create test-branch)")

    input("\nPress Enter to start the demo...")

    try:
        # Run demos
        demo_chat()
        demo_questions()
        demo_plan_revision()

        print("\n" + "="*60)
        print("Demo Complete!")
        print("="*60)
        print("\nYou can now use these features via:")
        print("  CLI: ccc chat send <branch> '<message>'")
        print("  CLI: ccc plan review <branch>")
        print("  CLI: ccc question list <branch>")
        print("  TUI: Press 'i' for chat, 'R' for reply, 'v' for plan review")

    except Exception as e:
        print(f"\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
