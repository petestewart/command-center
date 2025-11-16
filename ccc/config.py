"""
Configuration management for Command Center
"""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from ccc.utils import get_ccc_home, expand_path, sanitize_branch_name, print_warning


@dataclass
class Config:
    """Command Center configuration."""

    # Base path for git worktrees
    base_worktree_path: str = "~/code/worktrees"

    # Status polling interval in seconds
    status_poll_interval: int = 3

    # Tmux session name prefix
    tmux_session_prefix: str = "ccc-"

    # Default git remote name
    default_git_remote: str = "origin"

    # Default repository path (where worktrees are created from)
    # If not set, will use current git repository
    base_repo_path: Optional[str] = None

    # Phase 2: Cache settings
    git_status_cache_seconds: int = 10
    build_status_cache_seconds: int = 30
    test_status_cache_seconds: int = 30

    # Phase 1: Server configuration
    server_command: str = "npm run dev"  # Default server start command
    server_auto_start: bool = False  # Never auto-start server (manual only)
    server_health_check_interval: int = 10  # Health check interval in seconds
    server_health_check_timeout: int = 2  # Health check timeout in seconds

    # Custom regex patterns for server ready detection (optional)
    # If not set, uses default patterns in LogPatternMatcher
    server_ready_patterns: Optional[list[str]] = None
    server_error_patterns: Optional[list[str]] = None

    # Phase 1: Database configuration
    database_type: str = "postgresql"  # Database type: postgresql, mysql, etc.
    database_connection_string: Optional[str] = None  # e.g., "postgresql://localhost:5432/mydb"
    database_health_check_interval: int = 30  # Health check interval in seconds

    # Phase 3: Build and test commands
    # Global default commands (used if no project-specific override)
    default_build_command: str = "npm run build"
    default_test_command: str = "npm test"

    # Per-project command overrides
    # Format: {"project-name": {"build_command": "...", "test_command": "...", "server_command": "..."}}
    project_commands: Optional[Dict[str, Dict[str, str]]] = None

    # Diff viewer configuration
    diff_viewer: str = "delta"  # Options: "delta", "diff-so-fancy", "git"

    # Editor configuration (falls back to $EDITOR env var, then vim)
    editor: Optional[str] = None

    # Phase 4: Todo configuration
    todos_auto_assign_first_task: bool = True
    todos_show_completed: bool = True
    todos_max_display: int = 10
    todos_estimate_in_hours: bool = False

    # Phase 6: Claude CLI & Communication settings
    claude_cli_path: str = "claude"  # Path to claude CLI binary
    claude_timeout: int = 30  # Timeout in seconds for Claude responses
    chat_history_limit: int = 50  # Max messages to keep in history
    chat_context_window: int = 10  # Recent messages to include in context
    questions_notification_style: str = "banner"  # "banner", "toast", "silent"
    questions_auto_dismiss: int = 3600  # Auto-dismiss questions after N seconds

    # Phase 7: API Testing settings
    api_default_timeout: int = 30
    api_follow_redirects: bool = True
    api_max_history_entries: int = 50
    api_verify_ssl: bool = True

    # Phase 2: External Tool Launchers
    # IDE configuration
    ide_command: str = "cursor"  # Default IDE (cursor, code, vim, etc.)
    ide_args: list[str] = None  # Additional arguments for IDE

    # Git UI configuration
    git_ui_command: str = "lazygit"  # Git UI tool (lazygit, tig, etc.)
    git_ui_args: list[str] = None  # Additional arguments for git UI

    # Database client configuration
    db_client_command: str = "open"  # Command to open database client
    db_client_args: list[str] = None  # Arguments for database client (e.g., ["-a", "TablePlus"])

    # URL configuration
    jira_base_url: str = ""  # Base URL for Jira (e.g., "https://company.atlassian.net")
    api_docs_url: str = ""  # URL for API documentation

    # File paths
    plan_file: str = "PLAN.md"  # Path to plan file
    notes_file: str = "NOTES.md"  # Path to notes file
    tasks_file: str = "TASKS.md"  # Path to tasks file

    def get_worktree_path(self, branch_name: str) -> Path:
        """
        Get the worktree path for a specific branch.

        The branch name is sanitized for filesystem compatibility (e.g., slashes replaced with underscores).
        """
        base = expand_path(self.base_worktree_path)
        sanitized = sanitize_branch_name(branch_name)
        return base / sanitized

    def get_project_name(self, worktree_path: Path) -> Optional[str]:
        """
        Detect project name from worktree path.

        Looks for common project identifiers (package.json, setup.py, Cargo.toml, etc.)
        and extracts the project name.

        Args:
            worktree_path: Path to the worktree

        Returns:
            Project name if detected, None otherwise
        """
        import json
        import re

        worktree_path = Path(worktree_path)

        # Check for package.json (Node.js)
        package_json = worktree_path / "package.json"
        if package_json.exists():
            try:
                with open(package_json) as f:
                    data = json.load(f)
                    return data.get("name")
            except Exception:
                pass

        # Check for pyproject.toml (Python) - simple regex parsing
        pyproject = worktree_path / "pyproject.toml"
        if pyproject.exists():
            try:
                with open(pyproject) as f:
                    content = f.read()
                    # Look for [project] name = "..."
                    match = re.search(r'\[project\].*?name\s*=\s*["\']([^"\']+)["\']', content, re.DOTALL)
                    if match:
                        return match.group(1)
                    # Look for [tool.poetry] name = "..."
                    match = re.search(r'\[tool\.poetry\].*?name\s*=\s*["\']([^"\']+)["\']', content, re.DOTALL)
                    if match:
                        return match.group(1)
            except Exception:
                pass

        # Check for Cargo.toml (Rust) - simple regex parsing
        cargo_toml = worktree_path / "Cargo.toml"
        if cargo_toml.exists():
            try:
                with open(cargo_toml) as f:
                    content = f.read()
                    # Look for [package] name = "..."
                    match = re.search(r'\[package\].*?name\s*=\s*["\']([^"\']+)["\']', content, re.DOTALL)
                    if match:
                        return match.group(1)
            except Exception:
                pass

        return None

    def get_build_command(self, worktree_path: Path) -> str:
        """
        Get the build command for a specific project.

        Checks for project-specific override, falls back to default.

        Args:
            worktree_path: Path to the worktree

        Returns:
            Build command to execute
        """
        project_name = self.get_project_name(worktree_path)

        if project_name and self.project_commands:
            project_config = self.project_commands.get(project_name, {})
            if "build_command" in project_config:
                return project_config["build_command"]

        return self.default_build_command

    def get_test_command(self, worktree_path: Path) -> str:
        """
        Get the test command for a specific project.

        Checks for project-specific override, falls back to default.

        Args:
            worktree_path: Path to the worktree

        Returns:
            Test command to execute
        """
        project_name = self.get_project_name(worktree_path)

        if project_name and self.project_commands:
            project_config = self.project_commands.get(project_name, {})
            if "test_command" in project_config:
                return project_config["test_command"]

        return self.default_test_command

    def get_server_command(self, worktree_path: Path) -> str:
        """
        Get the server command for a specific project.

        Checks for project-specific override, falls back to default.

        Args:
            worktree_path: Path to the worktree

        Returns:
            Server command to execute
        """
        project_name = self.get_project_name(worktree_path)

        if project_name and self.project_commands:
            project_config = self.project_commands.get(project_name, {})
            if "server_command" in project_config:
                return project_config["server_command"]

        return self.server_command

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_ccc_home() / "config.yaml"


def load_config() -> Config:
    """
    Load configuration from ~/.ccc-control/config.yaml.
    Creates default config if it doesn't exist.
    """
    config_path = get_config_path()

    if not config_path.exists():
        # Create default config
        config = Config()
        save_config(config)
        return config

    try:
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}

        # Create config with values from file, using defaults for missing values
        config = Config(
            base_worktree_path=data.get(
                "base_worktree_path", Config.base_worktree_path
            ),
            status_poll_interval=data.get(
                "status_poll_interval", Config.status_poll_interval
            ),
            tmux_session_prefix=data.get(
                "tmux_session_prefix", Config.tmux_session_prefix
            ),
            default_git_remote=data.get(
                "default_git_remote", Config.default_git_remote
            ),
            base_repo_path=data.get("base_repo_path"),
            git_status_cache_seconds=data.get(
                "git_status_cache_seconds", Config.git_status_cache_seconds
            ),
            build_status_cache_seconds=data.get(
                "build_status_cache_seconds", Config.build_status_cache_seconds
            ),
            test_status_cache_seconds=data.get(
                "test_status_cache_seconds", Config.test_status_cache_seconds
            ),
            server_command=data.get(
                "server_command", Config.server_command
            ),
            server_auto_start=data.get(
                "server_auto_start", Config.server_auto_start
            ),
            server_health_check_interval=data.get(
                "server_health_check_interval", Config.server_health_check_interval
            ),
            server_health_check_timeout=data.get(
                "server_health_check_timeout", Config.server_health_check_timeout
            ),
            server_ready_patterns=data.get("server_ready_patterns"),
            server_error_patterns=data.get("server_error_patterns"),
            database_type=data.get(
                "database_type", Config.database_type
            ),
            database_connection_string=data.get("database_connection_string"),
            database_health_check_interval=data.get(
                "database_health_check_interval", Config.database_health_check_interval
            ),
            default_build_command=data.get(
                "default_build_command", Config.default_build_command
            ),
            default_test_command=data.get(
                "default_test_command", Config.default_test_command
            ),
            project_commands=data.get("project_commands"),
            diff_viewer=data.get("diff_viewer", Config.diff_viewer),
            editor=data.get("editor"),
            todos_auto_assign_first_task=data.get(
                "todos_auto_assign_first_task", Config.todos_auto_assign_first_task
            ),
            todos_show_completed=data.get(
                "todos_show_completed", Config.todos_show_completed
            ),
            todos_max_display=data.get(
                "todos_max_display", Config.todos_max_display
            ),
            todos_estimate_in_hours=data.get(
                "todos_estimate_in_hours", Config.todos_estimate_in_hours
            ),
            claude_cli_path=data.get(
                "claude_cli_path", Config.claude_cli_path
            ),
            claude_timeout=data.get(
                "claude_timeout", Config.claude_timeout
            ),
            chat_history_limit=data.get(
                "chat_history_limit", Config.chat_history_limit
            ),
            chat_context_window=data.get(
                "chat_context_window", Config.chat_context_window
            ),
            questions_notification_style=data.get(
                "questions_notification_style", Config.questions_notification_style
            ),
            questions_auto_dismiss=data.get(
                "questions_auto_dismiss", Config.questions_auto_dismiss
            ),
            api_default_timeout=data.get(
                "api_default_timeout", Config.api_default_timeout
            ),
            api_follow_redirects=data.get(
                "api_follow_redirects", Config.api_follow_redirects
            ),
            api_max_history_entries=data.get(
                "api_max_history_entries", Config.api_max_history_entries
            ),
            api_verify_ssl=data.get(
                "api_verify_ssl", Config.api_verify_ssl
            ),
            # Phase 2: External Tool Launchers
            ide_command=data.get("ide_command", Config.ide_command),
            ide_args=data.get("ide_args"),
            git_ui_command=data.get("git_ui_command", Config.git_ui_command),
            git_ui_args=data.get("git_ui_args"),
            db_client_command=data.get("db_client_command", Config.db_client_command),
            db_client_args=data.get("db_client_args"),
            jira_base_url=data.get("jira_base_url", Config.jira_base_url),
            api_docs_url=data.get("api_docs_url", Config.api_docs_url),
            plan_file=data.get("plan_file", Config.plan_file),
            notes_file=data.get("notes_file", Config.notes_file),
            tasks_file=data.get("tasks_file", Config.tasks_file),
        )

        return config

    except Exception as e:
        print_warning(f"Error loading config: {e}. Using defaults.")
        return Config()


def save_config(config: Config) -> None:
    """Save configuration to ~/.ccc-control/config.yaml."""
    config_path = get_config_path()

    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)


def update_config(**kwargs) -> Config:
    """
    Update configuration with new values.

    Args:
        **kwargs: Config fields to update

    Returns:
        Updated config

    Example:
        update_config(base_worktree_path="~/projects/worktrees")
    """
    config = load_config()

    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)

    save_config(config)
    return config


def install_wrapper_scripts() -> bool:
    """
    Install wrapper scripts (cc-build, cc-test) to ~/.ccc-control/bin.

    Returns:
        True if successful, False otherwise
    """
    import shutil
    import os

    try:
        # Get the bin directory
        bin_dir = get_ccc_home() / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)

        # Find the scripts directory (relative to this module)
        package_dir = Path(__file__).parent.parent
        scripts_dir = package_dir / "scripts"

        if not scripts_dir.exists():
            # Scripts not found, might be in development mode
            return False

        # Install scripts
        for script_name in ["cc-build", "cc-test"]:
            src = scripts_dir / script_name
            dst = bin_dir / script_name

            if src.exists():
                shutil.copy2(src, dst)
                # Make executable
                os.chmod(dst, 0o755)

        return True

    except Exception as e:
        return False


def init_config() -> Config:
    """
    Initialize configuration with interactive prompts.
    Called when user first sets up Command Center.
    """
    from ccc.utils import console

    console.print("\n[bold blue]Command Center Configuration[/bold blue]\n")

    # Get worktree base path
    default_worktree = Config.base_worktree_path
    worktree_path = (
        console.input(f"Base path for worktrees [{default_worktree}]: ").strip()
        or default_worktree
    )

    # Get status poll interval
    default_interval = Config.status_poll_interval
    poll_interval_str = console.input(
        f"Status poll interval in seconds [{default_interval}]: "
    ).strip()
    poll_interval = int(poll_interval_str) if poll_interval_str else default_interval

    # Get tmux prefix
    default_prefix = Config.tmux_session_prefix
    tmux_prefix = (
        console.input(f"Tmux session prefix [{default_prefix}]: ").strip()
        or default_prefix
    )

    # Create and save config
    config = Config(
        base_worktree_path=worktree_path,
        status_poll_interval=poll_interval,
        tmux_session_prefix=tmux_prefix,
    )

    save_config(config)

    console.print("\n[green]✓[/green] Configuration saved!\n")

    # Install wrapper scripts
    console.print("Installing wrapper scripts to ~/.ccc-control/bin...")
    if install_wrapper_scripts():
        console.print("[green]✓[/green] Wrapper scripts installed!")
        console.print("\nAdd to your PATH to use wrapper scripts:")
        console.print('  export PATH="$HOME/.ccc-control/bin:$PATH"')
        console.print("\nWrapper scripts available:")
        console.print(
            "  • cc-build <command>  - Track build status (auto-detects branch)"
        )
        console.print(
            "  • cc-test <command>   - Track test status (auto-detects branch)"
        )
    else:
        console.print(
            "[yellow]⚠[/yellow] Wrapper scripts not installed (scripts directory not found)"
        )

    console.print()

    return config
