"""Tests for external_tools module."""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
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
        """Test launching Git UI in tmux creates new window when no existing window."""
        mock_which.return_value = '/usr/bin/lazygit'

        # Mock no existing git window
        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.returncode = 0
            result.stdout = 'main\nother'  # No 'git' window
            result.stderr = ''
            return result

        mock_run.side_effect = run_side_effect

        result = launcher.launch_git_ui()

        assert result is True
        # Check that tmux new-window was called
        new_window_calls = [call for call in mock_run.call_args_list if 'new-window' in str(call)]
        assert len(new_window_calls) > 0

    @patch('sys.platform', 'darwin')
    @patch('ccc.external_tools.shutil.which')
    @patch('ccc.external_tools.subprocess.run')
    @patch('ccc.external_tools.subprocess.Popen')
    @patch.dict('os.environ', {}, clear=True)
    def test_launch_git_ui_outside_tmux(self, mock_popen, mock_run, mock_which, launcher):
        """Test launching Git UI outside tmux opens in regular terminal."""
        mock_which.return_value = '/usr/bin/lazygit'

        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.returncode = 1  # pgrep returns 1 when process not found
            result.stdout = ''
            result.stderr = ''
            if 'osascript' in cmd or 'System Events' in str(args):
                result.returncode = 0
                result.stdout = 'iTerm2, Finder'
            return result

        mock_run.side_effect = run_side_effect

        result = launcher.launch_git_ui()

        assert result is True
        mock_popen.assert_called_once()

    @patch('ccc.external_tools.shutil.which')
    def test_launch_git_ui_not_installed(self, mock_which, launcher):
        """Test launching Git UI when not installed returns False."""
        mock_which.return_value = None

        result = launcher.launch_git_ui()

        assert result is False

    @patch('ccc.external_tools.shutil.which')
    @patch('ccc.external_tools.subprocess.run')
    @patch.dict('os.environ', {'TMUX': 'tmux-session'})
    def test_launch_git_ui_reuses_existing_tmux_window(self, mock_run, mock_which, launcher):
        """Test that existing tmux window with lazygit is reused instead of creating new."""
        mock_which.return_value = '/usr/bin/lazygit'

        # Mock responses for checking existing windows
        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.returncode = 0
            result.stdout = ''
            result.stderr = ''

            if 'list-windows' in cmd:
                # Window named "git" exists
                result.stdout = 'main\ngit\nother'
            elif 'list-panes' in cmd:
                # lazygit is running in the window
                result.stdout = 'lazygit'
            elif 'select-window' in cmd:
                # Successfully selected window
                pass
            return result

        mock_run.side_effect = run_side_effect

        result = launcher.launch_git_ui()

        assert result is True
        # Verify select-window was called
        select_calls = [call for call in mock_run.call_args_list if 'select-window' in str(call)]
        assert len(select_calls) > 0

    @patch('ccc.external_tools.shutil.which')
    @patch('ccc.external_tools.subprocess.run')
    @patch.dict('os.environ', {'TMUX': 'tmux-session'})
    def test_launch_git_ui_recreates_stale_tmux_window(self, mock_run, mock_which, launcher):
        """Test that tmux window exists but lazygit not running causes recreation."""
        mock_which.return_value = '/usr/bin/lazygit'

        call_count = {'count': 0}

        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.returncode = 0
            result.stdout = ''
            result.stderr = ''

            if 'list-windows' in cmd:
                result.stdout = 'main\ngit\nother'
            elif 'list-panes' in cmd:
                # lazygit NOT running (different command)
                result.stdout = 'bash'
            elif 'kill-window' in cmd:
                call_count['count'] += 1
                pass
            elif 'new-window' in cmd:
                call_count['count'] += 1
                pass
            return result

        mock_run.side_effect = run_side_effect

        result = launcher.launch_git_ui()

        assert result is True
        # Verify both kill-window and new-window were called
        assert call_count['count'] >= 2

    @patch('sys.platform', 'darwin')
    @patch('ccc.external_tools.shutil.which')
    @patch('ccc.external_tools.subprocess.run')
    @patch('ccc.external_tools.subprocess.Popen')
    @patch.dict('os.environ', {}, clear=True)
    def test_launch_git_ui_macos_reuses_existing_process(self, mock_popen, mock_run, mock_which, launcher):
        """Test that macOS reuses existing lazygit process instead of creating new window."""
        mock_which.return_value = '/usr/bin/lazygit'

        def run_side_effect(*args, **kwargs):
            cmd = args[0]
            result = Mock()
            result.stderr = ''

            if 'pgrep' in cmd:
                # lazygit is running
                result.returncode = 0
                result.stdout = '12345'
            else:
                # System Events call
                result.returncode = 0
                result.stdout = 'iTerm2, Finder'
            return result

        mock_run.side_effect = run_side_effect

        result = launcher.launch_git_ui()

        assert result is True
        # Popen should NOT be called (no new window created)
        mock_popen.assert_not_called()
        # osascript activate should be called
        activate_calls = [call for call in mock_run.call_args_list if 'activate' in str(call)]
        assert len(activate_calls) > 0


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
