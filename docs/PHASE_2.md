# Phase 2: Enhanced Visibility - Implementation Plan

## Overview

**Duration:** 2 weeks  
**Goal:** Surface more context without manual investigation

Phase 2 builds on the foundation by adding visibility into git status, build results, and test outcomes. Developers should be able to see the health of their tickets at a glance without checking terminal scrollback.

---

## Week 1: Git & Build Status Integration

### Objectives

- Integrate git status checking
- Track build status
- Display in TUI with clear indicators

### Technical Components

#### 1.1 Git Status Integration

**What to track:**

- Modified files count
- Untracked files count
- Commits ahead of origin
- Current branch
- Last commit message

**Implementation:**

```python
import subprocess
from dataclasses import dataclass

@dataclass
class GitStatus:
    modified_files: List[str]
    untracked_files: List[str]
    commits_ahead: int
    current_branch: str
    last_commit: str
    last_commit_time: datetime

def get_git_status(worktree_path: str) -> GitStatus:
    """Query git for status information"""

    # Get modified files
    result = subprocess.run(
        ["git", "diff", "--name-only"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    modified = result.stdout.strip().split('\n') if result.stdout else []

    # Get untracked files
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    untracked = result.stdout.strip().split('\n') if result.stdout else []

    # Get commits ahead
    result = subprocess.run(
        ["git", "rev-list", "--count", "HEAD", "^origin/HEAD"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    commits_ahead = int(result.stdout.strip()) if result.stdout else 0

    # Get last commit info
    result = subprocess.run(
        ["git", "log", "-1", "--format=%s|||%ct"],
        cwd=worktree_path,
        capture_output=True,
        text=True
    )
    if result.stdout:
        msg, timestamp = result.stdout.strip().split('|||')
        last_commit = msg
        last_commit_time = datetime.fromtimestamp(int(timestamp))
    else:
        last_commit = "No commits"
        last_commit_time = None

    return GitStatus(
        modified_files=modified,
        untracked_files=untracked,
        commits_ahead=commits_ahead,
        current_branch=get_current_branch(worktree_path),
        last_commit=last_commit,
        last_commit_time=last_commit_time
    )
```

**Display in TUI:**

```
┌─ Git Status ───────────────────────────────────┐
│ Branch: feature/IN-413-bulk-uploads            │
│ Modified: 3 files                              │
│ Untracked: 1 file                              │
│ Commits ahead: 4                               │
│ Last commit: "Add input validation"            │
│               2 hours ago                      │
└────────────────────────────────────────────────┘
```

**Optimization:**

- Cache git status for 10 seconds to avoid excessive git calls
- Run git checks in background thread
- Show stale indicator if cache older than configured threshold

#### 1.2 Build Status Tracking

**Approach:**
Watch for build output in a known location or parse known build commands

**Build status file format:**

```json
{
  "ticket_id": "IN-413",
  "status": "passing",
  "last_build": "2025-11-09T14:32:00Z",
  "duration_seconds": 45,
  "errors": [],
  "warnings": 3
}
```

**Location:** `~/.ccc-control/<ticket-id>/build-status.json`

**How to populate:**

Option A: Manual update after build

```bash
$ npm run build && ccc build success IN-413
$ npm run build || ccc build failure IN-413
```

Option B: Wrapper script that automatically updates

```bash
# ~/.ccc-control/bin/ccc-build
#!/bin/bash
TICKET_ID=$1
shift
START=$(date +%s)

# Run the build command
if "$@"; then
    STATUS="passing"
    EXIT_CODE=0
else
    STATUS="failing"
    EXIT_CODE=$?
fi

END=$(date +%s)
DURATION=$((END - START))

# Update build status
`ccc build update "$TICKET_ID" --status "$STATUS" --duration "$DURATION"
exit $EXIT_CODE
```

Usage:

```bash
$ cccc-build IN-413 npm run build
```

**CLI commands:**

```bash
$ ccc build update <ticket-id> --status <passing|failing> --duration <seconds>
$ ccc build show <ticket-id>
```

**Display in TUI:**

```
┌─ Build Status ─────────────────────────────────┐
│ Status: ✓ Passing                              │
│ Last build: 45 seconds, 3 warnings             │
│ Completed: 10 minutes ago                      │
└────────────────────────────────────────────────┘
```

Or if failing:

```
┌─ Build Status ─────────────────────────────────┐
│ Status: ✗ Failing                              │
│ Last build: 23 seconds, 2 errors               │
│ Completed: 2 minutes ago                       │
│ [Press 'b' to view build log]                  │
└────────────────────────────────────────────────┘
```

### Week 1 Deliverables

✅ Git status querying working  
✅ Git status displayed in ticket detail view  
✅ Build status file format defined  
✅ `ccc build` CLI commands implemented  
✅ Build status displayed in TUI  
✅ Wrapper script for automatic build tracking

---

## Week 2: Test Results Integration

### Objectives

- Track test execution results
- Parse common test output formats
- Display pass/fail/skip counts

### Technical Components

#### 2.1 Test Results Tracking

**Test status file format:**

```json
{
  "ticket_id": "IN-413",
  "status": "passing",
  "last_run": "2025-11-09T14:45:00Z",
  "duration_seconds": 12,
  "total": 50,
  "passed": 47,
  "failed": 2,
  "skipped": 1,
  "failures": [
    {
      "name": "API.bulkUpload should validate input",
      "message": "Expected 400 but got 500",
      "file": "tests/api/bulk-upload.test.ts",
      "line": 42
    }
  ]
}
```

**Location:** `~/.ccc-control/<ticket-id>/test-status.json`

#### 2.2 Test Output Parsing

Support common test frameworks:

**Jest (JavaScript/TypeScript):**

```javascript
// Parse Jest output
// "Tests: 2 failed, 47 passed, 1 skipped, 50 total"
const JEST_PATTERN =
  /Tests:\s+(\d+)\s+failed,\s+(\d+)\s+passed,\s+(\d+)\s+skipped,\s+(\d+)\s+total/;
```

**pytest (Python):**

```python
# Parse pytest output
# "47 passed, 2 failed, 1 skipped in 12.34s"
PYTEST_PATTERN = r'(\d+) passed, (\d+) failed, (\d+) skipped in ([\d.]+)s'
```

**Go test:**

```go
// Parse go test output
// "PASS: 47 | FAIL: 2 | SKIP: 1"
```

**Wrapper script:**

```bash
# ~/.ccc-control/bin/ccc-test
#!/bin/bash
TICKET_ID=$1
shift
START=$(date +%s)
TMPFILE=$(mktemp)

# Run tests and capture output
if "$@" 2>&1 | tee "$TMPFILE"; then
    STATUS="passing"
else
    STATUS="failing"
fi

END=$(date +%s)
DURATION=$((END - START))

# Parse output and update test status
`ccc test parse "$TICKET_ID" "$TMPFILE" --duration "$DURATION" --status "$STATUS"
rm "$TMPFILE"
```

**CLI commands:**

```bash
$ ccc test update <ticket-id> --passed <n> --failed <n> --total <n>
$ ccc test parse <ticket-id> <output-file>
$ ccc test show <ticket-id>
```

#### 2.3 Test Status Display

**In list view (summary):**

```
● IN-413  Public API bulk uploads      ⚠ 47/50 tests    2m ago
                                         ↑ indicates some failures
```

**In detail view:**

```
┌─ Test Status ──────────────────────────────────┐
│ Status: ⚠ 47 of 50 passing (94%)              │
│ Failed: 2 tests                                │
│ Skipped: 1 test                                │
│ Last run: 3 minutes ago (took 12s)             │
│                                                │
│ Failures:                                      │
│ • API.bulkUpload should validate input         │
│   tests/api/bulk-upload.test.ts:42            │
│ • API.bulkUpload should handle errors          │
│   tests/api/bulk-upload.test.ts:67            │
│                                                │
│ [Press 't' to re-run tests]                    │
└────────────────────────────────────────────────┘
```

#### 2.4 Enhanced Status Panel

**New layout with all status types:**

```
┌─ Ticket Detail: IN-413 ────────────────────────┐
│                                                │
│ ┌─ Agent Status ─────────────────────────────┐ │
│ │ Status: ⚙ Working on input validation     │ │
│ │ Last update: 2 minutes ago                │ │
│ └───────────────────────────────────────────┘ │
│                                                │
│ ┌─ Git Status ───────────────────────────────┐ │
│ │ Branch: feature/IN-413-bulk-uploads       │ │
│ │ Modified: 3 files | Commits ahead: 4      │ │
│ │ Last commit: "Add validation" (2h ago)    │ │
│ └───────────────────────────────────────────┘ │
│                                                │
│ ┌─ Build Status ─────────────────────────────┐ │
│ │ Status: ✓ Passing (3 warnings)            │ │
│ │ Last build: 10 minutes ago (took 45s)     │ │
│ └───────────────────────────────────────────┘ │
│                                                │
│ ┌─ Test Status ──────────────────────────────┐ │
│ │ Status: ⚠ 47/50 passing (94%)             │ │
│ │ Failed: 2 | Skipped: 1                    │ │
│ │ Last run: 3 minutes ago (took 12s)        │ │
│ └───────────────────────────────────────────┘ │
│                                                │
└────────────────────────────────────────────────┘
```

#### 2.5 Configurable Refresh

**Add configuration options:**

```yaml
# ~/.ccc-control/config.yaml
status_poll_interval: 3
git_status_cache_seconds: 10
build_status_cache_seconds: 30
test_status_cache_seconds: 30
```

**Manual refresh:**
Press `r` in TUI to force immediate refresh of all status

### Week 2 Deliverables

✅ Test status file format defined  
✅ Test output parsers for major frameworks  
✅ `ccc test` CLI commands implemented  
✅ Test status displayed in TUI  
✅ Wrapper script for automatic test tracking  
✅ Enhanced status panel showing all status types  
✅ Configurable refresh intervals  
✅ Manual refresh working

---

## Phase 2 Success Criteria

### Visibility Improvements

✅ Can see git status without running `git status`  
✅ Can see build status without checking build output  
✅ Can see test results without running tests  
✅ All status information visible in single view  
✅ Status updates within 5 seconds of actual changes

### Developer Experience

✅ Wrapper scripts are easy to integrate into workflow  
✅ Status indicators use clear symbols and colors  
✅ Failed tests show enough detail to investigate  
✅ Manual refresh works when needed

### Performance

✅ Git status queries don't slow down TUI  
✅ Background polling uses minimal CPU  
✅ Large test suites don't cause TUI lag

---

## Configuration Examples

### For JavaScript/Node.js Project

**package.json:**

```json
{
  "scripts": {
    "build": "ccc-build $(cat .ccc-ticket) tsc",
    "test": "ccc-test $(cat .ccc-ticket) jest",
    "dev": "npm run build && node dist/index.js"
  }
}
```

**Set ticket context:**

```bash
# In agent terminal
echo "IN-413" > .ccc-ticket
npm run build  # Automatically tracked
npm test       # Automatically tracked
```

### For Python Project

**Makefile:**

```makefile
TICKET := $(shell cat .ccc-ticket)

build:
	ccc-build $(TICKET) python -m build

test:
	ccc-test $(TICKET) pytest

lint:
	ccc-build $(TICKET) ruff check .
```

### For Go Project

**.ccc-build.sh:**

```bash
#!/bin/bash
TICKET=$(cat .ccc-ticket)
ccc-build $TICKET go build ./...
```

---

## Documentation Updates

Need to add to documentation:

1. **INTEGRATION_GUIDE.md** - How to integrate with build/test commands
2. **STATUS_FILES.md** - All status file formats
3. **WRAPPER_SCRIPTS.md** - Using cccc-build and cccc-test wrappers
4. **CONFIGURATION.md** - All config options

---

## Known Limitations (Phase 2)

These remain out of scope:

❌ No automatic build/test triggering from TUI  
❌ No deep git integration (commit, push, etc.)  
❌ No CI/CD integration  
❌ No code coverage metrics  
❌ Test failure stack traces (just names and locations)

---

## Migration from Phase 1

For users upgrading from Phase 1:

1. **Config migration:** Add new config fields with defaults
2. **Ticket format:** Extend with new status file references
3. **Backward compatibility:** Phase 1 tickets still work, just without new status
4. **Documentation:** Clear upgrade guide

---

## Testing Plan

### Git Status Testing

- Test with clean working directory
- Test with modified files
- Test with untracked files
- Test with unpushed commits
- Test with merge conflicts

### Build Status Testing

- Test successful builds
- Test failing builds
- Test builds with warnings
- Test concurrent builds (should queue)

### Test Status Testing

- Test all-passing test suite
- Test partial failures
- Test all-failing test suite
- Test skipped tests
- Test timeout scenarios

### Integration Testing

- Modify code, verify git status updates
- Run build, verify build status updates
- Run tests, verify test status updates
- All status types update independently

---

## Next Steps to Phase 3

After Phase 2 completes:

- User testing with enhanced visibility
- Gather feedback on wrapper scripts
- Identify most-requested actions to add to Phase 3
- Refine Phase 3 plan based on learnings
