# Phase 5: IDE Integration - Implementation Plan

## Overview

**Duration:** 2 weeks  
**Goal:** Seamlessly connect to code editors for file viewing and editing

Phase 5 adds deep integration with code editors, allowing developers to quickly open files, view diffs, and navigate codebases from within Command Center.

---

## Goal

Seamlessly connect to code editors for file viewing and editing

## Key Features

### 5.1 Editor Detection

```python
def detect_editor() -> str:
    """Auto-detect user's preferred editor"""
    # Check environment variables
    if os.getenv("EDITOR"):
        return os.getenv("EDITOR")
    
    # Check for common editors
    editors = ["cursor", "code", "nvim", "vim", "nano"]
    for editor in editors:
        if shutil.which(editor):
            return editor
    
    return "vi"  # Fallback
```

### 5.2 Cursor/VSCode Integration

```python
def open_in_cursor(file_path: str, line: int = None):
    """Open file in Cursor at specific line"""
    if line:
        subprocess.run(["cursor", "--goto", f"{file_path}:{line}"])
    else:
        subprocess.run(["cursor", file_path])
```

### 5.3 Built-in Diff Viewer

- Uses `delta` for beautiful diffs
- Syntax highlighting
- Side-by-side or unified view
- Navigate between hunks

### 5.4 File Tree Navigation

```
┌─ Changed Files: IN-413 ────────────────────────┐
│ src/                                           │
│ ├─● api/                                       │
│ │  ├─ M bulk-upload.ts           [e]dit       │
│ │  └─ M response.ts               [d]iff      │
│ ├─● validators/                                │
│ │  └─ M input.ts                               │
│ └─● types/                                     │
│    └─ A upload.d.ts               (new)       │
│ tests/                                         │
│ └─● api/                                       │
│    └─ M bulk-upload.test.ts                   │
│                                                │
│ M=modified A=added D=deleted                   │
│ [j/k] navigate [e]dit [d]iff [v]iew in IDE    │
└────────────────────────────────────────────────┘
```

## CLI Commands

**Editor operations:**
```bash
# Open file in configured editor
cc edit <branch> <file-path>

# Open file at specific line
cc edit <branch> <file-path>:<line>

# Open all changed files
cc edit <branch> --all-changed

# Configure default editor
cc config set editor cursor
```

## Technical Implementation

### Editor Detection

```python
class EditorManager:
    KNOWN_EDITORS = {
        "cursor": {
            "binary": "cursor",
            "args": ["--goto", "{file}:{line}"],
            "supports_goto": True
        },
        "code": {
            "binary": "code",
            "args": ["--goto", "{file}:{line}"],
            "supports_goto": True
        },
        "nvim": {
            "binary": "nvim",
            "args": ["{file}", "+{line}"],
            "supports_goto": True
        },
        "vim": {
            "binary": "vim",
            "args": ["{file}", "+{line}"],
            "supports_goto": True
        }
    }
    
    def detect_editor(self) -> str:
        # Check config first
        if config_editor := self.config.get("editor"):
            return config_editor
        
        # Check environment
        if env_editor := os.getenv("EDITOR"):
            return env_editor
        
        # Auto-detect
        for name, info in self.KNOWN_EDITORS.items():
            if shutil.which(info["binary"]):
                return name
        
        return "vi"  # Ultimate fallback
```

### Opening Files

```python
def open_file(branch: str, file_path: str, line: int = None):
    """Open file in configured editor"""
    editor = EditorManager().detect_editor()
    editor_info = EditorManager.KNOWN_EDITORS.get(editor)
    
    worktree_path = get_worktree_path(branch)
    full_path = worktree_path / file_path
    
    if editor_info and editor_info["supports_goto"] and line:
        # Use editor's native goto
        args = [
            arg.format(file=full_path, line=line)
            for arg in editor_info["args"]
        ]
        subprocess.run([editor_info["binary"]] + args)
    else:
        # Basic file opening
        subprocess.run([editor, full_path])
```

### Built-in Diff Viewer

```python
class DiffViewer:
    def __init__(self):
        self.diff_tool = self._detect_diff_tool()
    
    def _detect_diff_tool(self) -> str:
        """Detect available diff tool"""
        tools = ["delta", "diff-so-fancy", "git"]
        for tool in tools:
            if shutil.which(tool):
                return tool
        return "git"
    
    def view_diff(self, branch: str, file_path: str = None):
        """Display diff in TUI"""
        worktree_path = get_worktree_path(branch)
        
        if self.diff_tool == "delta":
            cmd = ["git", "diff", file_path] if file_path else ["git", "diff"]
            process = subprocess.Popen(
                cmd,
                cwd=worktree_path,
                stdout=subprocess.PIPE
            )
            delta_process = subprocess.Popen(
                ["delta"],
                stdin=process.stdout,
                stdout=subprocess.PIPE,
                text=True
            )
            return delta_process.stdout.read()
        else:
            # Fallback to basic git diff
            cmd = ["git", "diff", "--color=always"]
            if file_path:
                cmd.append(file_path)
            result = subprocess.run(
                cmd,
                cwd=worktree_path,
                capture_output=True,
                text=True
            )
            return result.stdout
```

### File Tree

```python
def get_changed_files_tree(branch: str) -> dict:
    """Get tree structure of changed files"""
    worktree_path = get_worktree_path(branch)
    
    # Get changed files
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    
    files = []
    for line in result.stdout.strip().split('\n'):
        if not line:
            continue
        status = line[:2]
        filepath = line[3:]
        files.append({
            "path": filepath,
            "status": parse_git_status(status)
        })
    
    # Build tree structure
    return build_tree_from_paths(files)

def parse_git_status(status: str) -> str:
    """Parse git status code"""
    if status == " M" or status == "M ":
        return "modified"
    elif status == "A " or status == "AM":
        return "added"
    elif status == "D " or status == "AD":
        return "deleted"
    elif status == "??":
        return "untracked"
    return "unknown"
```

## TUI Integration

### File Browser View

New view accessible with `f` key from branch detail:

```python
class FileBrowserView(Container):
    def __init__(self, branch: str):
        super().__init__()
        self.branch = branch
        self.files = get_changed_files_tree(branch)
        self.selected_file = None
    
    def on_mount(self):
        self.render_file_tree()
    
    def action_edit(self):
        """Open selected file in editor"""
        if self.selected_file:
            open_file(self.branch, self.selected_file)
    
    def action_diff(self):
        """Show diff for selected file"""
        if self.selected_file:
            diff_content = DiffViewer().view_diff(
                self.branch,
                self.selected_file
            )
            self.show_diff_modal(diff_content)
```

## Deliverables

✅ Editor auto-detection  
✅ Open files in external editor  
✅ Built-in diff viewer with syntax highlighting  
✅ File tree navigation  
✅ Jump to specific lines  

## Success Criteria

### Functionality
✅ Correctly detects user's preferred editor  
✅ Opens files in editor from TUI  
✅ Can open files at specific line numbers  
✅ Diff viewer shows syntax-highlighted diffs  
✅ File tree shows all changed files  

### User Experience
✅ File opening is instant (<500ms)  
✅ Diff viewer is readable and navigable  
✅ File tree is intuitive to navigate  
✅ Keyboard shortcuts feel natural  
✅ Works with common editors (Cursor, VSCode, vim, neovim)  

### Integration
✅ Respects EDITOR environment variable  
✅ Works with git worktrees  
✅ Handles various file types  
✅ Gracefully degrades if editor not found  

## Testing Plan

### Editor Detection Testing
- Test with different EDITOR values
- Test with various editors installed
- Test with no editor configured
- Verify fallback to vi works

### File Opening Testing
- Open various file types
- Open files at specific lines
- Open files with spaces in names
- Test with relative and absolute paths

### Diff Viewer Testing
- View diffs for modified files
- View diffs for new files
- View diffs with large changes
- Test syntax highlighting
- Verify navigation works

### File Tree Testing
- Display tree with nested directories
- Show correct status indicators
- Handle empty directories
- Test with many files (>50)

## Configuration

### Editor Settings

Add to `~/.cc-control/config.yaml`:
```yaml
editor:
  default: cursor
  line_number_format: "{file}:{line}"  # How to format goto commands
  
diff_viewer:
  tool: delta
  theme: Monokai Extended
  side_by_side: false
  line_numbers: true
  
file_browser:
  show_hidden: false
  max_depth: 5
  sort_by: name  # or "status", "modified"
```

## Dependencies

New dependencies required:
- `delta` (optional, for better diffs)
- `pygments` (for syntax highlighting if delta not available)

## Known Limitations

❌ No in-TUI text editing (must use external editor)  
❌ No multi-file diff comparison  
❌ No blame/history view per file  
❌ No search across files from TUI  
❌ Limited support for binary files  

## Future Enhancements (Post-Phase 5)

- In-TUI text viewer for quick reads
- File search functionality
- Blame view integration
- History/timeline per file
- Open entire project in IDE
- Quick file open (fuzzy finder)

## Documentation Updates

Required documentation:
1. **EDITOR_INTEGRATION.md** - Setting up editor integration
2. **FILE_NAVIGATION.md** - Using file browser
3. **DIFF_VIEWING.md** - Understanding diffs
4. **KEYBOARD_SHORTCUTS.md** - Updated with file browser shortcuts

## Migration Notes

For users upgrading from Phase 4:
- Editor auto-detection happens on first use
- Configuration format extended with editor settings
- No breaking changes
- Optional dependency on delta (falls back to git diff)

## Next Steps to Phase 6

After Phase 5 completes:
- Gather feedback on editor integration
- Identify most-used file operations
- Plan communication features for replanning
