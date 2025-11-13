"""
Build and test command runner with streaming output support.
"""

import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional, List, Tuple
from datetime import datetime, timezone
import logging

from ccc.config import Config, load_config
from ccc.build_status import BuildStatus, write_build_status
from ccc.test_status import TestStatus, write_test_status
from ccc.utils import get_branch_dir, sanitize_branch_name


# Set up logging
logger = logging.getLogger("ccc.build_runner")
logger.setLevel(logging.DEBUG)


class CommandRunner:
    """
    Runs a command with streaming output support.

    Executes commands in a subprocess and streams output line by line
    to a callback function.
    """

    def __init__(
        self,
        command: str,
        cwd: Path,
        callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Initialize the command runner.

        Args:
            command: Shell command to execute
            cwd: Working directory for the command
            callback: Optional callback function for each line of output
        """
        self.command = command
        self.cwd = Path(cwd)
        self.callback = callback
        self.process: Optional[subprocess.Popen] = None
        self.output_lines: List[str] = []
        self.returncode: Optional[int] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._is_running = False

    def run(self) -> Tuple[int, List[str]]:
        """
        Run the command synchronously and collect output.

        Returns:
            Tuple of (return_code, list of output lines)
        """
        self.start_time = datetime.now(timezone.utc)
        self._is_running = True

        try:
            self.process = subprocess.Popen(
                self.command,
                shell=True,
                cwd=str(self.cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True,
            )

            # Read output line by line and stream to callback
            try:
                if self.process.stdout:
                    for line in self.process.stdout:
                        line = line.rstrip("\n")
                        self.output_lines.append(line)

                        # Call callback if provided
                        if self.callback:
                            self.callback(line)
            except (IOError, OSError, ValueError):
                # Handle broken pipe or closed file errors
                # This can happen if process exits before we finish reading
                pass
            finally:
                # Close stdout to ensure the iteration completes
                if self.process and self.process.stdout:
                    self.process.stdout.close()

                # Ensure process is fully finished
                if self.process:
                    self.process.wait()
                    self.returncode = self.process.returncode

        except Exception as e:
            logger.error(f"Error running command: {e}", exc_info=True)
            error_msg = f"Error: {e}"
            self.output_lines.append(error_msg)
            if self.callback:
                self.callback(error_msg)
            self.returncode = 1

        finally:
            self.end_time = datetime.now(timezone.utc)
            self._is_running = False

        return self.returncode, self.output_lines

    def run_async(self, on_complete: Optional[Callable[[int, List[str]], None]] = None) -> threading.Thread:
        """
        Run the command asynchronously in a background thread.

        Args:
            on_complete: Optional callback when command completes

        Returns:
            The thread object running the command
        """
        def _run():
            returncode, output = self.run()
            if on_complete:
                on_complete(returncode, output)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread

    def get_duration(self) -> Optional[float]:
        """
        Get command execution duration in seconds.

        Returns:
            Duration in seconds, or None if not yet complete
        """
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def is_running(self) -> bool:
        """Check if the command is currently running."""
        return self._is_running

    def kill(self) -> None:
        """Kill the running process."""
        if self.process and self._is_running:
            self.process.kill()
            self._is_running = False


def run_build(
    worktree_path: Path,
    branch_name: str,
    on_output: Optional[Callable[[str], None]] = None,
    on_complete: Optional[Callable[[bool, str], None]] = None,
) -> CommandRunner:
    """
    Run the build command for a worktree.

    Args:
        worktree_path: Path to the worktree
        branch_name: Branch name (for status file)
        on_output: Callback for each line of output
        on_complete: Callback when build completes (success, message)

    Returns:
        CommandRunner instance
    """
    config = load_config()
    build_command = config.get_build_command(worktree_path)

    runner = CommandRunner(build_command, worktree_path, on_output)

    def _on_complete(returncode: int, output: List[str]) -> None:
        """Handle build completion."""
        success = returncode == 0
        duration = runner.get_duration()

        # Save build status
        status = BuildStatus(
            branch_name=branch_name,
            status="passing" if success else "failing",
            last_build=datetime.now(timezone.utc),
            duration_seconds=int(duration) if duration else 0,
            errors=[line for line in output if "error" in line.lower()][:10],  # Keep first 10 errors
            warnings=len([line for line in output if "warning" in line.lower()]),
        )

        try:
            write_build_status(status)
        except Exception as e:
            logger.error(f"Failed to save build status: {e}")

        # Call user callback
        if on_complete:
            message = f"Build {'succeeded' if success else 'failed'}"
            if duration:
                message += f" in {duration:.1f}s"
            on_complete(success, message)

    # Run asynchronously
    runner.run_async(_on_complete)
    return runner


def run_tests(
    worktree_path: Path,
    branch_name: str,
    on_output: Optional[Callable[[str], None]] = None,
    on_complete: Optional[Callable[[bool, str], None]] = None,
) -> CommandRunner:
    """
    Run the test command for a worktree.

    Args:
        worktree_path: Path to the worktree
        branch_name: Branch name (for status file)
        on_output: Callback for each line of output
        on_complete: Callback when tests complete (success, message)

    Returns:
        CommandRunner instance
    """
    config = load_config()
    test_command = config.get_test_command(worktree_path)

    runner = CommandRunner(test_command, worktree_path, on_output)

    def _on_complete(returncode: int, output: List[str]) -> None:
        """Handle test completion."""
        success = returncode == 0
        duration = runner.get_duration()

        # Parse test output for pass/fail counts
        # This is a simple parser - could be enhanced for specific test frameworks
        passed = 0
        failed = 0
        skipped = 0

        for line in output:
            line_lower = line.lower()
            # Try to parse common test output patterns
            if "passed" in line_lower or "ok" in line_lower:
                # Extract numbers if present
                import re
                match = re.search(r'(\d+)\s+passed', line_lower)
                if match:
                    passed = int(match.group(1))
            if "failed" in line_lower or "error" in line_lower:
                match = re.search(r'(\d+)\s+failed', line_lower)
                if match:
                    failed = int(match.group(1))
            if "skipped" in line_lower:
                match = re.search(r'(\d+)\s+skipped', line_lower)
                if match:
                    skipped = int(match.group(1))

        # Save test status
        status = TestStatus(
            branch_name=branch_name,
            status="passing" if success else "failing",
            last_run=datetime.now(timezone.utc),
            duration_seconds=int(duration) if duration else 0,
            total=passed + failed + skipped,
            passed=passed,
            failed=failed,
            skipped=skipped,
            failures=[],  # Would need more sophisticated parsing for actual failures
        )

        try:
            write_test_status(status)
        except Exception as e:
            logger.error(f"Failed to save test status: {e}")

        # Call user callback
        if on_complete:
            if passed > 0 or failed > 0:
                message = f"{passed} passed, {failed} failed"
            else:
                message = f"Tests {'passed' if success else 'failed'}"
            if duration:
                message += f" in {duration:.1f}s"
            on_complete(success, message)

    # Run asynchronously
    runner.run_async(_on_complete)
    return runner
