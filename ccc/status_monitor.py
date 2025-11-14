"""
Server and database status monitoring for Command Center.

Provides real-time monitoring of server processes, database connections,
and health checks without blocking the UI.
"""

import json
import re
import threading
import time
import fcntl
import tempfile
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

import requests

from ccc.utils import get_branch_dir
from ccc.build_runner import CommandRunner


@dataclass
class ServerStatus:
    """Represents the current status of a server process."""

    state: str  # 'stopped', 'starting', 'healthy', 'unhealthy', 'error'
    url: Optional[str] = None
    port: Optional[int] = None
    error_message: Optional[str] = None
    last_check: Optional[datetime] = None
    uptime_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.last_check:
            data["last_check"] = self.last_check.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServerStatus":
        """Create from dictionary loaded from JSON."""
        if isinstance(data.get("last_check"), str):
            data["last_check"] = datetime.fromisoformat(data["last_check"])
        return cls(**data)


@dataclass
class DatabaseStatus:
    """Represents the current status of a database connection."""

    state: str  # 'stopped', 'connected', 'error'
    connection_string: Optional[str] = None
    error_message: Optional[str] = None
    last_check: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        if self.last_check:
            data["last_check"] = self.last_check.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatabaseStatus":
        """Create from dictionary loaded from JSON."""
        if isinstance(data.get("last_check"), str):
            data["last_check"] = datetime.fromisoformat(data["last_check"])
        return cls(**data)


@dataclass
class StatusBarState:
    """Complete status bar state including server, database, build, and tests."""

    server: ServerStatus
    database: DatabaseStatus
    build: Dict[str, Any]  # From existing build-status.json
    tests: Dict[str, Any]  # From existing test-status.json

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "server": self.server.to_dict(),
            "database": self.database.to_dict(),
            "build": self.build,
            "tests": self.tests,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatusBarState":
        """Create from dictionary loaded from JSON."""
        return cls(
            server=ServerStatus.from_dict(data.get("server", {})),
            database=DatabaseStatus.from_dict(data.get("database", {})),
            build=data.get("build", {}),
            tests=data.get("tests", {}),
        )


class LogPatternMatcher:
    """Parse subprocess output for server status patterns."""

    # Default patterns for common server frameworks
    DEFAULT_SERVER_READY_PATTERNS = [
        r"Server listening on.*:(\d+)",
        r"Ready on http://.*:(\d+)",
        r"Listening at.*:(\d+)",
        r"Started server on.*:(\d+)",
        r"Serving on http://.*:(\d+)",
    ]

    DEFAULT_SERVER_ERROR_PATTERNS = [
        r"^ERROR",
        r"EADDRINUSE",
        r"Fatal",
        r"uncaughtException",
        r"EACCES",
    ]

    def __init__(
        self,
        ready_patterns: Optional[List[str]] = None,
        error_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize pattern matcher with custom or default patterns.

        Args:
            ready_patterns: Custom regex patterns for server ready detection
            error_patterns: Custom regex patterns for error detection
        """
        self.ready_patterns = ready_patterns or self.DEFAULT_SERVER_READY_PATTERNS
        self.error_patterns = error_patterns or self.DEFAULT_SERVER_ERROR_PATTERNS

    def extract_server_url(self, line: str) -> Optional[str]:
        """
        Extract server URL from log line.

        Args:
            line: Log line to parse

        Returns:
            Server URL if found, None otherwise
        """
        for pattern in self.ready_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                # Extract port from first capture group
                port = match.group(1)
                return f"http://localhost:{port}"
        return None

    def is_error(self, line: str) -> bool:
        """
        Check if log line indicates an error.

        Args:
            line: Log line to check

        Returns:
            True if line matches error pattern, False otherwise
        """
        return any(re.search(pattern, line, re.IGNORECASE) for pattern in self.error_patterns)


class StatusMonitor:
    """
    Monitor server, database, build, and test status.

    Manages server processes, performs health checks, and maintains
    status state in a persistent file.
    """

    def __init__(
        self,
        branch_name: str,
        config: Dict[str, Any],
        on_status_change: Optional[Callable[[StatusBarState], None]] = None,
    ):
        """
        Initialize status monitor.

        Args:
            branch_name: Git branch name for this monitor
            config: Configuration dictionary
            on_status_change: Optional callback when status changes
        """
        self.branch_name = branch_name
        self.config = config
        self.on_status_change = on_status_change

        # State file
        branch_dir = get_branch_dir(branch_name)
        self.state_file = branch_dir / "status-bar.json"

        # Log pattern matcher
        ready_patterns = config.get("server_ready_patterns")
        error_patterns = config.get("server_error_patterns")
        self.log_matcher = LogPatternMatcher(ready_patterns, error_patterns)

        # Server process tracking
        self.server_runner: Optional[CommandRunner] = None
        self.server_start_time: Optional[datetime] = None

        # Health check tracking
        self._last_server_check: float = 0
        self._last_db_check: float = 0
        self._health_check_lock = threading.Lock()

    def start_server(self, worktree_path: Path) -> bool:
        """
        Start server process in tmux window 1.

        Args:
            worktree_path: Path to the git worktree

        Returns:
            True if server started successfully, False otherwise
        """
        if self.server_runner and self.server_runner._is_running:
            # Server already running
            return False

        # Get server command from config with default
        command = self.config.get("server_command", "npm run dev")

        # Update status to starting
        self._update_server_status(state="starting")

        try:
            # Create command runner with output callback
            self.server_runner = CommandRunner(
                command=command,
                cwd=worktree_path,
                callback=self._handle_server_output,
            )

            # Start in background thread
            thread = threading.Thread(
                target=self._run_server,
                daemon=True,
            )
            thread.start()

            self.server_start_time = datetime.now(timezone.utc)
            return True

        except Exception as e:
            self._update_server_status(
                state="error",
                error_message=f"Failed to start server: {e}",
            )
            return False

    def _run_server(self) -> None:
        """Run server process (called in background thread)."""
        try:
            exit_code, output = self.server_runner.run()

            # Server exited
            if exit_code == 0:
                self._update_server_status(state="stopped")
            else:
                self._update_server_status(
                    state="error",
                    error_message=f"Server exited with code {exit_code}",
                )
        except Exception as e:
            self._update_server_status(
                state="error",
                error_message=f"Server error: {e}",
            )

    def _handle_server_output(self, line: str) -> None:
        """
        Handle server output line.

        Parses output for server ready indicators and errors.

        Args:
            line: Output line from server process
        """
        # Check for server ready
        url = self.log_matcher.extract_server_url(line)
        if url:
            # Extract port from URL
            port_match = re.search(r":(\d+)", url)
            port = int(port_match.group(1)) if port_match else None

            self._update_server_status(
                state="healthy",
                url=url,
                port=port,
            )

        # Check for errors
        if self.log_matcher.is_error(line):
            current_status = self.load_status()
            # Only update to error if not already healthy
            # (avoid false positives from error handling logs)
            if current_status.server.state != "healthy":
                self._update_server_status(
                    state="error",
                    error_message=line.strip(),
                )

    def stop_server(self) -> bool:
        """
        Stop server process.

        Returns:
            True if server was stopped, False if not running
        """
        if not self.server_runner or not self.server_runner._is_running:
            return False

        try:
            # Terminate the process
            if self.server_runner.process:
                self.server_runner.process.terminate()

            self._update_server_status(state="stopped")
            self.server_runner = None
            self.server_start_time = None
            return True

        except Exception as e:
            self._update_server_status(
                state="error",
                error_message=f"Failed to stop server: {e}",
            )
            return False

    def check_server_health(self) -> None:
        """
        Perform HTTP health check on server.

        Runs asynchronously to avoid blocking UI.
        Uses configured interval to avoid excessive checks.
        """
        # Get interval from config (default 10 seconds)
        interval = self.config.get("server_health_check_interval", 10)

        # Check if enough time has passed
        if time.time() - self._last_server_check < interval:
            return

        # Load current status
        status = self.load_status()
        if not status.server.url:
            return

        # Run health check in background thread
        def _check():
            try:
                with self._health_check_lock:
                    self._last_server_check = time.time()

                # Get health check URL from config or use server URL
                health_url = self.config.get(
                    "server_health_check_url",
                    status.server.url,
                )

                # Perform request with short timeout
                timeout = self.config.get("server_health_check_timeout", 2)
                response = requests.get(health_url, timeout=timeout)

                # Update status based on response
                if response.status_code == 200:
                    uptime = None
                    if self.server_start_time:
                        uptime = (datetime.now(timezone.utc) - self.server_start_time).total_seconds()

                    self._update_server_status(
                        state="healthy",
                        uptime_seconds=uptime,
                    )
                else:
                    self._update_server_status(
                        state="unhealthy",
                        error_message=f"HTTP {response.status_code}",
                    )

            except requests.RequestException as e:
                self._update_server_status(
                    state="unhealthy",
                    error_message=str(e),
                )

        thread = threading.Thread(target=_check, daemon=True)
        thread.start()

    def check_database_connection(self) -> None:
        """
        Check database connectivity.

        Runs asynchronously to avoid blocking UI.
        Uses configured interval to avoid excessive checks.
        """
        # Get interval from config (default 30 seconds)
        interval = self.config.get("database_health_check_interval", 30)

        # Check if enough time has passed
        if time.time() - self._last_db_check < interval:
            return

        # Get connection string from config
        conn_string = self.config.get("database_connection_string")
        if not conn_string:
            return

        # Run check in background thread
        def _check():
            try:
                with self._health_check_lock:
                    self._last_db_check = time.time()

                # Simple TCP socket check for PostgreSQL
                # (Could be enhanced to use psycopg2 for actual connection test)
                import socket

                # Parse host and port from connection string
                # Format: postgresql://user:pass@host:port/dbname
                match = re.search(r"@([^:]+):(\d+)", conn_string)
                if match:
                    host = match.group(1)
                    port = int(match.group(2))

                    # Try to connect
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((host, port))
                    sock.close()

                    if result == 0:
                        self._update_database_status(state="connected")
                    else:
                        self._update_database_status(
                            state="error",
                            error_message="Connection refused",
                        )
                else:
                    self._update_database_status(
                        state="error",
                        error_message="Invalid connection string format",
                    )

            except Exception as e:
                self._update_database_status(
                    state="error",
                    error_message=str(e),
                )

        thread = threading.Thread(target=_check, daemon=True)
        thread.start()

    def _update_server_status(self, **kwargs) -> None:
        """Update server status in state file."""
        status = self.load_status()

        # Update server fields
        for key, value in kwargs.items():
            if hasattr(status.server, key):
                setattr(status.server, key, value)

        # Update last check time
        status.server.last_check = datetime.now(timezone.utc)

        # Save and notify
        self.save_status(status)

        if self.on_status_change:
            self.on_status_change(status)

    def _update_database_status(self, **kwargs) -> None:
        """Update database status in state file."""
        status = self.load_status()

        # Update database fields
        for key, value in kwargs.items():
            if hasattr(status.database, key):
                setattr(status.database, key, value)

        # Update last check time
        status.database.last_check = datetime.now(timezone.utc)

        # Save and notify
        self.save_status(status)

        if self.on_status_change:
            self.on_status_change(status)

    def load_status(self) -> StatusBarState:
        """
        Load status from file.

        Returns:
            Current status bar state, or default if file doesn't exist
        """
        if not self.state_file.exists():
            return self._default_status()

        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
            return StatusBarState.from_dict(data)

        except Exception:
            # If file is corrupted, return default
            return self._default_status()

    def save_status(self, status: StatusBarState) -> None:
        """
        Save status to file using atomic write with file locking.

        Args:
            status: Status state to save
        """
        try:
            # Ensure directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Create temp file in same directory
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.state_file.parent,
                prefix=".tmp-status-",
                suffix=".json",
            )

            try:
                # Write to temp file with lock
                with os.fdopen(temp_fd, "w") as f:
                    fcntl.flock(f, fcntl.LOCK_EX)
                    json.dump(status.to_dict(), f, indent=2, default=str)
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic rename
                os.rename(temp_path, self.state_file)

            finally:
                # Cleanup temp file if rename failed
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

        except Exception:
            # Silently fail - don't crash on status update
            pass

    def _default_status(self) -> StatusBarState:
        """Create default status state."""
        return StatusBarState(
            server=ServerStatus(state="stopped"),
            database=DatabaseStatus(state="stopped"),
            build={},
            tests={},
        )
