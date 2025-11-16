"""
External tool launcher for Command Center.

Provides functionality to launch external tools like IDE, Git UI, browser, and database clients.
"""

import os
import sys
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional

from ccc.config import Config
from ccc.session import TmuxSessionManager

logger = logging.getLogger("ccc.external_tools")


class ExternalToolLauncher:
    """
    Launches external tools from CCC.

    Supports launching IDE, Git UI, database clients, and opening URLs in browsers.
    """

    def __init__(self, config: Config, session_manager: TmuxSessionManager):
        """
        Initialize the external tool launcher.

        Args:
            config: CCC configuration object
            session_manager: Tmux session manager for launching tools in tmux
        """
        self.config = config
        self.session_manager = session_manager

    def launch_ide(self, file_path: str) -> bool:
        """
        Launch IDE to edit a file.

        Tries to use the configured IDE (default: Cursor), falls back to $EDITOR, then vim.

        Args:
            file_path: Path to the file to open

        Returns:
            True if successful, False otherwise
        """
        file_path = str(Path(file_path).resolve())

        # Try configured IDE first (default: cursor)
        ide_command = getattr(self.config, 'ide_command', 'cursor')
        ide_args = getattr(self.config, 'ide_args', None)

        # Ensure ide_args is a list
        if ide_args is None:
            ide_args = []

        logger.info(f"Attempting to launch IDE: {ide_command} with file: {file_path}")

        if shutil.which(ide_command):
            try:
                cmd = [ide_command] + ide_args + [file_path]
                logger.info(f"Running command: {' '.join(cmd)}")
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(f"Launched {ide_command} with {file_path}")
                return True
            except Exception as e:
                logger.warning(f"Failed to launch {ide_command}: {e}")
        else:
            logger.warning(f"{ide_command} not found in PATH")

        # Fallback to $EDITOR environment variable
        editor = os.environ.get('EDITOR')
        if editor and shutil.which(editor):
            try:
                logger.info(f"Falling back to $EDITOR: {editor}")
                subprocess.Popen([editor, file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(f"Launched $EDITOR ({editor}) with {file_path}")
                return True
            except Exception as e:
                logger.warning(f"Failed to launch $EDITOR ({editor}): {e}")

        # Final fallback to vim (should be available on most systems)
        if shutil.which('vim'):
            try:
                logger.info("Falling back to vim")
                subprocess.Popen(['vim', file_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info(f"Launched vim with {file_path}")
                return True
            except Exception as e:
                logger.error(f"Failed to launch vim: {e}")

        logger.error(f"No suitable editor found to open {file_path}")
        return False

    def launch_git_ui(self, directory: Optional[str] = None) -> bool:
        """
        Launch Git UI (lazygit) in a new temporary tmux window.

        Creates a new tmux window each time. Window closes when lazygit exits.

        Args:
            directory: Optional directory to launch git UI in. If not provided, uses current directory.

        Returns:
            True if successful, False otherwise
        """
        git_ui_command = getattr(self.config, 'git_ui_command', 'lazygit')
        git_ui_args = getattr(self.config, 'git_ui_args', None)

        # Ensure git_ui_args is a list
        if git_ui_args is None:
            git_ui_args = []

        # Check if git UI command is available
        if not shutil.which(git_ui_command):
            logger.error(f"Git UI command '{git_ui_command}' not found in PATH")
            return False

        try:
            # Get working directory to launch lazygit in
            # Use provided directory or current working directory
            cwd = directory if directory else os.getcwd()
            logger.info(f"Launching Git UI in directory: {cwd}")

            # Get current session (assumes we're running in a tmux session)
            current_session = os.environ.get('TMUX')
            if not current_session:
                # Not in tmux - open in a new terminal window (macOS/Linux)
                cmd_parts = [git_ui_command] + git_ui_args
                cmd_str = ' '.join(cmd_parts)

                if sys.platform == 'darwin':
                    # macOS: Open in new Terminal or iTerm2 window
                    try:
                        # Check if iTerm2 is running
                        result = subprocess.run(
                            ["osascript", "-e", 'tell application "System Events" to get name of processes'],
                            capture_output=True,
                            text=True,
                            timeout=1
                        )
                        processes = result.stdout.lower()

                        if "iterm2" in processes or "iterm" in processes:
                            # Use iTerm2 - cd to directory then run lazygit
                            applescript = f'''
                                tell application "iTerm"
                                    create window with default profile
                                    tell current session of current window
                                        write text "cd {cwd} && {cmd_str}"
                                    end tell
                                end tell
                            '''
                            subprocess.Popen(["osascript", "-e", applescript])
                            logger.info(f"Launched {git_ui_command} in new iTerm2 window at {cwd}")
                        else:
                            # Use Terminal.app - cd to directory then run lazygit
                            applescript = f'''
                                tell application "Terminal"
                                    do script "cd {cwd} && {cmd_str}"
                                    activate
                                end tell
                            '''
                            subprocess.Popen(["osascript", "-e", applescript])
                            logger.info(f"Launched {git_ui_command} in new Terminal window at {cwd}")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to launch in new terminal window: {e}")
                        return False
                else:
                    # Linux: Try to open in new terminal window
                    # Try common terminal emulators
                    full_cmd = f"cd {cwd} && {cmd_str}"
                    terminals = [
                        ['gnome-terminal', '--', 'bash', '-c', full_cmd],
                        ['konsole', '-e', 'bash', '-c', full_cmd],
                        ['xterm', '-e', 'bash', '-c', full_cmd],
                    ]

                    for term_cmd in terminals:
                        if shutil.which(term_cmd[0]):
                            subprocess.Popen(term_cmd)
                            logger.info(f"Launched {git_ui_command} in new {term_cmd[0]} window at {cwd}")
                            return True

                    logger.error("No suitable terminal emulator found")
                    return False

            # In tmux: Create new temporary tmux window for git UI
            # Using tmux directly for temporary window that closes on exit
            cmd_parts = [git_ui_command] + git_ui_args
            cmd_str = ' '.join(cmd_parts)

            # Create new window with git UI command in the current directory
            # The window will automatically close when the command exits
            result = subprocess.run([
                'tmux', 'new-window',
                '-n', 'git',  # Window name
                '-c', cwd,     # Start in current directory
                cmd_str
            ], check=True, capture_output=True, text=True)

            logger.info(f"Launched {git_ui_command} in new tmux window at {cwd}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to launch Git UI (tmux error): {e.stderr}")
            return False
        except Exception as e:
            logger.error(f"Failed to launch Git UI: {e}")
            return False

    def launch_database_client(self, connection_string: Optional[str] = None) -> bool:
        """
        Launch database client (TablePlus, DBeaver, etc.).

        Args:
            connection_string: Optional database connection string
                             If not provided, uses config.database_connection_string

        Returns:
            True if successful, False otherwise
        """
        db_client_command = getattr(self.config, 'db_client_command', 'open')
        db_client_args = getattr(self.config, 'db_client_args', ['-a', 'TablePlus'])

        conn_str = connection_string or getattr(self.config, 'database_connection_string', None)

        try:
            # Build command
            cmd = [db_client_command] + db_client_args

            # Add connection string if provided
            if conn_str:
                cmd.append(conn_str)

            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info(f"Launched database client: {' '.join(cmd)}")
            return True

        except Exception as e:
            logger.error(f"Failed to launch database client: {e}")
            return False

    def open_url(self, url: str) -> bool:
        """
        Open a URL in the default browser.

        Platform-specific: macOS uses 'open', Linux uses 'xdg-open', Windows uses 'start'.

        Args:
            url: URL to open

        Returns:
            True if successful, False otherwise
        """
        try:
            if sys.platform == 'darwin':
                # macOS
                subprocess.Popen(['open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform.startswith('linux'):
                # Linux
                subprocess.Popen(['xdg-open', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform == 'win32':
                # Windows
                subprocess.Popen(['start', url], shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                logger.error(f"Unsupported platform: {sys.platform}")
                return False

            logger.info(f"Opened URL: {url}")
            return True

        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")
            return False

    def open_jira_ticket(self, ticket_id: str) -> bool:
        """
        Open a Jira ticket in the browser.

        Uses config.jira_base_url to construct the full URL.

        Args:
            ticket_id: Jira ticket ID (e.g., "PROJ-123")

        Returns:
            True if successful, False otherwise
        """
        jira_base_url = getattr(self.config, 'jira_base_url', '')

        if not jira_base_url:
            logger.error("Jira base URL not configured. Set 'jira_base_url' in config.")
            return False

        # Construct full URL
        # Remove trailing slash from base URL if present
        base = jira_base_url.rstrip('/')
        url = f"{base}/browse/{ticket_id}"

        return self.open_url(url)

    def open_api_docs(self) -> bool:
        """
        Open API documentation in the browser.

        Uses config.api_docs_url.

        Returns:
            True if successful, False otherwise
        """
        api_docs_url = getattr(self.config, 'api_docs_url', '')

        if not api_docs_url:
            logger.error("API docs URL not configured. Set 'api_docs_url' in config.")
            return False

        return self.open_url(api_docs_url)

    def open_plan_file(self) -> bool:
        """
        Open PLAN.md file in IDE.

        Uses config.plan_file (default: "PLAN.md").

        Returns:
            True if successful, False otherwise
        """
        plan_file = getattr(self.config, 'plan_file', 'PLAN.md')
        return self.launch_ide(plan_file)

    def open_notes_file(self) -> bool:
        """
        Open NOTES.md file in IDE.

        Uses config.notes_file (default: "NOTES.md").

        Returns:
            True if successful, False otherwise
        """
        notes_file = getattr(self.config, 'notes_file', 'NOTES.md')
        return self.launch_ide(notes_file)

    def open_tasks_file(self) -> bool:
        """
        Open TASKS.md file in IDE.

        Uses config.tasks_file (default: "TASKS.md").

        Returns:
            True if successful, False otherwise
        """
        tasks_file = getattr(self.config, 'tasks_file', 'TASKS.md')
        return self.launch_ide(tasks_file)
