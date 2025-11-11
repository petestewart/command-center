"""
Tmux session management for Command Center
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict

import libtmux

from ccc.ticket import Ticket
from ccc.utils import print_error, print_success, print_warning


class TmuxSessionManager:
    """Manages tmux sessions for tickets."""

    def __init__(self):
        try:
            self.server = libtmux.Server()
        except Exception as e:
            raise RuntimeError(
                f"Failed to connect to tmux server: {e}\n"
                "Make sure tmux is installed and running."
            )

    def session_exists(self, session_name: str) -> bool:
        """Check if a tmux session exists."""
        try:
            return self.server.has_session(session_name)
        except Exception:
            return False

    def create_session(self, ticket: Ticket) -> bool:
        """
        Create a tmux session for a ticket with three windows:
        - agent (window 0)
        - server (window 1)
        - tests (window 2)

        Args:
            ticket: The ticket to create a session for

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if session already exists
            if self.session_exists(ticket.tmux_session):
                print_warning(f"Tmux session '{ticket.tmux_session}' already exists")
                return False

            worktree_path = Path(ticket.worktree_path)

            # Create the session with first window named "agent"
            session = self.server.new_session(
                session_name=ticket.tmux_session,
                window_name="agent",
                start_directory=str(worktree_path),
                attach=False,  # Don't attach immediately
            )

            # Create "server" window
            session.new_window(
                window_name="server",
                start_directory=str(worktree_path),
                attach=False,
            )

            # Create "tests" window
            session.new_window(
                window_name="tests",
                start_directory=str(worktree_path),
                attach=False,
            )

            # Select the first window (agent)
            session.select_window("agent")

            print_success(f"Created tmux session '{ticket.tmux_session}' with windows:")
            print_success("  - agent (window 0)")
            print_success("  - server (window 1)")
            print_success("  - tests (window 2)")

            return True

        except Exception as e:
            print_error(f"Failed to create tmux session: {e}")
            return False

    def kill_session(self, session_name: str) -> bool:
        """
        Kill a tmux session.

        Args:
            session_name: Name of the session to kill

        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.session_exists(session_name):
                print_warning(f"Tmux session '{session_name}' does not exist")
                return False

            session = self.server.find_where({"session_name": session_name})
            if session:
                session.kill_session()
                print_success(f"Killed tmux session '{session_name}'")
                return True
            else:
                print_warning(f"Could not find session '{session_name}'")
                return False

        except Exception as e:
            print_error(f"Failed to kill tmux session: {e}")
            return False

    def attach_to_window(self, session_name: str, window_name: str) -> bool:
        """
        Attach to a specific window in a tmux session.
        This will replace the current terminal with the tmux session.

        Args:
            session_name: Name of the tmux session
            window_name: Name of the window to attach to ("agent", "server", or "tests")

        Returns:
            True if attach command was executed, False otherwise
        """
        try:
            if not self.session_exists(session_name):
                print_error(f"Tmux session '{session_name}' does not exist")
                from ccc.utils import print_info

                print_info("The session may have been killed or never created.")
                print_info("You can recreate it by deleting and recreating the ticket:")
                print_info(
                    f"  ccc delete {session_name.replace('ccc-', '')} --keep-worktree"
                )
                print_info(f"  Then recreate the ticket with 'ccc create'")
                return False

            # Map window names to indices
            window_map = {
                "agent": 0,
                "server": 1,
                "tests": 2,
            }

            if window_name not in window_map:
                print_error(f"Invalid window name: {window_name}")
                print_error("Valid windows: agent, server, tests")
                return False

            window_idx = window_map[window_name]

            # Print instructions before attaching
            print_success(f"\nAttaching to {window_name} terminal...")
            print("Press [Ctrl-b] then [d] to detach and return to Command Center\n")

            # Execute tmux attach - this will replace current terminal
            # Using os.system because we want to replace the current process
            cmd = f"tmux attach-session -t {session_name}:{window_idx}"
            os.system(cmd)

            return True

        except Exception as e:
            print_error(f"Failed to attach to tmux session: {e}")
            return False

    def list_sessions(self) -> List[Dict[str, str]]:
        """
        List all tmux sessions.

        Returns:
            List of session info dictionaries
        """
        try:
            sessions = self.server.list_sessions()
            return [
                {
                    "name": s.name,
                    "windows": len(s.list_windows()),
                    "created": s.get("created", "unknown"),
                }
                for s in sessions
            ]
        except Exception as e:
            print_error(f"Failed to list tmux sessions: {e}")
            return []

    def get_session_info(self, session_name: str) -> Optional[Dict]:
        """
        Get information about a specific tmux session.

        Args:
            session_name: Name of the session

        Returns:
            Dictionary with session info, or None if not found
        """
        try:
            session = self.server.find_where({"session_name": session_name})
            if not session:
                return None

            windows = session.list_windows()
            return {
                "name": session.name,
                "windows": [w.name for w in windows],
                "window_count": len(windows),
            }

        except Exception as e:
            print_error(f"Failed to get session info: {e}")
            return None


def check_tmux_installed() -> bool:
    """
    Check if tmux is installed and accessible.

    Returns:
        True if tmux is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["tmux", "-V"], capture_output=True, text=True, check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_tmux_version() -> Optional[str]:
    """
    Get the installed tmux version.

    Returns:
        Version string, or None if tmux is not installed
    """
    try:
        result = subprocess.run(
            ["tmux", "-V"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
