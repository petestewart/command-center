"""
Claude Chat - Integration with Claude Code CLI for branch communication

This module provides communication with Claude via the Claude Code CLI,
allowing developers to discuss plans, get suggestions, and revise todos.
"""

import subprocess
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict

from ccc.utils import get_branch_dir, print_error, print_info


# Custom exceptions for better error handling
class ClaudeCLIError(Exception):
    """Base exception for Claude CLI errors"""
    pass


class ClaudeCLINotFoundError(ClaudeCLIError):
    """Claude CLI is not installed"""
    def __init__(self):
        super().__init__(
            "Claude Code CLI not found.\n\n"
            "Installation:\n"
            "  npm install -g @anthropic-ai/claude-code\n\n"
            "Or see: https://docs.claude.com/claude-code"
        )


class ClaudeCLINotAuthenticatedError(ClaudeCLIError):
    """Claude CLI is not authenticated"""
    def __init__(self):
        super().__init__(
            "Claude Code CLI not authenticated.\n\n"
            "Please authenticate using the Claude Code interface.\n"
            "This will use your Claude Pro or API subscription."
        )


class ClaudeCLITimeoutError(ClaudeCLIError):
    """Request timed out"""
    def __init__(self, timeout: int):
        super().__init__(
            f"Request timed out after {timeout} seconds.\n\n"
            "Try again or increase timeout in config:\n"
            "  ~/.ccc-control/config.yaml -> claude_timeout: <seconds>"
        )


@dataclass
class ChatMessage:
    """Represents a single chat message"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChatMessage":
        """Create from dictionary loaded from YAML"""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now(timezone.utc)

        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=timestamp
        )


class ClaudeChat:
    """
    Manages communication with Claude via Claude Code CLI.

    Handles:
    - Verifying Claude Code CLI installation and authentication
    - Building context from branch state (todos, git status)
    - Sending messages and receiving responses
    - Persisting chat history
    """

    def __init__(self, branch_name: str, cli_path: str = "claude", timeout: int = 60):
        """
        Initialize Claude chat for a branch.

        Args:
            branch_name: Branch name to chat about
            cli_path: Path to claude CLI binary (default: "claude")
            timeout: Timeout in seconds for CLI calls (default: 60)
        """
        self.branch_name = branch_name
        self.cli_path = cli_path
        self.timeout = timeout
        self.branch_dir = get_branch_dir(branch_name)
        self.history_file = self.branch_dir / "chat-history.yaml"
        self.messages: List[ChatMessage] = []

        # Load existing history
        self._load_history()

    def verify_cli(self) -> Tuple[bool, Optional[str]]:
        """
        Verify that Claude Code CLI is installed and accessible.

        Returns:
            Tuple of (success, error_message)
            - (True, None) if CLI is available
            - (False, error_msg) if there's an issue
        """
        try:
            result = subprocess.run(
                [self.cli_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return True, None

            # CLI exists but returned error
            stderr = result.stderr.strip()
            if "not authenticated" in stderr.lower() or "login" in stderr.lower():
                return False, "Claude CLI not authenticated. Run: claude login"
            return False, f"Claude CLI error: {stderr}"

        except FileNotFoundError:
            return False, (
                "Claude Code CLI not found.\n\n"
                "Install with: npm install -g @anthropic-ai/claude-code\n"
                "Or see: https://docs.claude.com/claude-code"
            )
        except subprocess.TimeoutExpired:
            return False, "Claude CLI check timed out (took more than 5 seconds)"
        except Exception as e:
            return False, f"Failed to verify Claude CLI: {str(e)}"

    def send_message(
        self,
        user_message: str,
        include_context: bool = True
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Send a message to Claude and get a response.

        Args:
            user_message: The user's message
            include_context: Whether to include branch context (default: True)

        Returns:
            Tuple of (response, error_message)
            - (response_text, None) on success
            - (None, error_msg) on failure
        """
        # Verify CLI is available
        is_available, error = self.verify_cli()
        if not is_available:
            return None, error

        # Build the full prompt
        if include_context:
            context = self._build_context()
            full_prompt = f"""{context}

---

User: {user_message}"""
        else:
            full_prompt = user_message

        # Call Claude CLI
        try:
            result = subprocess.run(
                [self.cli_path, "--print", full_prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.branch_dir)
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()

                # Check for authentication issues
                if "not authenticated" in stderr.lower() or "login" in stderr.lower():
                    return None, "Not authenticated. Please authenticate using Claude Code."

                # Generic error
                error_msg = stderr if stderr else "Unknown error from Claude CLI"
                return None, f"Claude CLI error: {error_msg}"

            # Success - extract response
            response = result.stdout.strip()

            if not response:
                return None, "Empty response from Claude (check your connection)"

            # Save to history
            self._add_to_history(user_message, response)

            return response, None

        except subprocess.TimeoutExpired:
            return None, f"Request timed out after {self.timeout} seconds. Try again or increase timeout in config."
        except Exception as e:
            return None, f"Failed to communicate with Claude: {str(e)}"

    def _build_context(self) -> str:
        """
        Build context about the current branch state.

        Includes:
        - Branch name and title
        - Current todos with status
        - Git status summary
        - Recent commit info
        """
        from ccc.ticket import TicketRegistry
        from ccc.todo import list_todos
        from ccc.git_status import get_git_status
        from ccc.build_status import read_build_status
        from ccc.test_status import read_test_status

        context_parts = []

        # Branch info
        registry = TicketRegistry()
        ticket = registry.get(self.branch_name)

        if ticket:
            context_parts.append(f"Branch: {self.branch_name}")
            context_parts.append(f"Title: {ticket.title}")
            context_parts.append(f"Status: {ticket.status}")
            context_parts.append("")

        # Todos
        todo_list = list_todos(self.branch_name)
        if todo_list.items:
            stats = todo_list.progress_stats()
            context_parts.append(f"Todos ({stats['done']}/{stats['total']} complete):")

            for item in todo_list.items[:10]:  # Limit to first 10
                status_icon = {
                    "done": "✓",
                    "in_progress": "⚙",
                    "not_started": "☐",
                    "blocked": "⏸"
                }.get(item.status, "○")

                blocked_info = f" (blocked by #{item.blocked_by})" if item.blocked_by else ""
                assigned_info = f" [{item.assigned_agent}]" if item.assigned_agent else ""

                context_parts.append(
                    f"  {status_icon} {item.id}. {item.description} - {item.status}{blocked_info}{assigned_info}"
                )

            if len(todo_list.items) > 10:
                context_parts.append(f"  ... and {len(todo_list.items) - 10} more")
            context_parts.append("")

        # Git status
        if ticket:
            git_status = get_git_status(ticket.worktree_path, use_cache=True)
            if git_status:
                context_parts.append("Git Status:")
                context_parts.append(f"  Branch: {git_status.current_branch}")
                context_parts.append(f"  Modified files: {len(git_status.modified_files)}")
                context_parts.append(f"  Untracked files: {len(git_status.untracked_files)}")
                context_parts.append(f"  Commits ahead: {git_status.commits_ahead}")
                if git_status.last_commit:
                    context_parts.append(f"  Last commit: {git_status.last_commit}")
                context_parts.append("")

        # Build status
        build_status = read_build_status(self.branch_name)
        if build_status:
            context_parts.append(f"Build Status: {build_status.status}")
            if build_status.errors:
                context_parts.append(f"  Errors: {len(build_status.errors)}")
            context_parts.append("")

        # Test status
        test_status = read_test_status(self.branch_name)
        if test_status and test_status.total > 0:
            context_parts.append(
                f"Test Status: {test_status.passed}/{test_status.total} passing ({test_status.status})"
            )
            if test_status.failures:
                context_parts.append(f"  Failures: {len(test_status.failures)}")
            context_parts.append("")

        # Add instruction
        context_parts.append(
            "You are helping a developer working on this branch. "
            "Provide helpful suggestions and answer questions about the plan, todos, and development approach."
        )

        return "\n".join(context_parts)

    def _add_to_history(self, user_message: str, assistant_response: str):
        """Add messages to chat history and persist to disk"""
        # Add user message
        self.messages.append(ChatMessage(
            role="user",
            content=user_message
        ))

        # Add assistant response
        self.messages.append(ChatMessage(
            role="assistant",
            content=assistant_response
        ))

        # Save to disk
        self._save_history()

    def _load_history(self):
        """Load chat history from disk"""
        if not self.history_file.exists():
            self.messages = []
            return

        try:
            with open(self.history_file, 'r') as f:
                data = yaml.safe_load(f) or {}

            messages_data = data.get('messages', [])
            self.messages = [ChatMessage.from_dict(msg) for msg in messages_data]

        except Exception as e:
            print_error(f"Failed to load chat history: {e}")
            self.messages = []

    def _save_history(self):
        """Save chat history to disk"""
        try:
            # Ensure directory exists
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'branch': self.branch_name,
                'messages': [msg.to_dict() for msg in self.messages]
            }

            with open(self.history_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        except Exception as e:
            print_error(f"Failed to save chat history: {e}")

    def get_history(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """
        Get chat history.

        Args:
            limit: Maximum number of messages to return (None for all)

        Returns:
            List of chat messages, most recent last
        """
        if limit is None:
            return self.messages
        return self.messages[-limit:]

    def clear_history(self):
        """Clear all chat history"""
        self.messages = []
        if self.history_file.exists():
            self.history_file.unlink()


def create_chat(branch_name: str, config=None) -> ClaudeChat:
    """
    Create a ClaudeChat instance with config settings.

    Args:
        branch_name: Branch name
        config: Optional Config object (will load if not provided)

    Returns:
        ClaudeChat instance
    """
    if config is None:
        from ccc.config import load_config
        config = load_config()

    cli_path = getattr(config, 'claude_cli_path', 'claude')
    timeout = getattr(config, 'claude_timeout', 60)

    return ClaudeChat(branch_name, cli_path=cli_path, timeout=timeout)
