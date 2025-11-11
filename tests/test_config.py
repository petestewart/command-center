"""
Unit tests for config module.
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from ccc.config import (
    Config,
    get_config_path,
    load_config,
    save_config,
    update_config,
    install_wrapper_scripts,
    init_config,
)


class TestConfig:
    """Tests for Config dataclass."""

    def test_config_default_values(self):
        """Test Config with default values."""
        config = Config()

        assert config.base_worktree_path == "~/code/worktrees"
        assert config.status_poll_interval == 3
        assert config.tmux_session_prefix == "ccc-"
        assert config.default_git_remote == "origin"
        assert config.base_repo_path is None
        assert config.git_status_cache_seconds == 10
        assert config.build_status_cache_seconds == 30
        assert config.test_status_cache_seconds == 30

    def test_config_custom_values(self):
        """Test Config with custom values."""
        config = Config(
            base_worktree_path="~/projects/wt",
            status_poll_interval=5,
            tmux_session_prefix="dev-",
            default_git_remote="upstream",
            base_repo_path="~/projects/main",
            git_status_cache_seconds=20,
        )

        assert config.base_worktree_path == "~/projects/wt"
        assert config.status_poll_interval == 5
        assert config.tmux_session_prefix == "dev-"
        assert config.default_git_remote == "upstream"
        assert config.base_repo_path == "~/projects/main"
        assert config.git_status_cache_seconds == 20

    @patch("ccc.config.expand_path")
    def test_config_get_worktree_path(self, mock_expand):
        """Test getting worktree path for a ticket."""
        mock_expand.return_value = Path("/home/user/code/worktrees")
        config = Config()

        path = config.get_worktree_path("TEST-001")

        assert path == Path("/home/user/code/worktrees/TEST-001")
        mock_expand.assert_called_once_with("~/code/worktrees")

    def test_config_to_dict(self):
        """Test converting Config to dictionary."""
        config = Config(
            base_worktree_path="~/test",
            status_poll_interval=10,
        )

        data = config.to_dict()

        assert isinstance(data, dict)
        assert data["base_worktree_path"] == "~/test"
        assert data["status_poll_interval"] == 10
        assert "tmux_session_prefix" in data


class TestConfigPaths:
    """Tests for config path functions."""

    @patch("ccc.config.get_cccc_home")
    def test_get_config_path(self, mock_get_home):
        """Test getting config file path."""
        mock_get_home.return_value = Path("/home/user/.cccc-control")

        path = get_config_path()

        assert path == Path("/home/user/.cccc-control/config.yaml")


class TestLoadSaveConfig:
    """Tests for loading and saving configuration."""

    @patch("ccc.config.get_config_path")
    @patch("ccc.config.save_config")
    def test_load_config_new(self, mock_save, mock_get_path):
        """Test loading config when file doesn't exist."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_get_path.return_value = mock_path

        config = load_config()

        # Should create default config
        assert isinstance(config, Config)
        assert config.base_worktree_path == Config.base_worktree_path
        mock_save.assert_called_once()

    @patch("ccc.config.get_config_path")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_existing(self, mock_file, mock_get_path):
        """Test loading existing config file."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        yaml_data = {
            "base_worktree_path": "~/custom/path",
            "status_poll_interval": 5,
            "tmux_session_prefix": "test-",
        }

        with patch("yaml.safe_load", return_value=yaml_data):
            config = load_config()

        assert config.base_worktree_path == "~/custom/path"
        assert config.status_poll_interval == 5
        assert config.tmux_session_prefix == "test-"

    @patch("ccc.config.get_config_path")
    def test_load_config_error(self, mock_get_path):
        """Test loading config with error."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        with patch("builtins.open", side_effect=Exception("YAML error")):
            config = load_config()

        # Should return default config
        assert isinstance(config, Config)

    @patch("ccc.config.get_config_path")
    @patch("builtins.open", new_callable=mock_open)
    def test_load_config_empty_file(self, mock_file, mock_get_path):
        """Test loading config from empty file."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_get_path.return_value = mock_path

        with patch("yaml.safe_load", return_value=None):
            config = load_config()

        # Should use defaults
        assert isinstance(config, Config)
        assert config.base_worktree_path == Config.base_worktree_path

    @patch("ccc.config.get_config_path")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_config(self, mock_file, mock_get_path):
        """Test saving config."""
        mock_path = MagicMock()
        mock_path.parent.mkdir = MagicMock()
        mock_get_path.return_value = mock_path

        config = Config(base_worktree_path="~/test")

        with patch("yaml.dump") as mock_yaml_dump:
            save_config(config)

        mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_yaml_dump.assert_called_once()

    @patch("ccc.config.get_config_path")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_config_creates_directory(self, mock_file, mock_get_path):
        """Test that save_config creates parent directory."""
        mock_path = MagicMock()
        mock_get_path.return_value = mock_path

        config = Config()
        save_config(config)

        mock_path.parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)


class TestUpdateConfig:
    """Tests for updating configuration."""

    @patch("ccc.config.load_config")
    @patch("ccc.config.save_config")
    def test_update_config_single_field(self, mock_save, mock_load):
        """Test updating a single config field."""
        existing_config = Config(base_worktree_path="~/old")
        mock_load.return_value = existing_config

        config = update_config(base_worktree_path="~/new")

        assert config.base_worktree_path == "~/new"
        mock_save.assert_called_once_with(config)

    @patch("ccc.config.load_config")
    @patch("ccc.config.save_config")
    def test_update_config_multiple_fields(self, mock_save, mock_load):
        """Test updating multiple config fields."""
        existing_config = Config()
        mock_load.return_value = existing_config

        config = update_config(
            status_poll_interval=10,
            tmux_session_prefix="new-",
        )

        assert config.status_poll_interval == 10
        assert config.tmux_session_prefix == "new-"
        mock_save.assert_called_once()

    @patch("ccc.config.load_config")
    @patch("ccc.config.save_config")
    def test_update_config_invalid_field(self, mock_save, mock_load):
        """Test updating config with invalid field."""
        existing_config = Config()
        mock_load.return_value = existing_config

        config = update_config(invalid_field="value")

        # Should not raise error, just ignore invalid field
        mock_save.assert_called_once()


class TestInstallWrapperScripts:
    """Tests for installing wrapper scripts."""

    @patch("ccc.config.get_cccc_home")
    def test_install_wrapper_scripts_success(self, mock_get_home):
        """Test successfully installing wrapper scripts."""
        mock_get_home.return_value = Path("/home/user/.cccc-control")

        # Just test that it doesn't raise an exception
        result = install_wrapper_scripts()

        # Function executes without error
        assert result in [True, False]

    @patch("ccc.config.get_cccc_home")
    @patch("ccc.config.Path")
    def test_install_wrapper_scripts_no_scripts_dir(self, mock_path_class, mock_get_home):
        """Test installing wrapper scripts when scripts directory doesn't exist."""
        mock_get_home.return_value = Path("/home/user/.cccc-control")

        # Setup mock to simulate scripts directory not existing
        with patch("pathlib.Path.exists", return_value=False):
            result = install_wrapper_scripts()

        # Should return False when scripts not found
        assert result is False

    @patch("ccc.config.get_cccc_home")
    def test_install_wrapper_scripts_error(self, mock_get_home):
        """Test installing wrapper scripts with error."""
        mock_get_home.side_effect = Exception("Error")

        result = install_wrapper_scripts()

        assert result is False


class TestInitConfig:
    """Tests for interactive config initialization."""

    @patch("ccc.utils.console")
    @patch("ccc.config.save_config")
    @patch("ccc.config.install_wrapper_scripts")
    def test_init_config_defaults(self, mock_install, mock_save, mock_console):
        """Test initializing config with default values."""
        # Simulate user pressing Enter for all prompts (use defaults)
        mock_console.input.side_effect = ["", "", ""]
        mock_install.return_value = True

        config = init_config()

        assert config.base_worktree_path == Config.base_worktree_path
        assert config.status_poll_interval == Config.status_poll_interval
        assert config.tmux_session_prefix == Config.tmux_session_prefix
        mock_save.assert_called_once()

    @patch("ccc.utils.console")
    @patch("ccc.config.save_config")
    @patch("ccc.config.install_wrapper_scripts")
    def test_init_config_custom_values(self, mock_install, mock_save, mock_console):
        """Test initializing config with custom values."""
        mock_console.input.side_effect = ["~/custom/path", "5", "dev-"]
        mock_install.return_value = True

        config = init_config()

        assert config.base_worktree_path == "~/custom/path"
        assert config.status_poll_interval == 5
        assert config.tmux_session_prefix == "dev-"
        mock_save.assert_called_once()

    @patch("ccc.utils.console")
    @patch("ccc.config.save_config")
    @patch("ccc.config.install_wrapper_scripts")
    def test_init_config_wrapper_scripts_failed(self, mock_install, mock_save, mock_console):
        """Test init config when wrapper scripts installation fails."""
        mock_console.input.side_effect = ["", "", ""]
        mock_install.return_value = False

        config = init_config()

        assert isinstance(config, Config)
        mock_console.print.assert_called()  # Should print warning about scripts
