"""
Configuration management for Command Center
"""

import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

from ccc.utils import get_cccc_home, expand_path, sanitize_branch_name


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

    def get_worktree_path(self, branch_name: str) -> Path:
        """
        Get the worktree path for a specific branch.

        The branch name is sanitized for filesystem compatibility (e.g., slashes replaced with underscores).
        """
        base = expand_path(self.base_worktree_path)
        sanitized = sanitize_branch_name(branch_name)
        return base / sanitized

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)


def get_config_path() -> Path:
    """Get the path to the config file."""
    return get_cccc_home() / "config.yaml"


def load_config() -> Config:
    """
    Load configuration from ~/.cccc-control/config.yaml.
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
        )

        return config

    except Exception as e:
        from ccc.utils import print_warning

        print_warning(f"Error loading config: {e}. Using defaults.")
        return Config()


def save_config(config: Config) -> None:
    """Save configuration to ~/.cccc-control/config.yaml."""
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
        bin_dir = get_cccc_home() / "bin"
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
        console.print("  export PATH=\"$HOME/.ccc-control/bin:$PATH\"")
        console.print("\nWrapper scripts available:")
        console.print("  • cc-build <command>  - Track build status (auto-detects branch)")
        console.print("  • cc-test <command>   - Track test status (auto-detects branch)")
    else:
        console.print("[yellow]⚠[/yellow] Wrapper scripts not installed (scripts directory not found)")

    console.print()

    return config
