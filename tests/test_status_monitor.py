"""
Unit tests for status_monitor module.
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from ccc.status_monitor import (
    ServerStatus,
    DatabaseStatus,
    StatusBarState,
    LogPatternMatcher,
    StatusMonitor,
)


class TestServerStatus:
    """Tests for ServerStatus dataclass."""

    def test_server_status_creation(self):
        """Test creating a ServerStatus."""
        status = ServerStatus(
            state="healthy",
            url="http://localhost:3000",
            port=3000,
        )

        assert status.state == "healthy"
        assert status.url == "http://localhost:3000"
        assert status.port == 3000
        assert status.error_message is None

    def test_server_status_to_dict(self):
        """Test converting ServerStatus to dict."""
        status = ServerStatus(
            state="healthy",
            url="http://localhost:3000",
            port=3000,
            last_check=datetime(2025, 11, 14, 12, 0, 0, tzinfo=timezone.utc),
        )

        data = status.to_dict()

        assert data["state"] == "healthy"
        assert data["url"] == "http://localhost:3000"
        assert data["port"] == 3000
        assert data["last_check"] == "2025-11-14T12:00:00+00:00"

    def test_server_status_from_dict(self):
        """Test creating ServerStatus from dict."""
        data = {
            "state": "healthy",
            "url": "http://localhost:3000",
            "port": 3000,
            "error_message": None,
            "last_check": "2025-11-14T12:00:00+00:00",
            "uptime_seconds": 120.5,
        }

        status = ServerStatus.from_dict(data)

        assert status.state == "healthy"
        assert status.url == "http://localhost:3000"
        assert status.port == 3000
        assert isinstance(status.last_check, datetime)


class TestDatabaseStatus:
    """Tests for DatabaseStatus dataclass."""

    def test_database_status_creation(self):
        """Test creating a DatabaseStatus."""
        status = DatabaseStatus(
            state="connected",
            connection_string="postgresql://localhost:5432/mydb",
        )

        assert status.state == "connected"
        assert status.connection_string == "postgresql://localhost:5432/mydb"
        assert status.error_message is None

    def test_database_status_to_dict(self):
        """Test converting DatabaseStatus to dict."""
        status = DatabaseStatus(
            state="connected",
            connection_string="postgresql://localhost:5432/mydb",
            last_check=datetime(2025, 11, 14, 12, 0, 0, tzinfo=timezone.utc),
        )

        data = status.to_dict()

        assert data["state"] == "connected"
        assert data["connection_string"] == "postgresql://localhost:5432/mydb"
        assert data["last_check"] == "2025-11-14T12:00:00+00:00"

    def test_database_status_from_dict(self):
        """Test creating DatabaseStatus from dict."""
        data = {
            "state": "connected",
            "connection_string": "postgresql://localhost:5432/mydb",
            "error_message": None,
            "last_check": "2025-11-14T12:00:00+00:00",
        }

        status = DatabaseStatus.from_dict(data)

        assert status.state == "connected"
        assert isinstance(status.last_check, datetime)


class TestStatusBarState:
    """Tests for StatusBarState dataclass."""

    def test_status_bar_state_creation(self):
        """Test creating a StatusBarState."""
        server = ServerStatus(state="healthy")
        database = DatabaseStatus(state="connected")
        build = {"status": "passing"}
        tests = {"status": "passing"}

        state = StatusBarState(
            server=server,
            database=database,
            build=build,
            tests=tests,
        )

        assert state.server.state == "healthy"
        assert state.database.state == "connected"
        assert state.build["status"] == "passing"
        assert state.tests["status"] == "passing"

    def test_status_bar_state_to_dict(self):
        """Test converting StatusBarState to dict."""
        server = ServerStatus(state="healthy")
        database = DatabaseStatus(state="connected")

        state = StatusBarState(
            server=server,
            database=database,
            build={"status": "passing"},
            tests={"status": "passing"},
        )

        data = state.to_dict()

        assert data["server"]["state"] == "healthy"
        assert data["database"]["state"] == "connected"
        assert data["build"]["status"] == "passing"

    def test_status_bar_state_from_dict(self):
        """Test creating StatusBarState from dict."""
        data = {
            "server": {"state": "healthy", "url": None, "port": None, "error_message": None, "last_check": None, "uptime_seconds": None},
            "database": {"state": "connected", "connection_string": None, "error_message": None, "last_check": None},
            "build": {"status": "passing"},
            "tests": {"status": "passing"},
        }

        state = StatusBarState.from_dict(data)

        assert state.server.state == "healthy"
        assert state.database.state == "connected"


class TestLogPatternMatcher:
    """Tests for LogPatternMatcher class."""

    def test_extract_server_url_npm(self):
        """Test extracting URL from npm dev server output."""
        matcher = LogPatternMatcher()

        url = matcher.extract_server_url("Server listening on :3000")
        assert url == "http://localhost:3000"

        url = matcher.extract_server_url("Ready on http://localhost:3000")
        assert url == "http://localhost:3000"

    def test_extract_server_url_python(self):
        """Test extracting URL from Python server output."""
        matcher = LogPatternMatcher()

        url = matcher.extract_server_url("Serving on http://0.0.0.0:8000")
        assert url == "http://localhost:8000"

    def test_extract_server_url_no_match(self):
        """Test log line with no server URL."""
        matcher = LogPatternMatcher()

        url = matcher.extract_server_url("Building project...")
        assert url is None

    def test_is_error_detects_errors(self):
        """Test error detection in log lines."""
        matcher = LogPatternMatcher()

        assert matcher.is_error("ERROR: Failed to start")
        assert matcher.is_error("Error: EADDRINUSE")
        assert matcher.is_error("Fatal: Cannot bind to port")
        assert matcher.is_error("uncaughtException: Error")

    def test_is_error_ignores_normal_lines(self):
        """Test that normal log lines don't trigger error."""
        matcher = LogPatternMatcher()

        assert not matcher.is_error("Server started successfully")
        assert not matcher.is_error("Listening on port 3000")

    def test_custom_patterns(self):
        """Test LogPatternMatcher with custom patterns."""
        matcher = LogPatternMatcher(
            ready_patterns=[r"Custom server ready on :(\d+)"],
            error_patterns=[r"CUSTOM_ERROR"],
        )

        url = matcher.extract_server_url("Custom server ready on :4000")
        assert url == "http://localhost:4000"

        assert matcher.is_error("CUSTOM_ERROR: Something went wrong")


class TestStatusMonitor:
    """Tests for StatusMonitor class."""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        return {
            "server_command": "npm run dev",
            "server_health_check_interval": 10,
            "server_health_check_timeout": 2,
            "database_health_check_interval": 30,
            "database_connection_string": "postgresql://localhost:5432/testdb",
        }

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create temporary directory for state files."""
        return tmp_path

    @patch("ccc.status_monitor.get_branch_dir")
    def test_status_monitor_init(self, mock_get_branch_dir, mock_config, temp_dir):
        """Test StatusMonitor initialization."""
        mock_get_branch_dir.return_value = temp_dir

        monitor = StatusMonitor("test-branch", mock_config)

        assert monitor.branch_name == "test-branch"
        assert monitor.config == mock_config
        assert monitor.state_file == temp_dir / "status-bar.json"

    @patch("ccc.status_monitor.get_branch_dir")
    def test_load_status_creates_default(self, mock_get_branch_dir, mock_config, temp_dir):
        """Test loading status creates default when file doesn't exist."""
        mock_get_branch_dir.return_value = temp_dir

        monitor = StatusMonitor("test-branch", mock_config)
        status = monitor.load_status()

        assert status.server.state == "stopped"
        assert status.database.state == "stopped"
        assert status.build == {}
        assert status.tests == {}

    @patch("ccc.status_monitor.get_branch_dir")
    def test_save_and_load_status(self, mock_get_branch_dir, mock_config, temp_dir):
        """Test saving and loading status."""
        mock_get_branch_dir.return_value = temp_dir

        monitor = StatusMonitor("test-branch", mock_config)

        # Create status
        status = StatusBarState(
            server=ServerStatus(state="healthy", url="http://localhost:3000", port=3000),
            database=DatabaseStatus(state="connected"),
            build={"status": "passing"},
            tests={"status": "passing"},
        )

        # Save
        monitor.save_status(status)

        # Load
        loaded_status = monitor.load_status()

        assert loaded_status.server.state == "healthy"
        assert loaded_status.server.url == "http://localhost:3000"
        assert loaded_status.server.port == 3000
        assert loaded_status.database.state == "connected"

    @patch("ccc.status_monitor.get_branch_dir")
    def test_update_server_status(self, mock_get_branch_dir, mock_config, temp_dir):
        """Test updating server status."""
        mock_get_branch_dir.return_value = temp_dir

        monitor = StatusMonitor("test-branch", mock_config)

        # Update status
        monitor._update_server_status(
            state="healthy",
            url="http://localhost:3000",
            port=3000,
        )

        # Load and verify
        status = monitor.load_status()
        assert status.server.state == "healthy"
        assert status.server.url == "http://localhost:3000"
        assert status.server.port == 3000
        assert status.server.last_check is not None

    @patch("ccc.status_monitor.get_branch_dir")
    def test_handle_server_output_detects_ready(self, mock_get_branch_dir, mock_config, temp_dir):
        """Test server output parsing detects ready state."""
        mock_get_branch_dir.return_value = temp_dir

        monitor = StatusMonitor("test-branch", mock_config)

        # Simulate server output
        monitor._handle_server_output("Server listening on :3000")

        # Verify status updated
        status = monitor.load_status()
        assert status.server.state == "healthy"
        assert status.server.url == "http://localhost:3000"
        assert status.server.port == 3000

    @patch("ccc.status_monitor.get_branch_dir")
    def test_handle_server_output_detects_error(self, mock_get_branch_dir, mock_config, temp_dir):
        """Test server output parsing detects errors."""
        mock_get_branch_dir.return_value = temp_dir

        monitor = StatusMonitor("test-branch", mock_config)

        # Simulate error output
        monitor._handle_server_output("ERROR: Failed to bind to port")

        # Verify status updated
        status = monitor.load_status()
        assert status.server.state == "error"
        assert "Failed to bind to port" in status.server.error_message

    @patch("ccc.status_monitor.get_branch_dir")
    def test_callback_on_status_change(self, mock_get_branch_dir, mock_config, temp_dir):
        """Test callback is called when status changes."""
        mock_get_branch_dir.return_value = temp_dir

        callback = Mock()
        monitor = StatusMonitor("test-branch", mock_config, on_status_change=callback)

        # Update status
        monitor._update_server_status(state="healthy")

        # Verify callback was called
        assert callback.called
        assert callback.call_args[0][0].server.state == "healthy"
