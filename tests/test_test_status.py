"""
Unit tests for test_status module.
"""

import json
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from ccc.test_status import (
    TestFailure,
    TestStatus,
    get_test_status_path,
    read_test_status,
    write_test_status,
    init_test_status,
    update_test_status,
    parse_test_output,
    format_test_status,
    _parse_jest_output,
    _parse_pytest_output,
    _parse_go_output,
)


class TestTestFailure:
    """Tests for TestFailure dataclass."""

    def test_test_failure_creation(self):
        """Test creating a TestFailure instance."""
        failure = TestFailure(
            name="test_example",
            message="AssertionError: expected True",
            file="test_example.py",
            line=42,
        )

        assert failure.name == "test_example"
        assert failure.message == "AssertionError: expected True"
        assert failure.file == "test_example.py"
        assert failure.line == 42

    def test_test_failure_minimal(self):
        """Test creating TestFailure with minimal info."""
        failure = TestFailure(
            name="test_minimal",
            message="Failed",
        )

        assert failure.name == "test_minimal"
        assert failure.message == "Failed"
        assert failure.file is None
        assert failure.line is None

    def test_test_failure_to_dict(self):
        """Test converting TestFailure to dictionary."""
        failure = TestFailure(
            name="test_to_dict",
            message="Error message",
            file="test.py",
            line=10,
        )

        data = failure.to_dict()

        assert data["name"] == "test_to_dict"
        assert data["message"] == "Error message"
        assert data["file"] == "test.py"
        assert data["line"] == 10

    def test_test_failure_from_dict(self):
        """Test creating TestFailure from dictionary."""
        data = {
            "name": "test_from_dict",
            "message": "Test error",
            "file": "tests/test.py",
            "line": 25,
        }

        failure = TestFailure.from_dict(data)

        assert failure.name == "test_from_dict"
        assert failure.message == "Test error"
        assert failure.file == "tests/test.py"
        assert failure.line == 25


class TestTestStatus:
    """Tests for TestStatus dataclass."""

    def test_test_status_creation(self):
        """Test creating a TestStatus instance."""
        status = TestStatus(
            ticket_id="TEST-001",
            status="passing",
            total=50,
            passed=50,
            failed=0,
            skipped=0,
        )

        assert status.ticket_id == "TEST-001"
        assert status.status == "passing"
        assert status.total == 50
        assert status.passed == 50
        assert status.failed == 0
        assert status.skipped == 0
        assert status.failures == []

    def test_test_status_with_failures(self):
        """Test TestStatus with failures."""
        failures = [
            TestFailure("test1", "Error 1"),
            TestFailure("test2", "Error 2"),
        ]
        status = TestStatus(
            ticket_id="TEST-002",
            status="failing",
            total=50,
            passed=48,
            failed=2,
            skipped=0,
            failures=failures,
        )

        assert status.failed == 2
        assert len(status.failures) == 2

    def test_test_status_to_dict(self):
        """Test converting TestStatus to dictionary."""
        now = datetime.now(timezone.utc)
        failures = [TestFailure("test1", "Error 1")]
        status = TestStatus(
            ticket_id="TEST-003",
            status="failing",
            last_run=now,
            duration_seconds=30,
            total=10,
            passed=9,
            failed=1,
            skipped=0,
            failures=failures,
        )

        data = status.to_dict()

        assert data["ticket_id"] == "TEST-003"
        assert data["status"] == "failing"
        assert data["last_run"] == now.isoformat()
        assert data["duration_seconds"] == 30
        assert data["total"] == 10
        assert data["passed"] == 9
        assert data["failed"] == 1
        assert len(data["failures"]) == 1

    def test_test_status_from_dict(self):
        """Test creating TestStatus from dictionary."""
        now = datetime.now(timezone.utc)
        data = {
            "ticket_id": "TEST-004",
            "status": "passing",
            "last_run": now.isoformat(),
            "duration_seconds": 45,
            "total": 100,
            "passed": 100,
            "failed": 0,
            "skipped": 0,
            "failures": [],
        }

        status = TestStatus.from_dict(data)

        assert status.ticket_id == "TEST-004"
        assert status.status == "passing"
        assert status.last_run == now
        assert status.duration_seconds == 45
        assert status.total == 100

    def test_test_status_from_dict_with_failures(self):
        """Test creating TestStatus from dict with failures."""
        data = {
            "ticket_id": "TEST-005",
            "status": "failing",
            "total": 10,
            "passed": 8,
            "failed": 2,
            "skipped": 0,
            "failures": [
                {"name": "test1", "message": "Error 1", "file": None, "line": None},
                {"name": "test2", "message": "Error 2", "file": "test.py", "line": 10},
            ],
        }

        status = TestStatus.from_dict(data)

        assert len(status.failures) == 2
        assert isinstance(status.failures[0], TestFailure)
        assert status.failures[1].file == "test.py"


class TestTestStatusPaths:
    """Tests for test status file path functions."""

    @patch("ccc.test_status.get_ticket_dir")
    def test_get_test_status_path(self, mock_get_ticket_dir):
        """Test getting test status file path."""
        mock_get_ticket_dir.return_value = Path("/home/user/.ccc-control/TEST-001")

        path = get_test_status_path("TEST-001")

        assert path == Path("/home/user/.ccc-control/TEST-001/test-status.json")
        mock_get_ticket_dir.assert_called_once_with("TEST-001")


class TestReadWriteTestStatus:
    """Tests for reading and writing test status files."""

    @patch("ccc.test_status.get_test_status_path")
    @patch("builtins.open", new_callable=mock_open)
    def test_read_test_status_success(self, mock_file, mock_get_path):
        """Test successfully reading test status."""
        mock_get_path.return_value = Path("/tmp/test-status.json")
        now = datetime.now(timezone.utc)
        data = {
            "ticket_id": "TEST-001",
            "status": "passing",
            "last_run": now.isoformat(),
            "duration_seconds": 30,
            "total": 50,
            "passed": 50,
            "failed": 0,
            "skipped": 0,
            "failures": [],
        }

        with patch.object(Path, "exists", return_value=True):
            with patch("json.load", return_value=data):
                status = read_test_status("TEST-001")

        assert status is not None
        assert status.ticket_id == "TEST-001"
        assert status.passed == 50

    @patch("ccc.test_status.get_test_status_path")
    def test_read_test_status_file_not_exists(self, mock_get_path):
        """Test reading test status when file doesn't exist."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_get_path.return_value = mock_path

        status = read_test_status("TEST-001")

        assert status is None

    @patch("ccc.test_status.get_test_status_path")
    def test_read_test_status_error(self, mock_get_path):
        """Test reading test status with error."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        with patch("builtins.open", side_effect=Exception("JSON error")):
            status = read_test_status("TEST-001")

        assert status is None

    @patch("ccc.test_status.get_test_status_path")
    @patch("builtins.open", new_callable=mock_open)
    def test_write_test_status_success(self, mock_file, mock_get_path):
        """Test successfully writing test status."""
        mock_path = MagicMock()
        mock_path.parent.mkdir = MagicMock()
        mock_get_path.return_value = mock_path

        status = TestStatus(
            ticket_id="TEST-001",
            status="passing",
            total=50,
            passed=50,
            failed=0,
            skipped=0,
        )

        with patch("json.dump") as mock_json_dump:
            result = write_test_status(status)

        assert result is True
        assert status.last_run is not None
        mock_json_dump.assert_called_once()

    @patch("ccc.test_status.get_test_status_path")
    def test_write_test_status_error(self, mock_get_path):
        """Test writing test status with error."""
        mock_get_path.side_effect = Exception("Write error")

        status = TestStatus(
            ticket_id="TEST-001",
            status="passing",
            total=0,
            passed=0,
            failed=0,
            skipped=0,
        )
        result = write_test_status(status)

        assert result is False


class TestInitAndUpdateTestStatus:
    """Tests for initializing and updating test status."""

    @patch("ccc.test_status.write_test_status")
    def test_init_test_status(self, mock_write):
        """Test initializing test status."""
        mock_write.return_value = True

        init_test_status("TEST-001")

        mock_write.assert_called_once()
        call_args = mock_write.call_args[0][0]
        assert call_args.ticket_id == "TEST-001"
        assert call_args.status == "unknown"

    @patch("ccc.test_status.read_test_status")
    @patch("ccc.test_status.write_test_status")
    def test_update_test_status_new(self, mock_write, mock_read):
        """Test updating test status for new ticket."""
        mock_read.return_value = None
        mock_write.return_value = True

        result = update_test_status(
            "TEST-001",
            "passing",
            duration=30,
            total=50,
            passed=50,
            failed=0,
            skipped=0,
        )

        assert result is True
        mock_write.assert_called_once()
        call_args = mock_write.call_args[0][0]
        assert call_args.status == "passing"
        assert call_args.total == 50
        assert call_args.passed == 50

    @patch("ccc.test_status.read_test_status")
    @patch("ccc.test_status.write_test_status")
    def test_update_test_status_existing(self, mock_write, mock_read):
        """Test updating existing test status."""
        existing = TestStatus(
            ticket_id="TEST-001",
            status="passing",
            total=50,
            passed=50,
            failed=0,
            skipped=0,
        )
        mock_read.return_value = existing
        mock_write.return_value = True

        failures = [TestFailure("test1", "Error")]
        result = update_test_status(
            "TEST-001",
            "failing",
            failed=1,
            passed=49,
            failures=failures,
        )

        assert result is True
        call_args = mock_write.call_args[0][0]
        assert call_args.status == "failing"
        assert call_args.failed == 1
        assert len(call_args.failures) == 1


class TestParseTestOutput:
    """Tests for parsing test output from various frameworks."""

    def test_parse_jest_output(self):
        """Test parsing Jest test output."""
        output = """
        Test Suites: 5 passed, 5 total
        Tests: 2 failed, 47 passed, 1 skipped, 50 total
        Snapshots: 0 total
        Time: 12.345s
        """

        result = _parse_jest_output(output)

        assert result["total"] == 50
        assert result["passed"] == 47
        assert result["failed"] == 2
        assert result["skipped"] == 1

    def test_parse_jest_output_all_passing(self):
        """Test parsing Jest output with all tests passing."""
        output = "Tests: 50 passed, 50 total"

        result = _parse_jest_output(output)

        assert result["total"] == 50
        assert result["passed"] == 50
        assert result["failed"] == 0
        assert result["skipped"] == 0

    def test_parse_jest_output_no_match(self):
        """Test parsing Jest output with no matches."""
        output = "Some random output"

        result = _parse_jest_output(output)

        assert result["total"] == 0
        assert result["passed"] == 0

    def test_parse_pytest_output(self):
        """Test parsing pytest output."""
        output = "47 passed, 2 failed, 1 skipped in 12.34s"

        result = _parse_pytest_output(output)

        assert result["total"] == 50
        assert result["passed"] == 47
        assert result["failed"] == 2
        assert result["skipped"] == 1

    def test_parse_pytest_output_only_passed(self):
        """Test parsing pytest output with only passed tests."""
        output = "50 passed in 10.5s"

        result = _parse_pytest_output(output)

        assert result["total"] == 50
        assert result["passed"] == 50
        assert result["failed"] == 0

    def test_parse_go_output(self):
        """Test parsing Go test output."""
        output = """
PASS
FAIL
PASS
"""

        result = _parse_go_output(output)

        assert result["total"] == 3
        assert result["passed"] == 2
        assert result["failed"] == 1
        assert result["skipped"] == 0

    def test_parse_test_output_auto_detect_jest(self):
        """Test auto-detecting Jest output."""
        output = "Tests: 10 passed, 10 total"

        result = parse_test_output(output, framework="auto")

        assert result["total"] == 10
        assert result["passed"] == 10

    def test_parse_test_output_auto_detect_pytest(self):
        """Test auto-detecting pytest output."""
        output = "5 passed, 1 failed in 5s"

        result = parse_test_output(output, framework="pytest")

        # Should parse pytest format
        assert result["total"] == 6
        assert result["passed"] == 5
        assert result["failed"] == 1

    def test_parse_test_output_explicit_framework(self):
        """Test parsing with explicit framework."""
        output = "Tests: 20 passed, 20 total"

        result = parse_test_output(output, framework="jest")

        assert result["total"] == 20
        assert result["passed"] == 20

    def test_parse_test_output_unknown_framework(self):
        """Test parsing with unknown framework."""
        output = "Some output"

        result = parse_test_output(output, framework="unknown")

        # Should return zeros for unknown framework
        assert result["total"] == 0
        assert result["passed"] == 0


class TestFormatTestStatus:
    """Tests for formatting test status."""

    def test_format_test_status_passing(self):
        """Test formatting passing test status."""
        now = datetime.now(timezone.utc)
        status = TestStatus(
            ticket_id="TEST-001",
            status="passing",
            last_run=now,
            duration_seconds=30,
            total=50,
            passed=50,
            failed=0,
            skipped=0,
        )

        formatted = format_test_status(status)

        assert "✓" in formatted
        assert "50/50" in formatted
        assert "100%" in formatted
        assert "30s" in formatted

    def test_format_test_status_failing(self):
        """Test formatting failing test status."""
        now = datetime.now(timezone.utc)
        failures = [
            TestFailure("test1", "Error 1", "test.py", 10),
            TestFailure("test2", "Error 2"),
        ]
        status = TestStatus(
            ticket_id="TEST-001",
            status="failing",
            last_run=now,
            duration_seconds=25,
            total=50,
            passed=48,
            failed=2,
            skipped=0,
            failures=failures,
        )

        formatted = format_test_status(status)

        assert "⚠" in formatted
        assert "48/50" in formatted
        assert "96%" in formatted
        assert "Failed: 2 tests" in formatted
        assert "test1" in formatted
        assert "test2" in formatted
        assert "test.py:10" in formatted

    def test_format_test_status_unknown(self):
        """Test formatting unknown test status."""
        status = TestStatus(
            ticket_id="TEST-001",
            status="unknown",
            total=0,
            passed=0,
            failed=0,
            skipped=0,
        )

        formatted = format_test_status(status)

        assert "? Unknown" in formatted

    def test_format_test_status_with_skipped(self):
        """Test formatting test status with skipped tests."""
        now = datetime.now(timezone.utc)
        status = TestStatus(
            ticket_id="TEST-001",
            status="passing",
            last_run=now,
            total=50,
            passed=48,
            failed=0,
            skipped=2,
        )

        formatted = format_test_status(status)

        assert "Skipped: 2 tests" in formatted

    def test_format_test_status_many_failures(self):
        """Test formatting test status with many failures."""
        now = datetime.now(timezone.utc)
        failures = [TestFailure(f"test{i}", f"Error {i}") for i in range(10)]
        status = TestStatus(
            ticket_id="TEST-001",
            status="failing",
            last_run=now,
            total=50,
            passed=40,
            failed=10,
            skipped=0,
            failures=failures,
        )

        formatted = format_test_status(status)

        # Should show first 5 failures
        assert "test0" in formatted
        assert "test4" in formatted
        # Should indicate more failures
        assert "and 5 more" in formatted
