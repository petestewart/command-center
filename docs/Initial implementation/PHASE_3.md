# Phase 3: Developer Actions - Implementation Plan

## Overview

**Duration:** 2 weeks  
**Goal:** Enable common actions directly from Command Center without dropping to CLI

Phase 3 adds the ability to perform git operations, trigger builds/tests, and preview file changes directly from the TUI without switching to terminal windows.

---

## Goal

Enable common actions directly from Command Center without dropping to CLI

## Key Features

### 3.1 Git Operations

**In-TUI git commands:**
- `c` - Commit with message dialog
- `p` - Push to remote
- `P` - Pull from remote
- `l` - View commit log (inline)
- `g` - Enhanced git status (modal view)

**Git commit dialog:**
```
┌─ Commit Changes: IN-413 ───────────────────────┐
│ Modified files (3):                            │
│ ☑ src/api/bulk-upload.ts                       │
│ ☑ src/validators/input.ts                      │
│ ☐ tests/api/bulk-upload.test.ts                │
│                                                │
│ Commit message:                                │
│ ┌────────────────────────────────────────────┐ │
│ │ Add input validation for bulk uploads      │ │
│ │                                            │ │
│ │ - Validate required fields                 │ │
│ │ - Check data types                         │ │
│ │ - Add error messages                       │ │
│ └────────────────────────────────────────────┘ │
│                                                │
│ [Tab] toggle files [Enter] commit [Esc] cancel │
└────────────────────────────────────────────────┘
```

### 3.2 Build Triggering

- `b` key to trigger build from TUI
- Show build progress in real-time
- Stream build output to panel
- Toast notification on completion

**Build output view:**
```
┌─ Building: IN-413 ─────────────────────────────┐
│ Running: npm run build                         │
│                                                │
│ > tsc --project tsconfig.json                  │
│ ✓ Compiled successfully                        │
│                                                │
│ Time: 45.2s                                    │
│ Warnings: 3                                    │
│                                                │
│ [Press any key to close]                       │
└────────────────────────────────────────────────┘
```

### 3.3 Test Execution

- `t` key to run tests from TUI
- Show test progress
- Display results immediately
- Jump to failed test files

### 3.4 File Preview

- `f` key to browse changed files
- Show inline diffs with syntax highlighting
- Use `delta` or `diff-so-fancy` for rendering

**File diff view:**
```
┌─ File: src/api/bulk-upload.ts ─────────────────┐
│ Modified 2 hours ago (47 lines changed)        │
│                                                │
│  40 │   export async function bulkUpload(      │
│  41 │     data: BulkUploadRequest              │
│  42 │   ): Promise<r> {                        │
│+ 43 │     // Validate input                    │
│+ 44 │     const validation = validateInput(    │
│+ 45 │       data                               │
│+ 46 │     );                                   │
│                                                │
│ [j/k] scroll [e] edit [n]ext file [p]revious   │
└────────────────────────────────────────────────┘
```

## Technical Implementation

**Git operations:**
```python
def commit_changes(ticket: Ticket, message: str, files: List[str]):
    """Execute git commit with selected files"""
    os.chdir(ticket.worktree_path)
    subprocess.run(["git", "add"] + files)
    subprocess.run(["git", "commit", "-m", message])
```

**Build triggering:**
```python
def trigger_build(ticket: Ticket):
    """Run build command and stream output"""
    # Read build command from .cc-control/config.yaml
    build_cmd = get_build_command(ticket)
    
    process = subprocess.Popen(
        build_cmd,
        cwd=ticket.worktree_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Stream output to TUI
    for line in process.stdout:
        yield line
```

## Deliverables

✅ Git commit dialog working  
✅ Push/pull operations working  
✅ Build triggering and progress display  
✅ Test execution from TUI  
✅ File diff preview  
✅ Keyboard shortcuts documented  

## Success Criteria

### Functionality
✅ Can commit changes with custom message from TUI  
✅ Can push/pull without leaving TUI  
✅ Can trigger builds and see progress in real-time  
✅ Can run tests and see results immediately  
✅ Can preview file diffs with syntax highlighting  

### User Experience
✅ All actions feel responsive (<1s to initiate)  
✅ Build/test output streams smoothly  
✅ Commit dialog supports multi-line messages  
✅ Can select which files to commit  
✅ Failed tests show actionable information  

### Integration
✅ Git operations work with worktrees  
✅ Build/test commands read from config  
✅ File previews work with various file types  
✅ All actions update relevant status files  

## Testing Plan

### Git Operations Testing
- Create commits with various message formats
- Test push/pull with remote repository
- Verify commit dialog file selection works
- Test with merge conflicts present
- Verify commit history view

### Build/Test Triggering Testing
- Trigger builds that succeed
- Trigger builds that fail
- Test with long-running builds (>1 minute)
- Verify output streaming doesn't lag
- Test toast notifications appear

### File Preview Testing
- Preview files with various extensions
- Test syntax highlighting accuracy
- Verify large diffs are handled gracefully
- Test navigation between files
- Verify "edit" action opens correct editor

## Configuration

### Build/Test Commands

Add to `~/.cc-control/config.yaml`:
```yaml
# Per-project build/test commands
projects:
  default:
    build_command: "npm run build"
    test_command: "npm test"
  
  # Project-specific overrides
  my-python-project:
    build_command: "python -m build"
    test_command: "pytest"
```

### Diff Viewer

```yaml
diff_viewer:
  tool: "delta"  # or "diff-so-fancy", "git"
  syntax_theme: "Monokai Extended"
  side_by_side: false
```

## Known Limitations

❌ No interactive rebase support  
❌ No merge conflict resolution UI  
❌ No git stash management  
❌ No cherry-pick support  
❌ Build/test commands must be non-interactive  

## Documentation Updates

Required documentation:
1. **GIT_OPERATIONS.md** - Using git features from TUI
2. **BUILD_TEST.md** - Configuring and running builds/tests
3. **KEYBOARD_SHORTCUTS.md** - Updated with new shortcuts
4. **CONFIGURATION.md** - Build/test command configuration

## Migration Notes

For users upgrading from Phase 2:
- Configuration format extended with build/test commands
- No breaking changes to existing functionality
- New keyboard shortcuts added (document conflicts if any)

## Next Steps to Phase 4

After Phase 3 completes:
- Gather feedback on in-TUI actions
- Identify which actions are most valuable
- Plan todo list management based on actual usage patterns
