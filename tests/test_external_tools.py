"""Tests for external_tools module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from ccc.external_tools import ExternalToolLauncher
from ccc.config import Config


@pytest.fixture
def mock_config():
    """Create a mock config for testing."""
    config = Config()
    config.ide_command = "cursor"
    config.ide_args = []
    config.git_ui_command = "lazygit"
    config.git_ui_args = []
    config.db_client_command = "open"
    config.db_client_args = ["-a", "TablePlus"]
    config.jira_base_url = "https://company.atlassian.net"
    config.api_docs_url = "https://docs.example.com/api"
    config.plan_file = "PLAN.md"
    config.notes_file = "NOTES.md"
    config.tasks_file = "TASKS.md"
    return config


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager."""
    return Mock()


@pytest.fixture
def launcher(mock_config, mock_session_manager):
    """Create a launcher instance for testing."""
    return ExternalToolLauncher(mock_config, mock_session_manager)


class TestLaunchIDE:
    """Tests for launch_ide method."""

    @patch('ccc.external_tools.shutil.which')
    @patch('ccc.external_tools.subprocess.Popen')
    def test_launch_ide_with_cursor(self, mock_popen, mock_which, launcher):
        """Test launching IDE with Cursor available."""
        mock_which.return_value = '/usr/local/bin/cursor'

        result = launcher.launch_ide('test.py')

        assert result is True
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == 'cursor'
        # The path gets converted to absolute, so just check that it ends with test.py
        assert call_args[-1].endswith('test.py')

    @patch('ccc.external_tools.shutil.which')
    @patch('ccc.external_tools.subprocess.Popen')
    @patch.dict('os.environ', {'EDITOR': 'vim'})
    def test_launch_ide_fallback_to_editor(self, mock_popen, mock_which, launcher):
        """Test launching IDE falls back to $EDITOR when Cursor not available."""
        # Cursor not available
        mock_which.side_effect = lambda cmd: '/usr/bin/vim' if cmd == 'vim' else None

        result = launcher.launch_ide('test.py')

        assert result is True
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == 'vim'

    @patch('ccc.external_tools.shutil.which')
    @patch('ccc.external_tools.subprocess.Popen')
    def test_launch_ide_absolute_path(self, mock_popen, mock_which, launcher):
        """Test that file path is converted to absolute path."""
        mock_which.return_value = '/usr/local/bin/cursor'

        launcher.launch_ide('relative/path.py')

        call_args = mock_popen.call_args[0][0]
        # Should be absolute path
        assert Path(call_args[-1]).is_absolute()


class TestLaunchGitUI:
    """Tests for launch_git_ui method."""

    @patch('ccc.external_tools.shutil.which')
    @patch('ccc.external_tools.subprocess.run')
    @patch.dict('os.environ', {'TMUX': 'tmux-session'})
    def test_launch_git_ui_in_tmux(self, mock_run, mock_which, launcher):
        """Test launching Git UI in tmux creates new window."""
        mock_which.return_value = '/usr/bin/lazygit'

        result = launcher.launch_git_ui()

        assert result is True
        mock_run.assert_called_once()
        # Check that tmux new-window was called
        call_args = mock_run.call_args[0][0]
        assert 'tmux' in call_args
        assert 'new-window' in call_args

    @patch('ccc.external_tools.shutil.which')
    @patch('ccc.external_tools.subprocess.Popen')
    @patch.dict('os.environ', {}, clear=True)
    def test_launch_git_ui_outside_tmux(self, mock_popen, mock_which, launcher):
        """Test launching Git UI outside tmux opens in regular terminal."""
        mock_which.return_value = '/usr/bin/lazygit'

        result = launcher.launch_git_ui()

        assert result is True
        mock_popen.assert_called_once()

    @patch('ccc.external_tools.shutil.which')
    def test_launch_git_ui_not_installed(self, mock_which, launcher):
        """Test launching Git UI when not installed returns False."""
        mock_which.return_value = None

        result = launcher.launch_git_ui()

        assert result is False


class TestOpenURL:
    """Tests for open_url method."""

    @patch('sys.platform', 'darwin')
    @patch('ccc.external_tools.subprocess.Popen')
    def test_open_url_macos(self, mock_popen, launcher):
        """Test opening URL on macOS uses 'open' command."""
        launcher.open_url('https://example.com')

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == 'open'
        assert call_args[1] == 'https://example.com'

    @patch('sys.platform', 'linux')
    @patch('ccc.external_tools.subprocess.Popen')
    def test_open_url_linux(self, mock_popen, launcher):
        """Test opening URL on Linux uses 'xdg-open' command."""
        launcher.open_url('https://example.com')

        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == 'xdg-open'
        assert call_args[1] == 'https://example.com'


class TestOpenJiraTicket:
    """Tests for open_jira_ticket method."""

    @patch('ccc.external_tools.ExternalToolLauncher.open_url')
    def test_open_jira_ticket(self, mock_open_url, launcher):
        """Test opening Jira ticket constructs correct URL."""
        mock_open_url.return_value = True

        result = launcher.open_jira_ticket('PROJ-123')

        assert result is True
        mock_open_url.assert_called_once_with('https://company.atlassian.net/browse/PROJ-123')

    def test_open_jira_ticket_no_base_url(self, mock_session_manager):
        """Test opening Jira ticket without base URL configured."""
        config = Config()
        config.jira_base_url = ""
        launcher = ExternalToolLauncher(config, mock_session_manager)

        result = launcher.open_jira_ticket('PROJ-123')

        assert result is False


class TestOpenAPIDocs:
    """Tests for open_api_docs method."""

    @patch('ccc.external_tools.ExternalToolLauncher.open_url')
    def test_open_api_docs(self, mock_open_url, launcher):
        """Test opening API docs."""
        mock_open_url.return_value = True

        result = launcher.open_api_docs()

        assert result is True
        mock_open_url.assert_called_once_with('https://docs.example.com/api')

    def test_open_api_docs_no_url(self, mock_session_manager):
        """Test opening API docs without URL configured."""
        config = Config()
        config.api_docs_url = ""
        launcher = ExternalToolLauncher(config, mock_session_manager)

        result = launcher.open_api_docs()

        assert result is False


class TestLaunchDatabaseClient:
    """Tests for launch_database_client method."""

    @patch('ccc.external_tools.subprocess.Popen')
    def test_launch_database_client(self, mock_popen, launcher):
        """Test launching database client."""
        result = launcher.launch_database_client()

        assert result is True
        mock_popen.assert_called_once()
        call_args = mock_popen.call_args[0][0]
        assert call_args[0] == 'open'
        assert '-a' in call_args
        assert 'TablePlus' in call_args

    @patch('ccc.external_tools.subprocess.Popen')
    def test_launch_database_client_with_connection_string(self, mock_popen, launcher):
        """Test launching database client with connection string."""
        result = launcher.launch_database_client('postgresql://localhost:5432/mydb')

        assert result is True
        call_args = mock_popen.call_args[0][0]
        assert 'postgresql://localhost:5432/mydb' in call_args


class TestOpenFiles:
    """Tests for open_plan_file, open_notes_file, open_tasks_file methods."""

    @patch('ccc.external_tools.ExternalToolLauncher.launch_ide')
    def test_open_plan_file(self, mock_launch_ide, launcher):
        """Test opening PLAN.md."""
        mock_launch_ide.return_value = True

        result = launcher.open_plan_file()

        assert result is True
        mock_launch_ide.assert_called_once_with('PLAN.md')

    @patch('ccc.external_tools.ExternalToolLauncher.launch_ide')
    def test_open_notes_file(self, mock_launch_ide, launcher):
        """Test opening NOTES.md."""
        mock_launch_ide.return_value = True

        result = launcher.open_notes_file()

        assert result is True
        mock_launch_ide.assert_called_once_with('NOTES.md')

    @patch('ccc.external_tools.ExternalToolLauncher.launch_ide')
    def test_open_tasks_file(self, mock_launch_ide, launcher):
        """Test opening TASKS.md."""
        mock_launch_ide.return_value = True

        result = launcher.open_tasks_file()

        assert result is True
        mock_launch_ide.assert_called_once_with('TASKS.md')
