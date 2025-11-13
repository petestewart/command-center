"""
Test status tracking for tickets.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field

from ccc.utils import get_branch_dir, print_warning, print_error, format_time_ago


@dataclass
class TestFailure:
    """Represents a test failure."""

    name: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestFailure":
        return cls(**data)


@dataclass
class TestStatus:
    """Represents the test status of a branch."""

    branch_name: str
    status: str  # "passing", "failing", "unknown"
    last_run: Optional[datetime] = None
    duration_seconds: int = 0
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: List[TestFailure] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.last_run:
            data["last_run"] = self.last_run.isoformat()
        data["failures"] = [f.to_dict() for f in self.failures]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestStatus":
        """Create from dictionary (loaded from JSON)."""
        if isinstance(data.get("last_run"), str):
            data["last_run"] = datetime.fromisoformat(data["last_run"])

        # Handle failures
        if "failures" in data:
            data["failures"] = [
                TestFailure.from_dict(f) if isinstance(f, dict) else f
                for f in data["failures"]
            ]
        else:
            data["failures"] = []

        return cls(**data)


def get_test_status_path(branch_name: str) -> Path:
    """Get the path to the test status file for a branch."""
    return get_branch_dir(branch_name) / "test-status.json"


def read_test_status(branch_name: str) -> Optional[TestStatus]:
    """
    Read test status from file.

    Args:
        branch_name: The branch name

    Returns:
        TestStatus if file exists and is valid, None otherwise
    """
    status_file = get_test_status_path(branch_name)

    if not status_file.exists():
        return None

    try:
        with open(status_file, "r") as f:
            data = json.load(f)

        return TestStatus.from_dict(data)

    except Exception as e:
        print_warning(f"Error reading test status for {branch_name}: {e}")
        return None


def write_test_status(status: TestStatus) -> bool:
    """
    Write test status to file.

    Args:
        status: The test status to write

    Returns:
        True if successful, False otherwise
    """
    try:
        status_file = get_test_status_path(status.branch_name)

        # Ensure directory exists
        status_file.parent.mkdir(parents=True, exist_ok=True)

        # Update timestamp if not set
        if status.last_run is None:
            status.last_run = datetime.now(timezone.utc)

        with open(status_file, "w") as f:
            json.dump(status.to_dict(), f, indent=2)

        return True

    except Exception as e:
        print_error(f"Error writing test status: {e}")
        return False


def init_test_status(branch_name: str) -> None:
    """
    Initialize a test status file for a new branch.

    Args:
        branch_name: The branch name
    """
    status = TestStatus(
        branch_name=branch_name,
        status="unknown",
    )
    write_test_status(status)


def update_test_status(
    branch_name: str,
    status: str,
    duration: Optional[int] = None,
    total: Optional[int] = None,
    passed: Optional[int] = None,
    failed: Optional[int] = None,
    skipped: Optional[int] = None,
    failures: Optional[List[TestFailure]] = None,
) -> bool:
    """
    Update test status (helper function for CLI).

    Args:
        branch_name: The branch name
        status: Test status ("passing" or "failing")
        duration: Test run duration in seconds
        total: Total number of tests
        passed: Number of passed tests
        failed: Number of failed tests
        skipped: Number of skipped tests
        failures: List of test failures

    Returns:
        True if successful, False otherwise
    """
    # Read existing status or create new
    test_status = read_test_status(branch_name)
    if test_status is None:
        test_status = TestStatus(branch_name=branch_name, status=status)
    else:
        test_status.status = status

    # Update fields
    test_status.last_run = datetime.now(timezone.utc)

    if duration is not None:
        test_status.duration_seconds = duration

    if total is not None:
        test_status.total = total

    if passed is not None:
        test_status.passed = passed

    if failed is not None:
        test_status.failed = failed

    if skipped is not None:
        test_status.skipped = skipped

    if failures is not None:
        test_status.failures = failures

    return write_test_status(test_status)


def parse_test_output(output: str, framework: str = "auto") -> Dict[str, Any]:
    """
    Parse test output from common frameworks.

    Args:
        output: Test output text
        framework: Framework type ("jest", "pytest", "go", "auto")

    Returns:
        Dictionary with parsed test results
    """
    if framework == "auto":
        # Auto-detect framework
        if "jest" in output.lower() or "Tests:" in output:
            framework = "jest"
        elif "pytest" in output.lower() or "passed," in output:
            framework = "pytest"
        elif "PASS" in output and "FAIL" in output and "ok  " in output:
            framework = "go"

    if framework == "jest":
        return _parse_jest_output(output)
    elif framework == "pytest":
        return _parse_pytest_output(output)
    elif framework == "go":
        return _parse_go_output(output)
    else:
        # Generic parsing
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        }


def _parse_jest_output(output: str) -> Dict[str, Any]:
    """Parse Jest test output."""
    # Example: "Tests: 2 failed, 47 passed, 1 skipped, 50 total"
    pattern = r"Tests:\s+(?:(\d+)\s+failed,?\s*)?(?:(\d+)\s+passed,?\s*)?(?:(\d+)\s+skipped,?\s*)?(\d+)\s+total"
    match = re.search(pattern, output)

    if match:
        failed = int(match.group(1)) if match.group(1) else 0
        passed = int(match.group(2)) if match.group(2) else 0
        skipped = int(match.group(3)) if match.group(3) else 0
        total = int(match.group(4))

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }

    return {"total": 0, "passed": 0, "failed": 0, "skipped": 0}


def _parse_pytest_output(output: str) -> Dict[str, Any]:
    """Parse pytest test output."""
    # Example: "47 passed, 2 failed, 1 skipped in 12.34s"
    # Pattern requires at least one of passed/failed/skipped with their numbers
    pattern = r"(\d+)\s+passed(?:,\s*(\d+)\s+failed)?(?:,\s*(\d+)\s+skipped)?|(\d+)\s+failed(?:,\s*(\d+)\s+skipped)?|(\d+)\s+skipped"
    match = re.search(pattern, output)

    if match:
        # Handle different match groups depending on what was found
        groups = match.groups()
        passed = int(groups[0]) if groups[0] else (0)
        failed = int(groups[1]) if groups[1] else (int(groups[3]) if groups[3] else 0)
        skipped = int(groups[2]) if groups[2] else (int(groups[4]) if groups[4] else (int(groups[5]) if groups[5] else 0))
        total = passed + failed + skipped

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }

    return {"total": 0, "passed": 0, "failed": 0, "skipped": 0}


def _parse_go_output(output: str) -> Dict[str, Any]:
    """Parse Go test output."""
    # Count individual test results (--- PASS: and --- FAIL:)
    passed = len(re.findall(r"^---\s+PASS:", output, re.MULTILINE))
    failed = len(re.findall(r"^---\s+FAIL:", output, re.MULTILINE))
    total = passed + failed

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": 0,
    }


def format_test_status(status: TestStatus) -> str:
    """
    Format test status for display.

    Args:
        status: TestStatus object

    Returns:
        Formatted string
    """
    lines = []

    # Status indicator
    if status.status == "passing":
        lines.append(f"Status: ✓ {status.passed}/{status.total} passing (100%)")
    elif status.status == "failing":
        percentage = (status.passed / status.total * 100) if status.total > 0 else 0
        lines.append(f"Status: ⚠ {status.passed}/{status.total} passing ({percentage:.0f}%)")
    else:
        lines.append("Status: ? Unknown")

    # Test details
    if status.last_run:
        if status.failed > 0:
            lines.append(f"Failed: {status.failed} tests")
        if status.skipped > 0:
            lines.append(f"Skipped: {status.skipped} tests")
        lines.append(f"Last run: {format_time_ago(status.last_run)} (took {status.duration_seconds}s)")

    # Failures
    if status.failures:
        lines.append("\nFailures:")
        for failure in status.failures[:5]:  # Show first 5 failures
            lines.append(f"  • {failure.name}")
            if failure.file:
                location = failure.file
                if failure.line:
                    location += f":{failure.line}"
                lines.append(f"    {location}")
        if len(status.failures) > 5:
            lines.append(f"  ... and {len(status.failures) - 5} more")

    return '\n'.join(lines)
