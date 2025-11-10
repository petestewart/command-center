"""
Basic tests for ticket functionality
"""

from datetime import datetime, timezone
from cc.ticket import Ticket, create_ticket


def test_create_ticket():
    """Test creating a ticket instance."""
    ticket = create_ticket(
        ticket_id="TEST-001",
        title="Test Ticket",
        branch="feature/TEST-001-test-ticket",
        worktree_path="/tmp/test-001"
    )

    assert ticket.id == "TEST-001"
    assert ticket.title == "Test Ticket"
    assert ticket.branch == "feature/TEST-001-test-ticket"
    assert ticket.worktree_path == "/tmp/test-001"
    assert ticket.tmux_session == "cc-TEST-001"
    assert ticket.status == "active"


def test_ticket_to_dict():
    """Test converting ticket to dictionary."""
    ticket = create_ticket(
        ticket_id="TEST-002",
        title="Another Test",
        branch="feature/test",
        worktree_path="/tmp/test"
    )

    ticket_dict = ticket.to_dict()

    assert ticket_dict['id'] == "TEST-002"
    assert ticket_dict['title'] == "Another Test"
    assert 'created_at' in ticket_dict
    assert 'updated_at' in ticket_dict


def test_ticket_from_dict():
    """Test creating ticket from dictionary."""
    data = {
        'id': 'TEST-003',
        'title': 'Dict Test',
        'branch': 'feature/test',
        'worktree_path': '/tmp/test',
        'tmux_session': 'cc-TEST-003',
        'status': 'active',
        'created_at': '2025-11-10T12:00:00+00:00',
        'updated_at': '2025-11-10T12:00:00+00:00',
    }

    ticket = Ticket.from_dict(data)

    assert ticket.id == 'TEST-003'
    assert ticket.title == 'Dict Test'
    assert isinstance(ticket.created_at, datetime)
