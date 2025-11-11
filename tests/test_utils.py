"""
Unit tests for utils module.
"""

import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from ccc.utils import (
    get_cccc_home,
    get_ticket_dir,
    validate_ticket_id,
    format_time_ago,
    expand_path,
    get_tmux_session_name,
    get_branch_name,
    truncate_string,
)


class TestPaths:
    """Tests for path utility functions."""

    @patch("pathlib.Path.home")
    def test_get_cccc_home(self, mock_home):
        """Test getting CCC home directory."""
        mock_home.return_value = Path("/home/testuser")

        with patch.object(Path, "mkdir") as mock_mkdir:
            home = get_cccc_home()

        assert home == Path("/home/testuser/.ccc-control")
        mock_mkdir.assert_called_once_with(exist_ok=True)

    @patch("ccc.utils.get_cccc_home")
    def test_get_ticket_dir(self, mock_get_home):
        """Test getting ticket directory."""
        mock_home_path = MagicMock()
        mock_home_path.__truediv__ = lambda self, x: Path(f"/home/user/.ccc-control/{x}")
        mock_get_home.return_value = mock_home_path

        with patch.object(Path, "mkdir"):
            ticket_dir = get_ticket_dir("TEST-001")

        # Just verify it was called correctly
        mock_get_home.assert_called_once()


class TestValidation:
    """Tests for validation functions."""

    def test_validate_ticket_id_valid(self):
        """Test validating valid ticket IDs."""
        assert validate_ticket_id("IN-413") is True
        assert validate_ticket_id("PROJ-123") is True
        assert validate_ticket_id("ABC-1") is True
        assert validate_ticket_id("TICKET-9999") is True

    def test_validate_ticket_id_invalid(self):
        """Test validating invalid ticket IDs."""
        assert validate_ticket_id("in-413") is False  # lowercase
        assert validate_ticket_id("IN413") is False  # no hyphen
        assert validate_ticket_id("IN-") is False  # no number
        assert validate_ticket_id("-413") is False  # no prefix
        assert validate_ticket_id("IN-ABC") is False  # letters after hyphen
        assert validate_ticket_id("123-456") is False  # no letter prefix
        assert validate_ticket_id("") is False  # empty string


class TestTimeFormatting:
    """Tests for time formatting functions."""

    def test_format_time_ago_just_now(self):
        """Test formatting time that's less than a minute ago."""
        now = datetime.now(timezone.utc)

        result = format_time_ago(now)

        assert result == "just now"

    def test_format_time_ago_minutes(self):
        """Test formatting time in minutes."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(minutes=5)

        result = format_time_ago(past)

        assert result == "5m ago"

    def test_format_time_ago_one_minute(self):
        """Test formatting one minute ago."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(minutes=1)

        result = format_time_ago(past)

        assert result == "1m ago"

    def test_format_time_ago_hours(self):
        """Test formatting time in hours."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=3)

        result = format_time_ago(past)

        assert result == "3h ago"

    def test_format_time_ago_days(self):
        """Test formatting time in days."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=5)

        result = format_time_ago(past)

        assert result == "5d ago"

    def test_format_time_ago_naive_datetime(self):
        """Test formatting naive datetime (without timezone)."""
        now = datetime.now(timezone.utc)
        naive = now.replace(tzinfo=None) - timedelta(hours=2)

        result = format_time_ago(naive)

        # Should handle it by adding UTC timezone
        assert "ago" in result


class TestPathExpansion:
    """Tests for path expansion."""

    @patch("os.path.expanduser")
    @patch("os.path.expandvars")
    def test_expand_path_with_tilde(self, mock_expandvars, mock_expanduser):
        """Test expanding path with tilde."""
        mock_expanduser.return_value = "/home/user/code"
        mock_expandvars.return_value = "/home/user/code"

        with patch.object(Path, "resolve", return_value=Path("/home/user/code")):
            result = expand_path("~/code")

        mock_expanduser.assert_called_once()
        assert isinstance(result, Path)

    @patch("os.path.expanduser")
    @patch("os.path.expandvars")
    def test_expand_path_with_env_var(self, mock_expandvars, mock_expanduser):
        """Test expanding path with environment variable."""
        mock_expanduser.return_value = "$HOME/projects"
        mock_expandvars.return_value = "/home/user/projects"

        with patch.object(Path, "resolve", return_value=Path("/home/user/projects")):
            result = expand_path("$HOME/projects")

        mock_expandvars.assert_called_once()
        assert isinstance(result, Path)


class TestTmuxSessionName:
    """Tests for tmux session name generation."""

    def test_get_tmux_session_name_default_prefix(self):
        """Test getting tmux session name with default prefix."""
        name = get_tmux_session_name("TEST-001")

        assert name == "ccc-TEST-001"

    def test_get_tmux_session_name_custom_prefix(self):
        """Test getting tmux session name with custom prefix."""
        name = get_tmux_session_name("TEST-001", prefix="dev-")

        assert name == "dev-TEST-001"

    def test_get_tmux_session_name_no_prefix(self):
        """Test getting tmux session name with no prefix."""
        name = get_tmux_session_name("TEST-001", prefix="")

        assert name == "TEST-001"


class TestBranchName:
    """Tests for branch name generation."""

    def test_get_branch_name_without_title(self):
        """Test getting branch name without title."""
        name = get_branch_name("IN-413")

        assert name == "feature/IN-413"

    def test_get_branch_name_with_title(self):
        """Test getting branch name with title."""
        name = get_branch_name("IN-413", "Public API bulk uploads")

        assert name == "feature/IN-413/public-api-bulk-uploads"

    def test_get_branch_name_with_special_chars(self):
        """Test getting branch name with special characters in title."""
        name = get_branch_name("BUG-42", "Fix: Login & Authentication Error!")

        assert name == "feature/BUG-42/fix-login-authentication-error"

    def test_get_branch_name_with_multiple_spaces(self):
        """Test getting branch name with multiple consecutive spaces."""
        name = get_branch_name("TASK-100", "Test    multiple     spaces")

        assert name == "feature/TASK-100/test-multiple-spaces"

    def test_get_branch_name_with_hyphens(self):
        """Test getting branch name with hyphens in title."""
        name = get_branch_name("FEAT-5", "Add-new-feature")

        assert name == "feature/FEAT-5/add-new-feature"

    def test_get_branch_name_empty_title(self):
        """Test getting branch name with empty title."""
        name = get_branch_name("IN-413", "")

        assert name == "feature/IN-413"

    def test_get_branch_name_title_only_special_chars(self):
        """Test getting branch name with title containing only special chars."""
        name = get_branch_name("IN-413", "!@#$%^&*()")

        assert name == "feature/IN-413"


class TestStringManipulation:
    """Tests for string manipulation functions."""

    def test_truncate_string_short(self):
        """Test truncating string that's shorter than max length."""
        text = "Short text"
        result = truncate_string(text, 20)

        assert result == "Short text"

    def test_truncate_string_exact(self):
        """Test truncating string that's exactly max length."""
        text = "Exact length"
        result = truncate_string(text, 12)

        assert result == "Exact length"

    def test_truncate_string_long(self):
        """Test truncating string that's longer than max length."""
        text = "This is a very long string that needs truncation"
        result = truncate_string(text, 20)

        assert result == "This is a very lo..."
        assert len(result) == 20

    def test_truncate_string_custom_suffix(self):
        """Test truncating string with custom suffix."""
        text = "This is a long string"
        result = truncate_string(text, 15, suffix=">>")

        assert result == "This is a lon>>"
        assert len(result) == 15

    def test_truncate_string_very_short_max(self):
        """Test truncating string with very short max length."""
        text = "Hello World"
        result = truncate_string(text, 5)

        assert result == "He..."
        assert len(result) == 5
