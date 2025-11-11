"""
Unit tests for build_status module.
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from ccc.build_status import (
    BuildStatus,
    get_build_status_path,
    read_build_status,
    write_build_status,
    init_build_status,
    update_build_status,
    format_build_status,
)


class TestBuildStatus:
    """Tests for BuildStatus dataclass."""

    def test_build_status_creation(self):
        """Test creating a BuildStatus instance."""
        status = BuildStatus(
            ticket_id="TEST-001",
            status="passing",
            duration_seconds=45,
            errors=[],
            warnings=2,
        )

        assert status.ticket_id == "TEST-001"
        assert status.status == "passing"
        assert status.duration_seconds == 45
        assert status.errors == []
        assert status.warnings == 2
        assert status.last_build is None

    def test_build_status_with_timestamp(self):
        """Test BuildStatus with timestamp."""
        now = datetime.now(timezone.utc)
        status = BuildStatus(
            ticket_id="TEST-002",
            status="failing",
            last_build=now,
            errors=["Error 1", "Error 2"],
        )

        assert status.last_build == now
        assert len(status.errors) == 2

    def test_build_status_to_dict(self):
        """Test converting BuildStatus to dictionary."""
        now = datetime.now(timezone.utc)
        status = BuildStatus(
            ticket_id="TEST-003",
            status="passing",
            last_build=now,
            duration_seconds=30,
            errors=[],
            warnings=1,
        )

        data = status.to_dict()

        assert data["ticket_id"] == "TEST-003"
        assert data["status"] == "passing"
        assert data["last_build"] == now.isoformat()
        assert data["duration_seconds"] == 30
        assert data["errors"] == []
        assert data["warnings"] == 1

    def test_build_status_from_dict(self):
        """Test creating BuildStatus from dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "ticket_id": "TEST-004",
            "status": "failing",
            "last_build": now.isoformat(),
            "duration_seconds": 60,
            "errors": ["Error 1"],
            "warnings": 3,
        }

        status = BuildStatus.from_dict(data)

        assert status.ticket_id == "TEST-004"
        assert status.status == "failing"
        assert status.last_build == now
        assert status.duration_seconds == 60
        assert status.errors == ["Error 1"]
        assert status.warnings == 3

    def test_build_status_from_dict_missing_fields(self):
        """Test creating BuildStatus from dictionary with missing fields."""
        data = {
            "ticket_id": "TEST-005",
            "status": "unknown",
        }

        status = BuildStatus.from_dict(data)

        assert status.ticket_id == "TEST-005"
        assert status.status == "unknown"
        assert status.errors == []
        assert status.warnings == 0
        assert status.last_build is None


class TestBuildStatusPaths:
    """Tests for build status file path functions."""

    @patch("ccc.build_status.get_ticket_dir")
    def test_get_build_status_path(self, mock_get_ticket_dir):
        """Test getting build status file path."""
        mock_get_ticket_dir.return_value = Path("/home/user/.cccc-control/TEST-001")

        path = get_build_status_path("TEST-001")

        assert path == Path("/home/user/.cccc-control/TEST-001/build-status.json")
        mock_get_ticket_dir.assert_called_once_with("TEST-001")


class TestReadWriteBuildStatus:
    """Tests for reading and writing build status files."""

    @patch("ccc.build_status.get_build_status_path")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_build_status_success(self, mock_file, mock_get_path):
        """Test successfully reading build status."""
        mock_get_path.return_value = Path("/tmp/build-status.json")
        now = datetime.now(timezone.utc)
        data = {
            "ticket_id": "TEST-001",
            "status": "passing",
            "last_build": now.isoformat(),
            "duration_seconds": 45,
            "errors": [],
            "warnings": 2,
        }
        mock_file.return_value.read.return_value = json.dumps(data)

        with patch.object(Path, "exists", return_value=True):
            with patch("json.load", return_value=data):
                status = read_build_status("TEST-001")

        assert status is not None
        assert status.ticket_id == "TEST-001"
        assert status.status == "passing"
        assert status.duration_seconds == 45

    @patch("ccc.build_status.get_build_status_path")
    def test_read_build_status_file_not_exists(self, mock_get_path):
        """Test reading build status when file doesn't exist."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_get_path.return_value = mock_path

        status = read_build_status("TEST-001")

        assert status is None

    @patch("ccc.build_status.get_build_status_path")
    def test_read_build_status_error(self, mock_get_path):
        """Test reading build status with JSON error."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        with patch("builtins.open", side_effect=Exception("JSON error")):
            status = read_build_status("TEST-001")

        assert status is None

    @patch("ccc.build_status.get_build_status_path")
    @patch("builtins.open", new_callable=mock_open)
    def test_write_build_status_success(self, mock_file, mock_get_path):
        """Test successfully writing build status."""
        mock_path = MagicMock()
        mock_path.parent.mkdir = MagicMock()
        mock_get_path.return_value = mock_path

        status = BuildStatus(
            ticket_id="TEST-001",
            status="passing",
            duration_seconds=30,
        )

        with patch("json.dump") as mock_json_dump:
            result = write_build_status(status)

        assert result is True
        assert status.last_build is not None  # Should be set automatically
        mock_json_dump.assert_called_once()

    @patch("ccc.build_status.get_build_status_path")
    def test_write_build_status_error(self, mock_get_path):
        """Test writing build status with error."""
        mock_get_path.side_effect = Exception("Write error")

        status = BuildStatus(ticket_id="TEST-001", status="passing")
        result = write_build_status(status)

        assert result is False


class TestInitAndUpdateBuildStatus:
    """Tests for initializing and updating build status."""

    @patch("ccc.build_status.write_build_status")
    def test_init_build_status(self, mock_write):
        """Test initializing build status."""
        mock_write.return_value = True

        init_build_status("TEST-001")

        mock_write.assert_called_once()
        call_args = mock_write.call_args[0][0]
        assert call_args.ticket_id == "TEST-001"
        assert call_args.status == "unknown"

    @patch("ccc.build_status.read_build_status")
    @patch("ccc.build_status.write_build_status")
    def test_update_build_status_new(self, mock_write, mock_read):
        """Test updating build status for new ticket."""
        mock_read.return_value = None
        mock_write.return_value = True

        result = update_build_status(
            "TEST-001",
            "passing",
            duration=45,
            warnings=2,
        )

        assert result is True
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0][0]
        assert call_args.ticket_id == "TEST-001"
        assert call_args.status == "passing"
        assert call_args.duration_seconds == 45
        assert call_args.warnings == 2

    @patch("ccc.build_status.read_build_status")
    @patch("ccc.build_status.write_build_status")
    def test_update_build_status_existing(self, mock_write, mock_read):
        """Test updating existing build status."""
        existing_status = BuildStatus(
            ticket_id="TEST-001",
            status="passing",
            duration_seconds=30,
        )
        mock_read.return_value = existing_status
        mock_write.return_value = True

        result = update_build_status(
            "TEST-001",
            "failing",
            errors=["Error 1", "Error 2"],
        )

        assert result is True
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0][0]
        assert call_args.status == "failing"
        assert len(call_args.errors) == 2


class TestFormatBuildStatus:
    """Tests for formatting build status."""

    def test_format_build_status_passing(self):
        """Test formatting passing build status."""
        now = datetime.now(timezone.utc)
        status = BuildStatus(
            ticket_id="TEST-001",
            status="passing",
            last_build=now,
            duration_seconds=45,
            warnings=2,
            errors=[],
        )

        formatted = format_build_status(status)

        assert "✓ Passing" in formatted
        assert "45s" in formatted
        assert "2 warnings" in formatted

    def test_format_build_status_failing(self):
        """Test formatting failing build status."""
        now = datetime.now(timezone.utc)
        status = BuildStatus(
            ticket_id="TEST-001",
            status="failing",
            last_build=now,
            duration_seconds=23,
            errors=["Error 1", "Error 2"],
            warnings=0,
        )

        formatted = format_build_status(status)

        assert "✗ Failing" in formatted
        assert "23s" in formatted
        assert "2 errors" in formatted
        assert "Error 1" in formatted
        assert "Error 2" in formatted

    def test_format_build_status_unknown(self):
        """Test formatting unknown build status."""
        status = BuildStatus(
            ticket_id="TEST-001",
            status="unknown",
        )

        formatted = format_build_status(status)

        assert "? Unknown" in formatted

    def test_format_build_status_many_errors(self):
        """Test formatting build status with many errors."""
        now = datetime.now(timezone.utc)
        errors = [f"Error {i}" for i in range(10)]
        status = BuildStatus(
            ticket_id="TEST-001",
            status="failing",
            last_build=now,
            errors=errors,
        )

        formatted = format_build_status(status)

        # Should show first 5 errors
        assert "Error 0" in formatted
        assert "Error 4" in formatted
        # Should indicate more errors
        assert "and 5 more" in formatted
