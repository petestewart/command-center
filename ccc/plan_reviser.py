"""
Plan Reviser - AI-powered plan review and suggestion system

This module uses Claude CLI to analyze the current todo list and suggest
improvements, reordering, or additions based on the branch context.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from ccc.claude_chat import ClaudeChat, create_chat
from ccc.todo import list_todos, TodoItem
from ccc.utils import print_error


@dataclass
class PlanSuggestion:
    """Represents a suggestion for plan improvement"""
    type: str  # "add", "remove", "reorder", "modify", "split", "combine"
    description: str
    task_ids: List[int] = None  # Affected task IDs
    details: Optional[str] = None  # Additional details


class PlanReviser:
    """
    Analyzes todo lists and suggests improvements using Claude.

    Capabilities:
    - Identify missing tasks
    - Suggest better task ordering
    - Find tasks that should be split or combined
    - Detect potential blockers
    """

    def __init__(self, branch_name: str, config=None):
        """
        Initialize plan reviser for a branch.

        Args:
            branch_name: Branch name
            config: Optional Config object
        """
        self.branch_name = branch_name
        self.chat = create_chat(branch_name, config)

    def suggest_improvements(
        self,
        additional_context: Optional[str] = None
    ) -> Tuple[List[PlanSuggestion], Optional[str]]:
        """
        Get suggestions for improving the current plan.

        Args:
            additional_context: Optional additional context for Claude

        Returns:
            Tuple of (suggestions, error_message)
            - (list_of_suggestions, None) on success
            - ([], error_msg) on failure
        """
        # Get current todos
        todo_list = list_todos(self.branch_name)

        if not todo_list.items:
            return [], "No todos found. Add some tasks first."

        # Build prompt for Claude
        prompt = self._build_review_prompt(todo_list, additional_context)

        # Get suggestions from Claude
        response, error = self.chat.send_message(prompt, include_context=True)

        if error:
            return [], error

        if not response:
            return [], "No response from Claude"

        # Parse suggestions from response
        suggestions = self._parse_suggestions(response, todo_list)

        return suggestions, None

    def suggest_next_steps(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Ask Claude what to work on next.

        Returns:
            Tuple of (suggestion, error_message)
            - (suggestion_text, None) on success
            - (None, error_msg) on failure
        """
        prompt = """Based on the current todo list and branch status, what should I work on next?

Please consider:
- Which tasks are not blocked
- Task dependencies
- Priority and impact
- Current progress

Provide a clear recommendation."""

        response, error = self.chat.send_message(prompt, include_context=True)

        if error:
            return None, error

        return response, None

    def review_specific_task(
        self,
        task_id: int,
        question: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get Claude's input on a specific task.

        Args:
            task_id: Task ID to review
            question: Optional specific question about the task

        Returns:
            Tuple of (review, error_message)
        """
        # Get the task
        todo_list = list_todos(self.branch_name)
        task = todo_list.get_item(task_id)

        if not task:
            return None, f"Task #{task_id} not found"

        # Build prompt
        if question:
            prompt = f"""Regarding todo #{task_id}: "{task.description}"

{question}"""
        else:
            prompt = f"""Please review todo #{task_id}: "{task.description}"

Consider:
- Is this task clearly defined?
- Are there dependencies or blockers?
- Should it be split into smaller tasks?
- Any suggestions for improvement?"""

        response, error = self.chat.send_message(prompt, include_context=True)

        if error:
            return None, error

        return response, None

    def _build_review_prompt(
        self,
        todo_list,
        additional_context: Optional[str]
    ) -> str:
        """Build prompt asking Claude to review the plan"""
        prompt_parts = []

        prompt_parts.append("Please review the current todo list and suggest improvements.")
        prompt_parts.append("")
        prompt_parts.append("Consider:")
        prompt_parts.append("- Are tasks in the right order?")
        prompt_parts.append("- Are any tasks missing?")
        prompt_parts.append("- Should any tasks be split into smaller pieces?")
        prompt_parts.append("- Should any tasks be combined?")
        prompt_parts.append("- Are there any blockers or dependencies to note?")
        prompt_parts.append("- Is the plan realistic given the current status?")
        prompt_parts.append("")

        if additional_context:
            prompt_parts.append(f"Additional context: {additional_context}")
            prompt_parts.append("")

        prompt_parts.append("Provide specific, actionable suggestions. "
                          "For each suggestion, clearly state what should be changed and why.")

        return "\n".join(prompt_parts)

    def _parse_suggestions(
        self,
        response: str,
        todo_list
    ) -> List[PlanSuggestion]:
        """
        Parse Claude's response into structured suggestions.

        This is a best-effort parser. It looks for common patterns in the response.
        """
        suggestions = []

        # Split response into lines
        lines = response.split('\n')

        current_suggestion = None
        current_description = []

        for line in lines:
            line = line.strip()

            # Look for numbered suggestions (1. 2. etc.)
            numbered_match = re.match(r'^(\d+)[\.\)]\s+(.+)$', line)
            if numbered_match:
                # Save previous suggestion
                if current_suggestion:
                    suggestions.append(PlanSuggestion(
                        type="general",
                        description='\n'.join(current_description),
                    ))

                # Start new suggestion
                current_description = [numbered_match.group(2)]
                current_suggestion = True
                continue

            # Look for bullet points (- * •)
            bullet_match = re.match(r'^[\-\*•]\s+(.+)$', line)
            if bullet_match:
                if current_suggestion:
                    current_description.append(bullet_match.group(1))
                else:
                    # Start new suggestion
                    current_description = [bullet_match.group(1)]
                    current_suggestion = True
                continue

            # Regular line - add to current description if we have one
            if line and current_suggestion:
                current_description.append(line)

        # Save last suggestion
        if current_suggestion and current_description:
            suggestions.append(PlanSuggestion(
                type="general",
                description='\n'.join(current_description),
            ))

        # If we didn't find structured suggestions, treat the whole response as one suggestion
        if not suggestions and response.strip():
            suggestions.append(PlanSuggestion(
                type="general",
                description=response.strip(),
            ))

        return suggestions


def get_plan_reviser(branch_name: str, config=None) -> PlanReviser:
    """
    Get a PlanReviser instance for a branch.

    Args:
        branch_name: Branch name
        config: Optional Config object

    Returns:
        PlanReviser instance
    """
    return PlanReviser(branch_name, config)
