"""
Unit tests for StatusBar widget.
"""

import pytest
from datetime import datetime, timezone
from rich.text import Text

from ccc.tui.widgets import StatusBar


class TestStatusBar:
    """Tests for StatusBar widget."""

    def test_status_bar_creation(self):
        """Test creating a StatusBar widget."""
        status_bar = StatusBar()

        assert status_bar is not None
        assert status_bar.border_title == "Status"
        # Note: Can't access reactive property without app context

    def test_get_status_icon(self):
        """Test status icon selection."""
        status_bar = StatusBar()

        assert status_bar._get_status_icon("healthy") == "●"
        assert status_bar._get_status_icon("connected") == "●"
        assert status_bar._get_status_icon("starting") == "◐"
        assert status_bar._get_status_icon("unhealthy") == "◐"
        assert status_bar._get_status_icon("error") == "✗"
        assert status_bar._get_status_icon("stopped") == "○"
        assert status_bar._get_status_icon("unknown") == "?"
        assert status_bar._get_status_icon("invalid") == "?"

    def test_get_status_style(self):
        """Test status style selection."""
        status_bar = StatusBar()

        assert status_bar._get_status_style("healthy") == "green"
        assert status_bar._get_status_style("connected") == "green"
        assert status_bar._get_status_style("starting") == "yellow"
        assert status_bar._get_status_style("unhealthy") == "yellow"
        assert status_bar._get_status_style("error") == "red"
        assert status_bar._get_status_style("stopped") == "dim"
        assert status_bar._get_status_style("unknown") == "dim"

    def test_render_server_status_healthy(self):
        """Test rendering healthy server status."""
        status_bar = StatusBar()
        text = Text()

        server = {
            "state": "healthy",
            "url": "http://localhost:3000",
            "port": 3000,
        }

        status_bar._render_server_status(text, server)

        rendered = text.plain
        assert "SERVER:" in rendered
        assert "●" in rendered
        assert "http://localhost:3000" in rendered

    def test_render_server_status_error(self):
        """Test rendering server error status."""
        status_bar = StatusBar()
        text = Text()

        server = {
            "state": "error",
            "error_message": "EADDRINUSE: Port already in use",
        }

        status_bar._render_server_status(text, server)

        rendered = text.plain
        assert "SERVER:" in rendered
        assert "✗" in rendered
        assert "EADDRINUSE" in rendered

    def test_render_server_status_stopped(self):
        """Test rendering stopped server status."""
        status_bar = StatusBar()
        text = Text()

        server = {
            "state": "stopped",
        }

        status_bar._render_server_status(text, server)

        rendered = text.plain
        assert "SERVER:" in rendered
        assert "○" in rendered

    def test_render_database_status_connected(self):
        """Test rendering connected database status."""
        status_bar = StatusBar()
        text = Text()

        database = {
            "state": "connected",
            "connection_string": "postgresql://localhost:5432/testdb",
        }

        status_bar._render_database_status(text, database)

        rendered = text.plain
        assert "DATABASE:" in rendered
        assert "●" in rendered
        assert ":5432" in rendered

    def test_render_database_status_error(self):
        """Test rendering database error status."""
        status_bar = StatusBar()
        text = Text()

        database = {
            "state": "error",
            "error_message": "Connection refused",
        }

        status_bar._render_database_status(text, database)

        rendered = text.plain
        assert "DATABASE:" in rendered
        assert "✗" in rendered
        assert "Connection refused" in rendered

    def test_render_tests_status_all_passing(self):
        """Test rendering all tests passing."""
        status_bar = StatusBar()
        text = Text()

        tests = {
            "last_run": "2025-11-14T12:00:00Z",
            "passed": 187,
            "total": 187,
            "status": "passing",
        }

        status_bar._render_tests_status(text, tests)

        rendered = text.plain
        assert "TESTS:" in rendered
        assert "✓" in rendered
        assert "187/187 passed" in rendered

    def test_render_tests_status_some_failing(self):
        """Test rendering some tests failing."""
        status_bar = StatusBar()
        text = Text()

        tests = {
            "last_run": "2025-11-14T12:00:00Z",
            "passed": 156,
            "total": 187,
            "status": "failing",
        }

        status_bar._render_tests_status(text, tests)

        rendered = text.plain
        assert "TESTS:" in rendered
        assert "✗" in rendered
        assert "156/187 passed" in rendered

    def test_render_tests_status_not_run(self):
        """Test rendering tests not run."""
        status_bar = StatusBar()
        text = Text()

        tests = {}

        status_bar._render_tests_status(text, tests)

        rendered = text.plain
        assert "TESTS:" in rendered
        assert "?" in rendered
        assert "not run" in rendered

    def test_render_build_status_success(self):
        """Test rendering successful build."""
        status_bar = StatusBar()
        text = Text()

        build = {
            "last_build": datetime(2025, 11, 14, 12, 0, 0, tzinfo=timezone.utc),
            "success": True,
            "duration_seconds": 45.2,
        }

        status_bar._render_build_status(text, build)

        rendered = text.plain
        assert "BUILD:" in rendered
        assert "●" in rendered

    def test_render_build_status_failure(self):
        """Test rendering failed build."""
        status_bar = StatusBar()
        text = Text()

        build = {
            "last_build": datetime(2025, 11, 14, 12, 0, 0, tzinfo=timezone.utc),
            "success": False,
            "duration_seconds": 12.5,
        }

        status_bar._render_build_status(text, build)

        rendered = text.plain
        assert "BUILD:" in rendered
        assert "✗" in rendered

    def test_render_build_status_not_run(self):
        """Test rendering build not run."""
        status_bar = StatusBar()
        text = Text()

        build = {}

        status_bar._render_build_status(text, build)

        rendered = text.plain
        assert "BUILD:" in rendered
        assert "?" in rendered
        assert "not run" in rendered

    def test_render_complete_status(self):
        """Test rendering complete status with all sections."""
        status_bar = StatusBar()

        status = {
            "server": {
                "state": "healthy",
                "url": "http://localhost:3000",
                "port": 3000,
            },
            "database": {
                "state": "connected",
                "connection_string": "postgresql://localhost:5432/testdb",
            },
            "tests": {
                "last_run": "2025-11-14T12:00:00Z",
                "passed": 187,
                "total": 187,
                "status": "passing",
            },
            "build": {
                "last_build": datetime(2025, 11, 14, 12, 0, 0, tzinfo=timezone.utc),
                "success": True,
                "duration_seconds": 45.2,
            },
        }

        text = status_bar._render_status(status)
        rendered = text.plain

        # Check all sections are present
        assert "SERVER:" in rendered
        assert "DATABASE:" in rendered
        assert "TESTS:" in rendered
        assert "BUILD:" in rendered

        # Check status indicators
        assert "http://localhost:3000" in rendered
        assert ":5432" in rendered
        assert "187/187 passed" in rendered

    def test_render_empty_status(self):
        """Test rendering with empty status."""
        status_bar = StatusBar()

        text = status_bar._render_status({})
        rendered = text.plain

        # Should render empty or minimal content
        assert rendered is not None

    def test_render_status_with_server_only(self):
        """Test rendering status with only server data."""
        status_bar = StatusBar()

        status = {
            "server": {
                "state": "healthy",
                "url": "http://localhost:3000",
            },
        }

        # Test that render method works directly
        text = status_bar._render_status(status)
        rendered = text.plain

        assert "SERVER:" in rendered
        assert "http://localhost:3000" in rendered
