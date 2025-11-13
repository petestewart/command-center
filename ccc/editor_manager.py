"""
Editor manager for opening files in external editors.

Handles auto-detection of editors and supports opening files at specific line numbers.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class EditorInfo:
    """Information about an editor."""
    binary: str
    supports_goto: bool
    goto_format: str  # Format string with {file} and {line} placeholders


class EditorManager:
    """
    Manages editor detection and file opening.

    Supports auto-detection of common editors and handles opening files
    with optional line number positioning.
    """

    # Known editors with their command-line syntax for goto
    KNOWN_EDITORS: Dict[str, EditorInfo] = {
        "cursor": EditorInfo(
            binary="cursor",
            supports_goto=True,
            goto_format="--goto {file}:{line}"
        ),
        "code": EditorInfo(
            binary="code",
            supports_goto=True,
            goto_format="--goto {file}:{line}"
        ),
        "nvim": EditorInfo(
            binary="nvim",
            supports_goto=True,
            goto_format="+{line} {file}"
        ),
        "vim": EditorInfo(
            binary="vim",
            supports_goto=True,
            goto_format="+{line} {file}"
        ),
        "nano": EditorInfo(
            binary="nano",
            supports_goto=True,
            goto_format="+{line} {file}"
        ),
        "emacs": EditorInfo(
            binary="emacs",
            supports_goto=True,
            goto_format="+{line} {file}"
        ),
        "subl": EditorInfo(
            binary="subl",
            supports_goto=True,
            goto_format="{file}:{line}"
        ),
        "atom": EditorInfo(
            binary="atom",
            supports_goto=True,
            goto_format="{file}:{line}"
        ),
    }

    def __init__(self, config_editor: Optional[str] = None):
        """
        Initialize the editor manager.

        Args:
            config_editor: Optional editor from config file
        """
        self.config_editor = config_editor
        self._detected_editor: Optional[str] = None

    def detect_editor(self) -> str:
        """
        Auto-detect the user's preferred editor.

        Priority:
        1. Config file setting
        2. EDITOR environment variable
        3. Auto-detect from known editors
        4. Fallback to 'vi'

        Returns:
            Editor command name
        """
        if self._detected_editor:
            return self._detected_editor

        # 1. Check config first
        if self.config_editor:
            self._detected_editor = self.config_editor
            return self._detected_editor

        # 2. Check environment variable
        env_editor = os.getenv("EDITOR")
        if env_editor:
            # Extract just the binary name if it's a full path
            self._detected_editor = Path(env_editor).name
            return self._detected_editor

        # 3. Auto-detect from known editors
        for name, info in self.KNOWN_EDITORS.items():
            if shutil.which(info.binary):
                self._detected_editor = name
                return self._detected_editor

        # 4. Fallback to vi (should be available on most systems)
        self._detected_editor = "vi"
        return self._detected_editor

    def get_editor_info(self, editor_name: str) -> Optional[EditorInfo]:
        """
        Get information about an editor.

        Args:
            editor_name: Name of the editor

        Returns:
            EditorInfo if known, None otherwise
        """
        return self.KNOWN_EDITORS.get(editor_name)

    def open_file(
        self,
        file_path: Path,
        line: Optional[int] = None,
        worktree_root: Optional[Path] = None
    ) -> tuple[bool, str]:
        """
        Open a file in the configured editor.

        Args:
            file_path: Path to the file to open
            line: Optional line number to jump to
            worktree_root: Optional worktree root to open as workspace

        Returns:
            Tuple of (success, message)
        """
        editor_name = self.detect_editor()
        editor_info = self.get_editor_info(editor_name)

        # Convert to absolute path
        file_path = file_path.resolve()

        # Build command
        cmd = []

        # For VS Code and Cursor, open workspace folder if available
        if editor_name in ["cursor", "code"] and worktree_root:
            worktree_root = worktree_root.resolve()
            cmd = [editor_info.binary, str(worktree_root)]

            # Add goto syntax for the file
            if line and editor_info.supports_goto:
                goto_arg = f"--goto {file_path}:{line}"
                cmd.append(goto_arg)
            else:
                cmd.append(str(file_path))

        elif editor_info and editor_info.supports_goto and line:
            # Use editor's native goto syntax
            goto_arg = editor_info.goto_format.format(file=str(file_path), line=line)

            # Split the goto format into separate arguments
            if goto_arg.startswith("--goto "):
                # VS Code/Cursor style: --goto file:line
                cmd = [editor_info.binary, "--goto", goto_arg.replace("--goto ", "")]
            elif goto_arg.startswith("+"):
                # Vim style: +line file
                parts = goto_arg.split()
                cmd = [editor_info.binary] + parts
            else:
                # Other styles: file:line
                cmd = [editor_info.binary, goto_arg]

        elif editor_info:
            # Basic file opening without line number
            cmd = [editor_info.binary, str(file_path)]

        else:
            # Unknown editor, try basic command
            cmd = [editor_name, str(file_path)]

        # Execute command
        try:
            subprocess.run(cmd, check=False)

            msg = f"Opened {file_path.name} in {editor_name}"
            if line:
                msg += f" at line {line}"

            return True, msg

        except FileNotFoundError:
            return False, f"Editor '{editor_name}' not found"

        except Exception as e:
            return False, f"Error opening editor: {e}"

    def is_available(self) -> bool:
        """
        Check if the detected editor is available.

        Returns:
            True if editor is available, False otherwise
        """
        editor_name = self.detect_editor()
        editor_info = self.get_editor_info(editor_name)

        if editor_info:
            return shutil.which(editor_info.binary) is not None

        # For unknown editors, check if the command exists
        return shutil.which(editor_name) is not None


def open_in_editor(
    file_path: Path,
    line: Optional[int] = None,
    worktree_root: Optional[Path] = None,
    config_editor: Optional[str] = None
) -> tuple[bool, str]:
    """
    Convenience function to open a file in the editor.

    Args:
        file_path: Path to the file to open
        line: Optional line number to jump to
        worktree_root: Optional worktree root to open as workspace
        config_editor: Optional editor from config

    Returns:
        Tuple of (success, message)
    """
    manager = EditorManager(config_editor=config_editor)
    return manager.open_file(file_path, line=line, worktree_root=worktree_root)
