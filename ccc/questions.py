"""
Agent Questions - System for agents to ask developers questions

This module allows AI agents to post questions when they need clarification
or decisions from the developer. Questions appear as notifications in the TUI
and can be replied to via CLI or TUI.
"""

import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
import uuid

from ccc.utils import get_branch_dir, print_error


@dataclass
class AgentQuestion:
    """Represents a question posted by an agent"""

    id: str
    agent_id: str
    question: str
    timestamp: datetime
    answered: bool = False
    answer: Optional[str] = None
    answer_timestamp: Optional[datetime] = None
    context: Optional[Dict[str, Any]] = None  # Additional context (file, line, etc.)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization"""
        data = {
            'id': self.id,
            'agent_id': self.agent_id,
            'question': self.question,
            'timestamp': self.timestamp.isoformat(),
            'answered': self.answered,
        }

        if self.answer:
            data['answer'] = self.answer
        if self.answer_timestamp:
            data['answer_timestamp'] = self.answer_timestamp.isoformat()
        if self.context:
            data['context'] = self.context

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentQuestion":
        """Create from dictionary loaded from YAML"""
        timestamp = data.get('timestamp')
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        answer_timestamp = data.get('answer_timestamp')
        if isinstance(answer_timestamp, str):
            answer_timestamp = datetime.fromisoformat(answer_timestamp)

        return cls(
            id=data['id'],
            agent_id=data['agent_id'],
            question=data['question'],
            timestamp=timestamp,
            answered=data.get('answered', False),
            answer=data.get('answer'),
            answer_timestamp=answer_timestamp,
            context=data.get('context')
        )


class QuestionManager:
    """
    Manages agent questions for a branch.

    Handles:
    - Posting new questions
    - Answering questions
    - Listing unanswered/all questions
    - Persisting questions to disk
    """

    def __init__(self, branch_name: str):
        """
        Initialize question manager for a branch.

        Args:
            branch_name: Branch name
        """
        self.branch_name = branch_name
        self.branch_dir = get_branch_dir(branch_name)
        self.questions_file = self.branch_dir / "questions.yaml"
        self.questions: List[AgentQuestion] = []

        # Load existing questions
        self._load_questions()

    def post_question(
        self,
        agent_id: str,
        question: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentQuestion:
        """
        Post a new question from an agent.

        Args:
            agent_id: ID of the agent posting the question
            question: The question text
            context: Optional context (file path, line number, etc.)

        Returns:
            The created AgentQuestion
        """
        new_question = AgentQuestion(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            question=question,
            timestamp=datetime.now(timezone.utc),
            context=context
        )

        self.questions.append(new_question)
        self._save_questions()

        return new_question

    def answer_question(
        self,
        question_id: str,
        answer: str
    ) -> Optional[AgentQuestion]:
        """
        Answer a question.

        Args:
            question_id: ID of the question to answer
            answer: The answer text

        Returns:
            The updated AgentQuestion, or None if not found
        """
        question = self.get_question(question_id)
        if not question:
            return None

        question.answered = True
        question.answer = answer
        question.answer_timestamp = datetime.now(timezone.utc)

        self._save_questions()

        return question

    def get_question(self, question_id: str) -> Optional[AgentQuestion]:
        """
        Get a question by ID.

        Args:
            question_id: Question ID

        Returns:
            AgentQuestion or None if not found
        """
        for q in self.questions:
            if q.id == question_id:
                return q
        return None

    def get_unanswered(self) -> List[AgentQuestion]:
        """
        Get all unanswered questions.

        Returns:
            List of unanswered questions, ordered by timestamp (oldest first)
        """
        unanswered = [q for q in self.questions if not q.answered]
        return sorted(unanswered, key=lambda q: q.timestamp)

    def get_all(self, limit: Optional[int] = None) -> List[AgentQuestion]:
        """
        Get all questions.

        Args:
            limit: Maximum number of questions to return (most recent)

        Returns:
            List of all questions, ordered by timestamp (most recent first)
        """
        sorted_questions = sorted(self.questions, key=lambda q: q.timestamp, reverse=True)
        if limit:
            return sorted_questions[:limit]
        return sorted_questions

    def dismiss_question(self, question_id: str) -> bool:
        """
        Dismiss (remove) a question without answering.

        Args:
            question_id: ID of question to dismiss

        Returns:
            True if question was found and removed, False otherwise
        """
        initial_count = len(self.questions)
        self.questions = [q for q in self.questions if q.id != question_id]

        if len(self.questions) < initial_count:
            self._save_questions()
            return True

        return False

    def clear_answered(self):
        """Remove all answered questions"""
        self.questions = [q for q in self.questions if not q.answered]
        self._save_questions()

    def _load_questions(self):
        """Load questions from disk"""
        if not self.questions_file.exists():
            self.questions = []
            return

        try:
            with open(self.questions_file, 'r') as f:
                data = yaml.safe_load(f) or {}

            questions_data = data.get('questions', [])
            self.questions = [AgentQuestion.from_dict(q) for q in questions_data]

        except Exception as e:
            print_error(f"Failed to load questions: {e}")
            self.questions = []

    def _save_questions(self):
        """Save questions to disk"""
        try:
            # Ensure directory exists
            self.questions_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'branch': self.branch_name,
                'questions': [q.to_dict() for q in self.questions]
            }

            with open(self.questions_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        except Exception as e:
            print_error(f"Failed to save questions: {e}")


def get_question_manager(branch_name: str) -> QuestionManager:
    """
    Get a QuestionManager instance for a branch.

    Args:
        branch_name: Branch name

    Returns:
        QuestionManager instance
    """
    return QuestionManager(branch_name)


def has_unanswered_questions(branch_name: str) -> bool:
    """
    Check if a branch has any unanswered questions.

    Args:
        branch_name: Branch name

    Returns:
        True if there are unanswered questions
    """
    manager = QuestionManager(branch_name)
    return len(manager.get_unanswered()) > 0
